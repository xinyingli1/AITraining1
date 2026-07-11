from google.antigravity import LocalAgentConfig, types
from tools.calendar_tools import schedule_meal, list_calendar_events
from agents import get_default_gemini_config

SYSTEM_INSTRUCTIONS = """
You are the Calendar Scheduler Agent. Your sole responsibility is to manage the user's calendar.
You can list existing events to check availability and schedule new events (meals, grocery trips, cooking sessions).
Always verify availability before scheduling.
"""

def get_agent_config(save_dir: str = "/tmp/conversations") -> LocalAgentConfig:
    return LocalAgentConfig(
        system_instructions=SYSTEM_INSTRUCTIONS,
        tools=[schedule_meal, list_calendar_events],
        save_dir=save_dir,
        capabilities=types.CapabilitiesConfig(enable_subagents=False),
        gemini_config=get_default_gemini_config(),
    )
