import os
import json
import asyncio
import contextvars
from google import genai
from google.genai import types as genai_types
from google.antigravity import types as agy_types
from google.antigravity.hooks import hooks

from tools.profile_tools import update_user_profile
from tools.pii import redact_pii


# Context variable to store the latest user input for the current turn
latest_user_input = contextvars.ContextVar("latest_user_input", default="")


def log_json(severity: str, message: str, **kwargs):
    """Helper to output structured JSON logs compatible with Google Cloud Logging."""
    log_entry = {
        "severity": severity.upper(),
        "message": message,
        "component": "async-memory-generation",
        **kwargs,
    }
    # Print as a single-line JSON string (Cloud Logging parses this automatically)
    print(json.dumps(log_entry), flush=True)


@hooks.pre_turn
async def capture_user_input(data: str) -> agy_types.HookResult:
    """Captures the user's input at the start of the turn."""
    latest_user_input.set(data)
    return agy_types.HookResult(allow=True)


async def extract_and_save_memory(user_input: str, agent_response: str):
    """Asynchronously extracts memories from the turn and updates the user profile."""
    # Redact PII from the inputs before logging or processing
    user_input = redact_pii(user_input)
    agent_response = redact_pii(agent_response)

    # Log the intent to start extraction
    log_json(
        "INFO",
        "Starting asynchronous memory extraction",
        intent="extract_user_preferences",
        stage="started",
        user_input=user_input,
    )


    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            log_json(
                "WARNING",
                "Memory extraction skipped: GEMINI_API_KEY not set",
                intent="extract_user_preferences",
                stage="failed",
                outcome="skipped_no_api_key",
            )
            return

        # Initialize the Google GenAI client
        client = genai.Client(api_key=api_key)

        prompt = f"""
        Analyze the following conversation turn between a User and a Meal Planning Agent.
        Extract any newly mentioned personal food preferences, allergies, or dietary restrictions of the User.
        Only extract information that is explicitly stated or strongly implied as a personal preference/restriction.
        Do not extract general recipe ingredients unless the user explicitly says they like, dislike, or cannot eat them.
        
        User Input: "{user_input}"
        Agent Response: "{agent_response}"
        
        Return a JSON object with the following keys:
        - "preferences": list of strings (e.g. ["likes spicy food", "prefers Italian"])
        - "allergies": list of strings (e.g. ["peanuts", "shellfish"])
        - "restrictions": list of strings (e.g. ["vegetarian", "gluten-free"])
        
        If no new information is mentioned for a category, return an empty list.
        Return ONLY the raw JSON string. Do not wrap in markdown or backticks.
        """

        # Call the Gemini model asynchronously
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )

        result_text = response.text
        if result_text:
            data = json.loads(result_text)
            prefs = data.get("preferences", [])
            allergies = data.get("allergies", [])
            restrs = data.get("restrictions", [])

            if prefs or allergies or restrs:
                # Update the profile (handles Firestore or local file automatically)
                update_user_profile(
                    preferences=prefs, allergies=allergies, restrictions=restrs
                )

                log_json(
                    "INFO",
                    "Successfully extracted new memory and updated user profile",
                    intent="extract_user_preferences",
                    stage="completed",
                    outcome="success",
                    extracted={
                        "preferences": prefs,
                        "allergies": allergies,
                        "restrictions": restrs,
                    },
                )
            else:
                log_json(
                    "INFO",
                    "No new memory extracted from conversation turn",
                    intent="extract_user_preferences",
                    stage="completed",
                    outcome="no_new_info",
                )
    except Exception as e:
        # Log the error but do not disrupt the main agent execution
        log_json(
            "ERROR",
            f"Error generating memory: {str(e)}",
            intent="extract_user_preferences",
            stage="failed",
            outcome="error",
            error=str(e),
        )


@hooks.post_turn
async def post_turn_memory_hook(data: str):
    """Triggered after the turn completes. Spawns the memory extraction in the background."""
    user_input = latest_user_input.get()
    if user_input:
        # Spawn the memory extraction as a background task
        asyncio.create_task(extract_and_save_memory(user_input, data))
