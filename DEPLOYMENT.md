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
8. [Infrastructure as Code (Terraform)](#8-infrastructure-as-code-terraform)




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

#### 1. Architecture Overview
Instead of a single monolithic agent, the system is designed as a **Coordinator-based Multi-Agent System** ([agents/coordinator.py](file:///agents/coordinator.py)) wrapped in a FastAPI web server ([app.py](file:///app.py)):

*   **Coordinator Agent**: A central orchestrator that analyzes the user's request, plans the execution steps, delegates tasks to specialized subagents by calling them as tools, and compiles the final response.
*   **Specialized Subagents**:
    *   **Profile Agent** ([agents/profile_agent.py](file:///agents/profile_agent.py)): Manages user profiles (preferences, allergies, restrictions).
    *   **Meal Planner Agent** ([agents/planner_agent.py](file:///agents/planner_agent.py)): Researches recipes and plans meals.
    *   **Calendar Agent** ([agents/calendar_agent.py](file:///agents/calendar_agent.py)): Handles calendar lookups and event scheduling.
    *   **Payment Agent** ([agents/payment_agent.py](file:///agents/payment_agent.py)): Processes purchases under strict safety policies.
*   **Lifespan Initialization**: Initializes OpenTelemetry and registers the Google Cloud Trace exporter when the container starts.
*   **Stateless API (`POST /chat`)**: Accepts JSON requests containing `message`, `conversation_id` (optional, for session persistence), and `user_id` (optional, for multi-tenant profiles). Returns the Coordinator's aggregated text response and the `conversation_id`.
*   **Health Probes (`GET /healthz`)**: Returns a `200 OK` status, satisfying Google Cloud Run's liveness and readiness requirements.
*   **History Compaction**: The Coordinator is configured with `compaction_threshold = 10000` (tokens). When its history exceeds this size, the SDK automatically compacts it. A custom `on_compaction` hook is registered to log these events.
*   **Asynchronous Memory Generation**: The Coordinator is configured with `capture_user_input` and `post_turn_memory_hook` hooks. After every turn, the Coordinator asynchronously analyzes the latest user message and response in the background, extracts new food preferences/allergies/restrictions, and silently updates the user's profile in Firestore (or local file).

For a detailed breakdown of the multi-agent design, see [multi_agent_design.md](file:///Users/xinyingli/.gemini/jetski/brain/304cf2e2-a6af-4635-a950-becde08906ad/multi_agent_design.md).



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

### 5. Structured JSON Logging
To integrate natively with **Google Cloud Logging (Stackdriver)**, components like the asynchronous memory generator ([tools/memory.py](file:///tools/memory.py)) output structured JSON logs instead of plain text:
* **Log Format**: Logs are printed to standard output as a single-line JSON object containing fields like `severity` (e.g. `INFO`, `ERROR`, `WARNING`), `message`, `component`, `intent`, `stage`, and `outcome`.
* **Automatic Parsing**: Google Cloud Run automatically captures and parses these JSON objects, mapping them to the correct severity levels and structured payload fields in your Cloud Logging console, allowing for easy querying and alerting.

### 6. PII Redaction & Data Privacy
The agent implements a multi-layered **PII Redaction system** ([tools/pii.py](file:///tools/pii.py)) to protect user privacy and comply with data safety regulations:
* **Query Redaction**: Before sending search queries to external search engines (via DuckDuckGo), the agent automatically redacts emails, phone numbers, credit card numbers, and SSNs.
* **Anonymized Memory Generation**: The asynchronous memory generator redacts PII from the conversation turn before sending it to Gemini, ensuring that no sensitive user data is processed or stored in user profiles.
* **Telemetry Redaction (`PiiRedactingSpanProcessor`)**: A custom OpenTelemetry `SpanProcessor` is registered first in the tracer provider. When any span ends, the processor automatically scans and redacts PII from all span attributes in-place. This guarantees that no PII is ever exported to Jaeger, Google Cloud Trace, or console logs.

### 7. Deployment via Agents CLI (GCP Agent Runtime)
For automated deployment to the hosted **Google Cloud Agent Runtime**, you can use the official **Agents CLI** (`agents-cli`) or the **ADK** tool:

#### Option A: Using `agents-cli` (Recommended)
1. **Install the CLI**:
   ```bash
   pip install google-agents-cli uv
   agents-cli setup
   ```
2. **Scaffold Deployment Configs**:
   Enhance your existing project directory with the required Agent Runtime configuration files (including `pyproject.toml` and build scripts):
   ```bash
   agents-cli scaffold enhance --deployment-target agent_engine
   ```
3. **Connect to Google Cloud**:
   Authenticate and set your target GCP project:
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```
4. **Deploy**:
   ```bash
   agents-cli deploy
   ```
   This command automatically builds the container, pushes it to Google Artifact Registry, and deploys it to the Agent Runtime environment configured in `pyproject.toml`.

#### Option B: Using the `adk` CLI
Alternatively, you can deploy directly using the `adk` CLI tool:
```bash
uv run adk deploy agent_engine meal_planning_agent \
  --project="YOUR_PROJECT_ID" \
  --region="us-central1"
```

---

## 8. Infrastructure as Code (Terraform)

We use **Terraform** to provision and manage the Google Cloud resources required for the enterprise deployment. The Terraform files are located in the [terraform/](file:///terraform/) directory.

### Resources Provisioned
1. **Service Account**: A dedicated service account `meal-planning-agent-sa` for the Cloud Run service.
2. **Firestore Database**: A default Native-mode Firestore instance (`(default)`) for storing user profiles.
3. **IAM Bindings**:
   * **Cloud Datastore User** (`roles/datastore.user`): Granted to the service account to access Firestore.
   * **Cloud Trace Agent** (`roles/cloudtrace.agent`): Granted to the service account to write telemetry spans to Cloud Trace.
   * **Vertex AI User** (`roles/aiplatform.user`): Granted to the service account to allow it to access Gemini models via Vertex AI without needing an API key.
4. **Cloud Run Service (v2)**: Deploys the FastAPI container with the specified service account and environment variables.
5. **IAM Policy**: Configures public, unauthenticated access (`allUsers` as `roles/run.invoker`) to the Cloud Run endpoint.

### How to Deploy using Terraform

1. **Change to the terraform directory**:
   ```bash
   cd terraform
   ```

2. **Initialize Terraform**:
   ```bash
   terraform init
   ```

3. **Configure Variables**:
   Create a `terraform.tfvars` file to specify your GCP project and Docker image:
   ```hcl
   project_id = "your-gcp-project-id"
   region     = "us-central1"
   image_url  = "us-central1-docker.pkg.dev/your-gcp-project-id/your-repo/meal-planning-agent:latest"
   
   # Optional: Provide if you do not want to use Vertex AI IAM authentication
   # gemini_api_key = "your-api-key"
   ```

4. **Plan the Deployment**:
   Verify the resources that will be created:
   ```bash
   terraform plan
   ```

5. **Apply the Configuration**:
   Deploy the infrastructure:
   ```bash
   terraform apply
   ```

6. **Retrieve the URL**:
   After the deployment completes, Terraform will output the public URL of your Cloud Run service:
   ```bash
   # Example output:
   # service_url = "https://meal-planning-agent-service-xxxxxx.a.run.app"
   ```



