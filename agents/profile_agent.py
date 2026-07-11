from google.antigravity import LocalAgentConfig, types
from tools.profile_tools import get_user_profile, update_user_profile
from agents import get_default_gemini_config

SYSTEM_INSTRUCTIONS = """
You are the Profile & Memory Agent. Your sole responsibility is to manage the user's dietary profile, preferences, allergies, and restrictions.
You have access to tools to view and update the profile.
Always assist the Coordinator or User in retrieving or updating this information.
Keep your responses concise and factual.
"""


def get_agent_config(save_dir: str = "/tmp/conversations") -> LocalAgentConfig:
    return LocalAgentConfig(
        system_instructions=SYSTEM_INSTRUCTIONS,
        tools=[get_user_profile, update_user_profile],
        save_dir=save_dir,
        capabilities=types.CapabilitiesConfig(enable_subagents=False),
        gemini_config=get_default_gemini_config(),
    )
