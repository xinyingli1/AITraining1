terraform {
  required_version = ">= 1.0.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Service Account for Cloud Run
resource "google_service_account" "agent_sa" {
  account_id   = "meal-planning-agent-sa"
  display_name = "Service Account for Meal Planning Agent"
}

# 2. Firestore Database (Native mode)
# Note: Google Cloud allows only one Firestore database named '(default)' per project.
# This resource assumes you are managing the default database.
resource "google_firestore_database" "database" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}

# 3. IAM Bindings for Service Account
# A. Firestore Access
resource "google_project_iam_member" "firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

# B. Cloud Trace Access
resource "google_project_iam_member" "trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

# C. Vertex AI User Access (for enterprise-managed Gemini API via Vertex AI)
resource "google_project_iam_member" "vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

# 4. Cloud Run Service (v2)
resource "google_cloud_run_v2_service" "agent_service" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.agent_sa.email

    containers {
      image = var.image_url

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      ports {
        container_port = 8080
      }

      # Inject API Key if provided
      dynamic "env" {
        for_each = var.gemini_api_key != "" ? [1] : []
        content {
          name  = "GEMINI_API_KEY"
          value = var.gemini_api_key
        }
      }
    }
  }

  depends_on = [
    google_project_iam_member.firestore_user,
    google_project_iam_member.trace_agent,
    google_project_iam_member.vertex_user,
    google_firestore_database.database
  ]
}

# 5. Allow Unauthenticated Public Access to Cloud Run (Optional)
resource "google_cloud_run_v2_service_iam_member" "noauth" {
  location = google_cloud_run_v2_service.agent_service.location
  name     = google_cloud_run_v2_service.agent_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
