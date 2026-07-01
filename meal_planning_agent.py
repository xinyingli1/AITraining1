import asyncio
import os

# Prevent local connections (like the localharness WebSocket) from routing through the proxy
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

from google.antigravity import Agent

# Import custom tools
from tools.profile_tools import get_user_profile
from tools.telemetry import init_telemetry, get_tracer
from agents.coordinator import (
    get_coordinator_config,
    current_session_id,
    current_save_dir,
    ensure_trajectory_exists,
)


# System instructions to define the agent's persona and responsibilities
SYSTEM_INSTRUCTIONS = """You are the "Meal Planning Agent", a helpful personal assistant dedicated to automating meal planning for the user.

Your core responsibilities:
1. **Understand & Remember User Profile**: 
   - Always check the user's profile using `get_user_profile` to know their dietary preferences, allergies, and restrictions.
   - If the user mentions new preferences, allergies, or restrictions, update their profile using `update_user_profile`.
   - STRICTLY respect all allergies and restrictions in any meal plans or recipes you suggest.

2. **Plan & Schedule Meals**:
   - Create weekly or daily meal plans based on the user's profile.
   - Use `list_calendar_events` to check the user's calendar before scheduling meals, cooking sessions, or grocery trips to avoid conflicts.
   - Use `schedule_meal` to add planned meals, grocery shopping, or cooking sessions to the user's Google Calendar.

3. **Search for Recipes & Ideas**:
   - Use `search_web` to find recipes, cooking ideas, local grocery stores, or restaurants.
   - When suggesting recipes, summarize the ingredients and cooking steps, and provide the URL for reference.

4. **Handle Purchases & Orders**:
   - If the user wants to buy groceries, order meal kits, or order from a restaurant, use the `process_payment` tool.
   - Note: The system will automatically intercept `process_payment` and ask the user for explicit confirmation before proceeding. You do not need to ask manually in text before calling the tool, but you must explain what you are about to purchase.

5. **Delegation**:
   - You can spawn specialized subagents (A2A) to delegate subtasks if needed (e.g., a "Nutritionist Agent" to analyze a recipe, or a "Recipe Finder Agent" to compile options).

Be friendly, organized, and proactive in helping the user manage their meals.
"""


async def main():

    # Initialize telemetry
    init_telemetry()
    tracer = get_tracer()

    # Create the coordinator configuration
    conversation_id = "cli_session"
    save_dir = "/tmp/conversations"

    # Ensure the trajectory file exists so the harness doesn't fail
    ensure_trajectory_exists(conversation_id, save_dir)

    config = get_coordinator_config(conversation_id, save_dir)

    print("Initializing Meal Planning Agent...")
    async with Agent(config) as agent:
        print("\n==================================================")
        print("      Meal Planning Agent is now ONLINE!         ")
        print("  Type your requests (e.g., 'Plan dinner for tonight')")
        print("  Type 'exit' or 'quit' to end the session.       ")
        print("==================================================\n")

        # Display current profile if it exists
        try:
            profile_str = get_user_profile()
            print(f"Current User Profile: {profile_str}\n")
        except Exception:
            pass

        loop = asyncio.get_event_loop()
        while True:
            try:
                user_input = await loop.run_in_executor(None, lambda: input("You: "))
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye!")
                break

            if user_input.strip().lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            if not user_input.strip():
                continue

            print("Agent: ", end="", flush=True)
            try:
                # Wrap the chat interaction in a span for distributed tracing
                with tracer.start_as_current_span("agent_chat_turn") as span:
                    span.set_attribute("chat.user_message", user_input)

                    # Set the session context for the worker tools
                    current_session_id.set(agent.conversation_id or conversation_id)
                    current_save_dir.set(save_dir)

                    response = await agent.chat(user_input)

                    response_chunks = []
                    async for chunk in response:
                        print(chunk, end="", flush=True)
                        response_chunks.append(chunk)
                    print()
                    span.set_attribute("agent.response", "".join(response_chunks))
            except Exception as e:
                print(f"\nAn error occurred: {e}")


if __name__ == "__main__":
    # Ensure we can run async main
    asyncio.run(main())
