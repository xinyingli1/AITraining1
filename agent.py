import os
from pathlib import Path
import sys

_AGENT_DIR = Path(__file__).parent.resolve()
if str(_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENT_DIR))

# When deployed on Argolis (Reasoning Engine) without GEMINI_API_KEY, instruct google.antigravity to use Vertex AI ADC
if not os.environ.get("GEMINI_API_KEY") and os.environ.get("GOOGLE_CLOUD_PROJECT"):
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

from google.adk.agents import config_agent_utils
from google.adk.apps import App

root_agent = config_agent_utils.from_config(str(_AGENT_DIR / "root_agent.yaml"))
app = App(root_agent=root_agent, name="meal_planning_agent")
