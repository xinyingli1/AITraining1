from google.antigravity import LocalAgentConfig, types
from tools.calendar_tools import schedule_meal, list_calendar_events

SYSTEM_INSTRUCTIONS = """
You are the Calendar Scheduler Agent. Your sole responsibility is to manage the user's calendar.
You can list existing events to check availability and schedule new events (meals, grocery trips, cooking sessions).
Always verify availability before scheduling.
"""


def get_agent_config(conversation_id: str, save_dir: str) -> LocalAgentConfig:
    return LocalAgentConfig(
        system_instructions=SYSTEM_INSTRUCTIONS,
        tools=[schedule_meal, list_calendar_events],
        conversation_id=f"{conversation_id}_calendar",
        save_dir=save_dir,
        capabilities=types.CapabilitiesConfig(enable_subagents=False),
    )
