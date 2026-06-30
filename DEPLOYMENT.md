# Build and Deployment Guide

This document explains the CI/CD pipeline, containerization, and local quality control setup for the **Meal Planning Agent**.

---

## Table of Contents
1. [Local Quality Control (Linting & Testing)](#1-local-quality-control-linting--testing)
2. [CI/CD Pipeline (GitHub Actions)](#2-cicd-pipeline-github-actions)
3. [Containerization (Docker)](#3-containerization-docker)
4. [Handling Google Calendar API in Containerized Environments](#4-handling-google-calendar-api-in-containerized-environments)
5. [Production Deployment Considerations](#5-production-deployment-considerations)
6. [Distributed Tracing (OpenTelemetry)](#6-distributed-tracing-opentelemetry)
7. [Google Enterprise Agent Platform Deployment](#7-google-enterprise-agent-platform-deployment)



---

## 1. Local Quality Control (Linting & Testing)

To maintain high code quality, we use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting, and [Pytest](https://docs.pytest.org/) for unit testing.

### Install Development Dependencies
Install the required development packages:
```bash
pip install -r requirements-dev.txt --index-url https://pypi.org/simple
```

### Running the Linter & Formatter
We use Ruff to enforce style guides and catch potential bugs.

* **Check for lint errors:**
  ```bash
  python3 -m ruff check .
  ```
* **Automatically fix lint errors:**
  ```bash
  python3 -m ruff check . --fix
  ```
* **Check formatting (dry-run):**
  ```bash
  python3 -m ruff format --check .
  ```
* **Format code:**
  ```bash
  python3 -m ruff format .
  ```

### Running Unit & Agent Evaluation Tests
We have implemented two levels of testing under the `tests/` directory:
1. **Unit Tests**: Test individual tool behaviors locally (e.g., JSON profile updates) without mutating real state or invoking LLMs.
2. **Agent Evaluation Scenarios**: Run the agent end-to-end against a **golden dataset** using mocked tools to assert reasoning and safety policies.

To run all tests (evaluation tests will be automatically skipped if no `GEMINI_API_KEY` is present):
```bash
python3 -m pytest
```

To run the agent evaluation scenarios specifically, you **must** provide your `GEMINI_API_KEY` in the environment so the agent can interact with the Gemini model:
```bash
export GEMINI_API_KEY="your-api-key"
python3 -m pytest -v tests/test_agent_eval.py
```

### Golden Dataset Scenarios (`tests/golden_dataset.json`)
The agent is evaluated against the following scenarios:
* **`food_restrictions_respected`**: Verifies that the agent reads the user profile and does not suggest ingredients violating allergies (e.g. peanuts) or dietary restrictions (e.g. vegetarian).
* **`payment_requires_confirmation_approved`**: Verifies that a payment >= $10.00 (e.g., $25.00) triggers the user confirmation prompt, and succeeds if the user approves.
* **`payment_requires_confirmation_denied`**: Verifies that a payment >= $10.00 is blocked if the user denies approval.
* **`payment_below_threshold_auto_approved`**: Verifies that a payment < $10.00 (e.g. $2.50) bypasses user confirmation and is auto-approved.
* **`calendar_conflict_respected`**: Verifies that the agent checks the calendar, detects conflicts (e.g. a Dentist appointment), and refuses to schedule overlapping cooking sessions.


---

## 2. CI/CD Pipeline (GitHub Actions)

We have configured a GitHub Actions workflow in [.github/workflows/ci.yml](file:///.github/workflows/ci.yml).

### Workflow Triggers
* **Lint & Test**: Runs on every `push` or `pull_request` to the `main` branch.
* **Build Docker Image**: Runs **only** on a `push` (e.g., merge) to the `main` branch after the lint and test jobs pass.

### Jobs
1. **Lint and Test**:
   * Sets up a Python 3.10 environment.
   * Caches pip dependencies to speed up future runs.
   * Installs production and development dependencies.
   * Runs `ruff check` and `ruff format --check`.
   * Runs the `pytest` suite.
2. **Build Docker Image**:
   * Sets up Docker Buildx.
   * Builds the Docker image from the [Dockerfile](file:///Dockerfile).
   * *Note: The push to a container registry (like GitHub Container Registry or Google Artifact Registry) is currently set to `false`. You can enable it by configuring registry credentials.*

---

## 3. Containerization (Docker)

The application can be packaged into a lightweight Docker container using the provided [Dockerfile](file:///Dockerfile) and [.dockerignore](file:///.dockerignore).

### Build the Docker Image
To build the image locally:
```bash
docker build -t meal-planning-agent .
```

### Run the Docker Container
Because the Meal Planning Agent is an interactive CLI application, you **must** run the container in interactive mode (`-it`):
```bash
docker run -it meal-planning-agent
```

### Persisting the User Profile
The agent stores user preferences, allergies, and restrictions in `user_profile.json`. To prevent this profile from being lost when the container exits, mount it as a volume:
```bash
docker run -it \
  -v $(pwd)/user_profile.json:/app/user_profile.json \
  meal-planning-agent
```

---

## 4. Handling Google Calendar API in Containerized Environments

The Google Calendar API integration uses OAuth 2.0. By default, if the agent does not find a valid `token.json`, it attempts to open a local browser window to authenticate. **This will fail or hang in a headless Docker container or remote server.**

### Solution: Volume Mount Pre-authorized Tokens (Recommended for Local Docker)
1. Run the agent locally once on your host machine:
   ```bash
   python3 meal_planning_agent.py
   ```
2. Complete the OAuth flow in your browser. This generates a `token.json` in your project root.
3. Run the Docker container by mounting **both** `credentials.json` and the generated `token.json`:
   ```bash
   docker run -it \
     -v $(pwd)/user_profile.json:/app/user_profile.json \
     -v $(pwd)/credentials.json:/app/credentials.json \
     -v $(pwd)/token.json:/app/token.json \
     meal-planning-agent
   ```

---

## 5. Production Deployment Considerations

If you plan to deploy this agent as a background service or web app in the cloud (e.g., Google Cloud Run, AWS ECS):

1. **Service Accounts**:
   For fully automated environments, refactor the authentication in [tools/calendar_tools.py](file:///tools/calendar_tools.py) to use a **Google Cloud Service Account** instead of User OAuth.
   * Download the Service Account JSON key.
   * Share your Google Calendar with the Service Account's email address (with "Make changes to events" permission).
   * Use `google.oauth2.service_account.Credentials.from_service_account_file()` to authenticate.
2. **Environment Variables**:
   Avoid baking credentials into the Docker image. Pass sensitive configuration (like API keys or service account JSON) using environment variables or secret managers (e.g., Google Secret Manager), and load them in your Python code.

---

## 6. Distributed Tracing (OpenTelemetry)

We have integrated OpenTelemetry into the Meal Planning Agent to support distributed tracing, allowing you to monitor the execution flow, trace LLM chat turns, and track individual tool executions.

### How it Works
* **Telemetry Initialization**: Initialized at startup via `init_telemetry()` in [tools/telemetry.py](file:///tools/telemetry.py).
* **Traced Components**:
  * The main agent turn (`agent_chat_turn` span) is wrapped inside [meal_planning_agent.py](file:///Users/xinyingli/Project/AITraining1/meal_planning_agent.py).
  * Each tool (`get_user_profile`, `update_user_profile`, `schedule_meal`, `list_calendar_events`, `search_web`, `process_payment`) is decorated with `@tracer.start_as_current_span` and records specific attributes (e.g., `payment.amount`, `search.query`).

### Visualizing Traces Locally

1. **Start Jaeger (OTel Collector & UI)**:
   Run the Jaeger all-in-one container:
   ```bash
   docker run --rm -d --name jaeger \
     -p 16686:16686 \
     -p 4317:4317 \
     -p 4318:4318 \
     jaegertracing/all-in-one:latest
   ```
   * Access the Jaeger UI at: http://localhost:16686

2. **Run the Agent**:
   When you run the agent, it will automatically export traces to the local Jaeger collector (via gRPC on port 4317 or HTTP on port 4318) and print them as JSON to the console.
   ```bash
   python3 meal_planning_agent.py
   ```

3. **Configure Endpoint (Optional)**:
   You can override the OTLP exporter endpoint by setting the `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable:
   ```bash
   export OTEL_EXPORTER_OTLP_ENDPOINT="http://your-collector-host:4317"
   python3 meal_planning_agent.py
   ```

---

## 7. Google Enterprise Agent Platform Deployment

For enterprise-grade deployment (e.g., Google Cloud Run, Vertex AI Agent Builder), the application has been restructured to run as a stateless **FastAPI Web Service** and integrate natively with Google Cloud services.

### 1. Architecture Overview
Instead of running as an interactive CLI loop, the agent is wrapped in a FastAPI web server ([app.py](file:///app.py)).
* **Lifespan Initialization**: Initializes OpenTelemetry and registers the Google Cloud Trace exporter when the container starts.
* **Stateless API (`POST /chat`)**: Accepts JSON requests containing `message`, `conversation_id` (optional, for session persistence), and `user_id` (optional, for multi-tenant profiles). Returns the agent's text response and the `conversation_id`.
* **Health Probes (`GET /healthz`)**: Returns a `200 OK` status, satisfying Google Cloud Run's liveness and readiness requirements.

### 2. Google Cloud Services Integration

#### A. Cloud Firestore (User Profiles)
In production, user profiles are stored in **Google Cloud Firestore** rather than a local file:
* **Storage**: Profiles are saved in the `meal_planning_profiles` collection. The document ID corresponds to the `user_id` (defaulting to `default_user`).
* **IAM Authentication**: The Firestore client uses Application Default Credentials (ADC) and inherits permissions from the Cloud Run Service Account. No API keys or JSON credentials need to be baked into the container.
* **Local Fallback**: If the Firestore client cannot be initialized (e.g. during local development), it automatically falls back to the local [user_profile.json](file:///user_profile.json) file.

#### B. Google Cloud Trace (Stackdriver)
Traces are automatically exported to **Google Cloud Trace**:
* **Integration**: The telemetry module ([tools/telemetry.py](file:///tools/telemetry.py)) automatically registers `CloudTraceSpanExporter` alongside the Console and OTLP exporters.
* **Span Flow**: Any request to `POST /chat` generates a parent span `api_chat_request`, which contains child spans for the agent execution and any tool calls (e.g. `get_user_profile`, `search_web`).

#### C. Google Calendar (Application Default Credentials)
The Google Calendar integration ([tools/calendar_tools.py](file:///tools/calendar_tools.py)) has been updated to try **Application Default Credentials (ADC)** first.
* In Cloud Run, it will authenticate using the identity of the Cloud Run Service Account.
* **Setup**: To allow the Service Account to write to your calendar, share the target Google Calendar with the Service Account's email address (e.g. `your-service-account@your-project.iam.gserviceaccount.com`) and grant it **Make changes to events** permission.
* **Local Fallback**: If ADC is not available or fails, it falls back to the local `token.json` / `credentials.json` OAuth flow.

### 3. Required IAM Roles
The Service Account running the Cloud Run service must be granted the following IAM roles in your GCP project:
1. **Cloud Datastore User** (`roles/datastore.user`): To read/write user profiles in Firestore.
2. **Cloud Trace Agent** (`roles/cloudtrace.agent`): To write distributed traces to Google Cloud Trace.

### 4. Deploying to Google Cloud Run
To build and deploy the service to Google Cloud Run, execute the following command in the project root:

```bash
# Build the image using Cloud Builds and deploy it to Cloud Run
gcloud run deploy meal-planning-agent-service \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GEMINI_API_KEY=your-api-key"
```

*Note: For a fully enterprise-managed setup, you can remove the `GEMINI_API_KEY` environment variable and grant the Cloud Run Service Account the **Vertex AI User** (`roles/aiplatform.user`) role, allowing the Google Antigravity SDK to authenticate natively via Vertex AI.*


