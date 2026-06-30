# Build and Deployment Guide

This document explains the CI/CD pipeline, containerization, and local quality control setup for the **Meal Planning Agent**.

---

## Table of Contents
1. [Local Quality Control (Linting & Testing)](#1-local-quality-control-linting--testing)
2. [CI/CD Pipeline (GitHub Actions)](#2-cicd-pipeline-github-actions)
3. [Containerization (Docker)](#3-containerization-docker)
4. [Handling Google Calendar API in Containerized Environments](#4-handling-google-calendar-api-in-containerized-environments)
5. [Production Deployment Considerations](#5-production-deployment-considerations)

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

### Running Unit Tests
We have implemented unit tests under the `tests/` directory to verify the tool functionalities (such as profile management and payments) without mutating local state.

Run the tests using:
```bash
python3 -m pytest
```

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
