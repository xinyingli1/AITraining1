variable "project_id" {
  description = "The GCP Project ID to deploy resources in"
  type        = string
}

variable "region" {
  description = "The GCP region to deploy resources in"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "The name of the Cloud Run service"
  type        = string
  default     = "meal-planning-agent-service"
}

variable "image_url" {
  description = "The Docker image URL in Artifact Registry (e.g., us-central1-docker.pkg.dev/project/repo/image:tag)"
  type        = string
}

variable "gemini_api_key" {
  description = "The Gemini API Key (optional if using Vertex AI IAM roles)"
  type        = string
  sensitive   = true
  default     = ""
}
