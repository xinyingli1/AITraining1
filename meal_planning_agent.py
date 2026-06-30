import asyncio
import os
import sys
from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import policy

# Import custom tools
from tools.profile_tools import get_user_profile, update_user_profile
from tools.calendar_tools import schedule_meal, list_calendar_events
from tools.search_tools import search_web
from tools.payment_tools import process_payment

# Define the safety policy handler for payments
async def payment_confirmation_handler(tool_call) -> bool:
    args = tool_call.args
    amount = args.get("amount")
    item = args.get("item")
    merchant = args.get("merchant")
    
    print(f"\n==================================================")
    print(f"⚠️  [PAYMENT AUTHORIZATION REQUIRED] ⚠️")
    print(f"The Meal Planning Agent is requesting to pay:")
    print(f"  - Amount  : ${amount:.2f}")
    print(f"  - Item    : {item}")
    print(f"  - Merchant: {merchant}")
    print(f"==================================================")
    
    loop = asyncio.get_event_loop()
    while True:
        # Run input() in an executor to avoid blocking the async event loop
        choice = await loop.run_in_executor(None, lambda: input("Do you approve this payment? (yes/no): ").strip().lower())
        if choice in ['y', 'yes']:
            print("✅ Payment approved.")
            return True
        elif choice in ['n', 'no']:
            print("❌ Payment denied.")
            return False
        else:
            print("Please enter 'yes' or 'no'.")

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
    # Configure safety policies
    policies = [
        # Deny run_command completely for safety
        policy.deny("run_command"),
        # Intercept process_payment and require user approval
        policy.ask_user("process_payment", handler=payment_confirmation_handler),
        # Allow all other tools
        policy.allow_all(),
    ]

    # Create the agent configuration
    config = LocalAgentConfig(
        system_instructions=SYSTEM_INSTRUCTIONS,
        tools=[
            get_user_profile,
            update_user_profile,
            schedule_meal,
            list_calendar_events,
            search_web,
            process_payment
        ],
        policies=policies,
        capabilities=types.CapabilitiesConfig(
            enable_subagents=True,
        )
    )

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
                
            if user_input.strip().lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
                
            if not user_input.strip():
                continue

            print("Agent: ", end="", flush=True)
            try:
                response = await agent.chat(user_input)
                async for chunk in response:
                    print(chunk, end="", flush=True)
                print()
            except Exception as e:
                print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    # Ensure we can run async main
    asyncio.run(main())
