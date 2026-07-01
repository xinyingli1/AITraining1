import os
import json
import asyncio
import pytest
import unittest.mock as mock
from google.antigravity import Agent
from agents.coordinator import (
    get_coordinator_config,
    current_session_id,
    current_save_dir,
)

# Global mock states
mock_profile_data = "{}"
mock_calendar_events = "No events"
recorded_tool_calls = []


# Define mock tools with type hints and docstrings so SDK can generate schemas
def mock_get_user_profile() -> str:
    recorded_tool_calls.append(("get_user_profile", {}))
    return mock_profile_data


def mock_update_user_profile(
    preferences: list[str] = None,
    allergies: list[str] = None,
    restrictions: list[str] = None,
) -> str:
    args = {
        "preferences": preferences,
        "allergies": allergies,
        "restrictions": restrictions,
    }
    recorded_tool_calls.append(("update_user_profile", args))
    return f"Profile updated successfully. Current profile: {json.dumps(args)}"


def mock_schedule_meal(
    summary: str, start_time_iso: str, end_time_iso: str, description: str = ""
) -> str:
    args = {
        "summary": summary,
        "start_time_iso": start_time_iso,
        "end_time_iso": end_time_iso,
        "description": description,
    }
    recorded_tool_calls.append(("schedule_meal", args))
    return f"Successfully scheduled '{summary}' on Google Calendar!"


def mock_list_calendar_events(start_time_iso: str, end_time_iso: str) -> str:
    recorded_tool_calls.append(
        (
            "list_calendar_events",
            {"start_time_iso": start_time_iso, "end_time_iso": end_time_iso},
        )
    )
    return mock_calendar_events


def mock_search_web(query: str) -> str:
    recorded_tool_calls.append(("search_web", {"query": query}))
    return "Mock Search Result: Recipe for Spicy Lentil Soup. Ingredients: lentils, tomatoes, vegetable broth, spices. (Vegetarian, Peanut-free)."


def mock_process_payment(amount: float, item: str, merchant: str) -> str:
    recorded_tool_calls.append(
        ("process_payment", {"amount": amount, "item": item, "merchant": merchant})
    )
    return f"SUCCESS: Payment of ${amount:.2f} to {merchant} for '{item}' was successfully processed."


# Load golden dataset
def load_golden_dataset():
    dataset_path = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
    with open(dataset_path, "r") as f:
        return json.load(f)


@pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY environment variable not set",
)
@pytest.mark.parametrize("test_case", load_golden_dataset())
@pytest.mark.asyncio
@mock.patch("tools.profile_tools.get_user_profile", side_effect=mock_get_user_profile)
@mock.patch(
    "tools.profile_tools.update_user_profile", side_effect=mock_update_user_profile
)
@mock.patch("tools.calendar_tools.schedule_meal", side_effect=mock_schedule_meal)
@mock.patch(
    "tools.calendar_tools.list_calendar_events",
    side_effect=mock_list_calendar_events,
)
@mock.patch("tools.search_tools.search_web", side_effect=mock_search_web)
@mock.patch("tools.payment_tools.process_payment", side_effect=mock_process_payment)
async def test_agent_scenarios(
    mock_pay, mock_search, mock_list_cal, mock_sched, mock_upd_prof, mock_get_prof, test_case
):
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
        mock_calendar_events = (
            "No events scheduled in this time range. You are free!"
        )

    # Configure the Coordinator agent for the test
    conversation_id = "eval_session"
    save_dir = "/tmp/conversations"
    config = get_coordinator_config(conversation_id, save_dir)

    user_approve = test_case.get("user_approve_payment", "yes")

    # Set the session context for the worker tools
    current_session_id.set(conversation_id)
    current_save_dir.set(save_dir)

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
            assert (
                expected_tool in called_tool_names
            ), f"Expected tool '{expected_tool}' was not called. Called tools: {called_tool_names}"

        # 2. Assert expected tool arguments if specified
        if "expected_tool_args" in test_case:
            expected_args = test_case["expected_tool_args"]
            # Find the corresponding tool call
            matching_call = None
            for call in recorded_tool_calls:
                if (
                    call[0] == list(test_case["expected_tool_args"].keys())[0]
                    or len(recorded_tool_calls) == 1
                ):
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
            assert (
                expected_out.lower() in full_response.lower()
            ), f"Expected '{expected_out}' in response, but got: {full_response}"

        # 4. Assert prohibited output substrings (e.g., allergies)
        for prohibited_out in test_case.get("prohibited_outputs", []):
            assert (
                prohibited_out.lower() not in full_response.lower()
            ), f"Prohibited '{prohibited_out}' found in response: {full_response}"
