import os
import contextvars
from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import hooks
from tools.memory import capture_user_input, post_turn_memory_hook
from agents import profile_agent, planner_agent, calendar_agent, payment_agent, get_default_gemini_config


@hooks.on_compaction
async def log_compaction(data):
    print(f"\n⚡ [CONTEXT COMPACTION] History was compacted. Details: {data}")


SYSTEM_INSTRUCTIONS = """

You are the Coordinator for the Meal Planning Assistant. Your job is to orchestrate the workflow by delegating tasks to specialized subagents.
You must NOT perform these tasks yourself. Always use the appropriate subagent tool:
- Use `call_profile_agent` to view or update the user's dietary profile (preferences, allergies, restrictions).
- Use `call_meal_planner_agent` to search for recipes, plan dinners, or get ingredient lists.
- Use `call_calendar_agent` to check calendar availability or schedule events.
- Use `call_payment_agent` to process payments for grocery orders or deliveries.

When a user asks a question, break it down, call the necessary subagents, and then compile a friendly, cohesive response for the user.
If a subagent asks for information, provide it if you have it, or ask the user.
"""

# Context variables to pass the current save directory down to the tool calls
current_save_dir = contextvars.ContextVar(
    "current_save_dir", default="/tmp/conversations"
)


def ensure_trajectory_exists(conversation_id: str, save_dir: str):
    """Pre-creates an empty trajectory file if it does not exist, to prevent harness load errors."""
    if conversation_id and save_dir:
        os.makedirs(save_dir, exist_ok=True)
        traj_path = os.path.join(save_dir, f"traj-{conversation_id}")
        if not os.path.exists(traj_path):
            with open(traj_path, "wb") as f:
                f.write(b"")


async def call_profile_agent(prompt: str) -> str:
    """Delegates a task to the Profile Agent. Use this for reading or updating dietary preferences, allergies, or restrictions."""
    save_dir = current_save_dir.get()
    config = profile_agent.get_agent_config(save_dir)
    async with Agent(config) as agent:
        response = await agent.chat(prompt)
        return await response.text()


async def call_meal_planner_agent(prompt: str) -> str:
    """Delegates a task to the Meal Planner Agent. Use this for recipe ideas, dinner suggestions, and meal planning."""
    save_dir = current_save_dir.get()
    config = planner_agent.get_agent_config(save_dir)
    async with Agent(config) as agent:
        response = await agent.chat(prompt)
        return await response.text()


async def call_calendar_agent(prompt: str) -> str:
    """Delegates a task to the Calendar Scheduler Agent. Use this to schedule events, check availability, or list existing calendar entries."""
    save_dir = current_save_dir.get()
    config = calendar_agent.get_agent_config(save_dir)
    async with Agent(config) as agent:
        response = await agent.chat(prompt)
        return await response.text()


async def call_payment_agent(prompt: str) -> str:
    """Delegates a task to the Payment Agent. Use this to process payments for groceries, meal kits, or deliveries."""
    save_dir = current_save_dir.get()
    config = payment_agent.get_agent_config(save_dir)
    async with Agent(config) as agent:
        response = await agent.chat(prompt)
        return await response.text()


def get_coordinator_config(save_dir: str = "/tmp/conversations") -> LocalAgentConfig:
    return LocalAgentConfig(
        system_instructions=SYSTEM_INSTRUCTIONS,
        tools=[
            call_profile_agent,
            call_meal_planner_agent,
            call_calendar_agent,
            call_payment_agent,
        ],
        hooks=[log_compaction, capture_user_input, post_turn_memory_hook],
        capabilities=types.CapabilitiesConfig(
            enable_subagents=True,
            compaction_threshold=10000,
        ),
        save_dir=save_dir,
        gemini_config=get_default_gemini_config(),
    )
