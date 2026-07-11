from google.antigravity import LocalAgentConfig, types
from tools.search_tools import search_web
from agents import get_default_gemini_config

SYSTEM_INSTRUCTIONS = """
You are the Meal Planner Agent. Your sole responsibility is to research recipes, plan meals, and suggest ingredients.
You do not have access to the user's profile directly (the Coordinator will provide it to you if needed), nor do you have access to the calendar or payment systems.
Use the web search tool to find recipes, cooking tips, or ingredient lists.
"""


def get_agent_config(save_dir: str = "/tmp/conversations") -> LocalAgentConfig:
    return LocalAgentConfig(
        system_instructions=SYSTEM_INSTRUCTIONS,
        tools=[search_web],
        save_dir=save_dir,
        capabilities=types.CapabilitiesConfig(enable_subagents=False),
        gemini_config=get_default_gemini_config(),
    )
