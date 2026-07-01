from google.antigravity import LocalAgentConfig, types
from tools.search_tools import search_web

SYSTEM_INSTRUCTIONS = """
You are the Meal Planner Agent. Your sole responsibility is to research recipes, plan meals, and suggest ingredients.
You do not have access to the user's profile directly (the Coordinator will provide it to you if needed), nor do you have access to the calendar or payment systems.
Use the web search tool to find recipes, cooking tips, or ingredient lists.
"""


def get_agent_config(conversation_id: str, save_dir: str) -> LocalAgentConfig:
    return LocalAgentConfig(
        system_instructions=SYSTEM_INSTRUCTIONS,
        tools=[search_web],
        conversation_id=f"{conversation_id}_planner",
        save_dir=save_dir,
        capabilities=types.CapabilitiesConfig(enable_subagents=False),
    )
