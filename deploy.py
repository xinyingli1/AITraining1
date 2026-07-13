import os
import json
from pathlib import Path
from google.adk.cli import cli_deploy

# =====================================================================
# Deployment Configuration
# =====================================================================
PROJECT_ID = "trainingproject1-500718"
REGION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
AGENT_ENGINE_ID = "2486794585599115264"


def main():
    agent_folder = Path(__file__).parent.resolve()
    config_path = agent_folder / ".agent_engine_config.json"

    display_name = "Meal Planning Agent"
    description = "Meal planning assistant with specialized subagents and GCP Logging"

    if config_path.exists():
        print(f"📄 Reading configuration & env_vars from {config_path.name}...")
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
                display_name = config_data.get("display_name", display_name)
                description = config_data.get("description", description)
        except Exception as e:
            print(f"⚠️ Warning reading {config_path.name}: {e}")

    print(f"🚀 Deploying to Agent Engine ({AGENT_ENGINE_ID}) in {PROJECT_ID}/{REGION}...")
    cli_deploy.to_agent_engine(
        agent_folder=str(agent_folder),
        project=PROJECT_ID,
        region=REGION,
        agent_engine_id=AGENT_ENGINE_ID,
        display_name=display_name,
        description=description,
    )

    print("\n✅ Deployment completed successfully!")
    print(f"🔗 Playground: https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/{REGION}/agent-engines/{AGENT_ENGINE_ID}/playground?project={PROJECT_ID}")


if __name__ == "__main__":
    main()
