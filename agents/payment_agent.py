import sys
import asyncio
from google.antigravity import LocalAgentConfig, types
from google.antigravity.hooks import policy
from tools.payment_tools import process_payment

SYSTEM_INSTRUCTIONS = """
You are the Payment & Checkout Agent. Your sole responsibility is to process payments for grocery orders, meal kits, or delivery services.
This is a highly sensitive role. Always confirm the exact amount, merchant, and items before processing.
"""


# Define the safety policy handler for payments
async def payment_confirmation_handler(tool_call) -> bool:
    args = tool_call.args
    amount = args.get("amount")
    item = args.get("item")
    merchant = args.get("merchant")

    print("\n==================================================")
    print("⚠️  [PAYMENT AUTHORIZATION REQUIRED] ⚠️")
    print("The Meal Planning Agent is requesting to pay:")
    print(f"  - Amount  : ${amount:.2f}")
    print(f"  - Item    : {item}")
    print(f"  - Merchant: {merchant}")
    print("==================================================")

    # Check if we are running in an interactive terminal
    if not sys.stdin.isatty():
        print(
            "❌ [PAYMENT DENIED] Non-interactive environment detected. Auto-denying payment."
        )
        return False

    loop = asyncio.get_event_loop()
    while True:
        # Run input() in an executor to avoid blocking the async event loop
        choice = await loop.run_in_executor(
            None,
            lambda: input("Do you authorize this payment? (yes/no): ")
            .strip()
            .lower(),
        )
        if choice in ["yes", "y"]:
            print("✅ [PAYMENT APPROVED]")
            return True
        elif choice in ["no", "n"]:
            print("❌ [PAYMENT DENIED]")
            return False
        else:
            print("Please enter 'yes' or 'no'.")


POLICIES = [
    # Add custom payment verification policy
    policy.ask_user(
        "process_payment",
        handler=payment_confirmation_handler,
    ),
    # Allow all other tools
    policy.allow_all(),
]



def get_agent_config(conversation_id: str, save_dir: str) -> LocalAgentConfig:
    return LocalAgentConfig(
        system_instructions=SYSTEM_INSTRUCTIONS,
        tools=[process_payment],
        policies=POLICIES,
        conversation_id=f"{conversation_id}_payment",
        save_dir=save_dir,
        capabilities=types.CapabilitiesConfig(enable_subagents=False),
    )
