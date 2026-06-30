import os
import json
import asyncio
import pytest
import unittest.mock as mock
from google.antigravity import Agent, LocalAgentConfig
from google.antigravity.hooks import policy
from meal_planning_agent import SYSTEM_INSTRUCTIONS, payment_confirmation_handler

# Global mock states
mock_profile_data = "{}"
mock_calendar_events = "No events"
recorded_tool_calls = []

# Define mock tools with type hints and docstrings so SDK can generate schemas
def get_user_profile() -> str:
    """Retrieves the user's profile containing dietary preferences, allergies, and restrictions.
    
    Returns:
        A JSON string containing the user's profile.
    """
    recorded_tool_calls.append(("get_user_profile", {}))
    return mock_profile_data

def update_user_profile(preferences: list[str] = None, allergies: list[str] = None, restrictions: list[str] = None) -> str:
    """Updates the user's profile with new preferences, allergies, or restrictions.
    
    Returns:
        A message indicating the profile was updated.
    """
    args = {"preferences": preferences, "allergies": allergies, "restrictions": restrictions}
    recorded_tool_calls.append(("update_user_profile", args))
    return f"Profile updated successfully. Current profile: {json.dumps(args)}"

def schedule_meal(summary: str, start_time_iso: str, end_time_iso: str, description: str = "") -> str:
    """Schedules a meal, grocery shopping trip, or cooking session on the user's Google Calendar.
    
    Returns:
        A success message with the event link.
    """
    args = {"summary": summary, "start_time_iso": start_time_iso, "end_time_iso": end_time_iso, "description": description}
    recorded_tool_calls.append(("schedule_meal", args))
    return f"Successfully scheduled '{summary}' on Google Calendar!"

def list_calendar_events(start_time_iso: str, end_time_iso: str) -> str:
    """Lists Google Calendar events within a specific time range to help identify free slots.
    
    Returns:
        A list of scheduled events.
    """
    recorded_tool_calls.append(("list_calendar_events", {"start_time_iso": start_time_iso, "end_time_iso": end_time_iso}))
    return mock_calendar_events

def search_web(query: str) -> str:
    """Performs a web search to find recipes, cooking ideas, local grocery stores, or restaurants.
    
    Returns:
        A search result snippet.
    """
    recorded_tool_calls.append(("search_web", {"query": query}))
    # Return a recipe that respects restrictions (vegetarian, peanut-free) if those are common
    return "Mock Search Result: Recipe for Spicy Lentil Soup. Ingredients: lentils, tomatoes, vegetable broth, spices. (Vegetarian, Peanut-free)."

def process_payment(amount: float, item: str, merchant: str) -> str:
    """Processes a payment for groceries, meal kits, or restaurant orders.
    
    Returns:
        A confirmation message of the transaction.
    """
    recorded_tool_calls.append(("process_payment", {"amount": amount, "item": item, "merchant": merchant}))
    return f"SUCCESS: Payment of ${amount:.2f} to {merchant} for '{item}' was successfully processed."


# Load golden dataset
def load_golden_dataset():
    dataset_path = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
    with open(dataset_path, "r") as f:
        return json.load(f)

@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY environment variable not set")
@pytest.mark.parametrize("test_case", load_golden_dataset())
@pytest.mark.asyncio
async def test_agent_scenarios(test_case):
    global mock_profile_data, mock_calendar_events, recorded_tool_calls
    
    # Reset recorded tool calls
    recorded_tool_calls.clear()
    
    # Set up mock states for this test case
    mock_profile_data = json.dumps(test_case.get("profile", {}))
    
    events = test_case.get("calendar_events", [])
    if events:
        events_str = "Scheduled events in this time range:\n"
        for e in events:
            events_str += f"- {e['summary']} ({e['start']} to {e['end']})\n"
        mock_calendar_events = events_str
    else:
        mock_calendar_events = "No events scheduled in this time range. You are free!"

    # Configure the test agent
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
        policies=[
            policy.deny("run_command"),
            policy.ask_user("process_payment", handler=payment_confirmation_handler, when=lambda args: args.get("amount", 0) >= 10.0),
            policy.allow("process_payment", when=lambda args: args.get("amount", 0) < 10.0),
            policy.allow_all(),
        ]
    )

    # We patch the builtins.input to simulate the user's choice for payment confirmation
    user_approve = test_case.get("user_approve_payment", "yes")
    
    async with Agent(config) as agent:
        with mock.patch("builtins.input", return_value=user_approve):
            # Run the agent chat
            response_chunks = []
            response = await agent.chat(test_case["user_input"])
            async for chunk in response:
                response_chunks.append(chunk)
            
            full_response = "".join(response_chunks)

        # 1. Assert expected tool calls were made
        called_tool_names = [call[0] for call in recorded_tool_calls]
        for expected_tool in test_case.get("expected_tool_calls", []):
            assert expected_tool in called_tool_names, f"Expected tool '{expected_tool}' was not called. Called tools: {called_tool_names}"

        # 2. Assert expected tool arguments if specified
        if "expected_tool_args" in test_case:
            expected_args = test_case["expected_tool_args"]
            # Find the corresponding tool call
            matching_call = None
            for call in recorded_tool_calls:
                if call[0] == list(test_case["expected_tool_args"].keys())[0] or len(recorded_tool_calls) == 1:
                    # Just check if we can find a call matching the expected args
                    matching_call = call
                    break
            if matching_call:
                actual_args = matching_call[1]
                for k, v in expected_args.items():
                    # For floats, do approximate check
                    if isinstance(v, float):
                        assert abs(actual_args.get(k, 0) - v) < 0.01
                    else:
                        assert actual_args.get(k) == v

        # 3. Assert expected output substrings
        for expected_out in test_case.get("expected_outputs", []):
            assert expected_out.lower() in full_response.lower(), f"Expected '{expected_out}' in response, but got: {full_response}"

        # 4. Assert prohibited output substrings (e.g., allergies)
        for prohibited_out in test_case.get("prohibited_outputs", []):
            assert prohibited_out.lower() not in full_response.lower(), f"Prohibited '{prohibited_out}' found in response: {full_response}"
