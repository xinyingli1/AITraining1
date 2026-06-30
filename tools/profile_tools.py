import json
import os
from opentelemetry import trace
from tools.telemetry import get_tracer
from google.cloud import firestore

tracer = get_tracer()

# Store the profile in the user's workspace for easy access
PROFILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "user_profile.json",
)

# Initialize Firestore client
# If running in GCP, this automatically uses the service account credentials
_db = None
try:
    _db = firestore.Client()
except Exception:
    _db = None


def _get_firestore_profile() -> dict | None:
    if not _db:
        return None
    try:
        user_id = os.environ.get("USER_ID", "default_user")
        doc_ref = _db.collection("meal_planning_profiles").document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            default_profile = {"preferences": [], "allergies": [], "restrictions": []}
            doc_ref.set(default_profile)
            return default_profile
    except Exception as e:
        # Fallback to local file if Firestore is not accessible
        print(f"Firestore error: {e}. Falling back to local file.")
        return None


def _update_firestore_profile(profile: dict) -> bool:
    if not _db:
        return False
    try:
        user_id = os.environ.get("USER_ID", "default_user")
        doc_ref = _db.collection("meal_planning_profiles").document(user_id)
        doc_ref.set(profile)
        return True
    except Exception as e:
        print(f"Firestore error: {e}. Falling back to local file.")
        return False


@tracer.start_as_current_span("get_user_profile")
def get_user_profile() -> str:
    """Retrieves the user's profile containing dietary preferences, allergies, and restrictions.

    Returns:
        A JSON string containing the user's profile.
    """
    # Try Firestore first
    profile_data = _get_firestore_profile()
    if profile_data is not None:
        return json.dumps(profile_data)

    # Fallback to local file
    if not os.path.exists(PROFILE_PATH):
        default_profile = {"preferences": [], "allergies": [], "restrictions": []}
        with open(PROFILE_PATH, "w") as f:
            json.dump(default_profile, f, indent=2)
        return json.dumps(default_profile)

    with open(PROFILE_PATH, "r") as f:
        return f.read()


@tracer.start_as_current_span("update_user_profile")
def update_user_profile(
    preferences: list[str] = None,
    allergies: list[str] = None,
    restrictions: list[str] = None,
) -> str:
    """Updates the user's profile with new preferences, allergies, or restrictions.

    Args:
        preferences: List of food preferences to add (e.g., ["Italian", "spicy food"]).
        allergies: List of allergies to add (e.g., ["peanuts", "shellfish"]).
        restrictions: List of dietary restrictions to add (e.g., ["vegetarian", "gluten-free"]).

    Returns:
        A message indicating the profile was updated, along with the new profile.
    """
    span = trace.get_current_span()
    if preferences:
        span.set_attribute("profile.preferences_added", preferences)
    if allergies:
        span.set_attribute("profile.allergies_added", allergies)
    if restrictions:
        span.set_attribute("profile.restrictions_added", restrictions)

    # 1. Get current profile
    profile = None
    profile_data = _get_firestore_profile()
    if profile_data is not None:
        profile = profile_data
    else:
        # Fallback to local
        profile = {"preferences": [], "allergies": [], "restrictions": []}
        if os.path.exists(PROFILE_PATH):
            with open(PROFILE_PATH, "r") as f:
                try:
                    profile = json.load(f)
                except json.JSONDecodeError:
                    pass

    # 2. Update fields
    if preferences is not None:
        profile["preferences"] = list(set(profile.get("preferences", []) + preferences))
    if allergies is not None:
        profile["allergies"] = list(set(profile.get("allergies", []) + allergies))
    if restrictions is not None:
        profile["restrictions"] = list(set(profile.get("restrictions", []) + restrictions))

    # 3. Save profile
    saved_to_firestore = _update_firestore_profile(profile)
    if not saved_to_firestore:
        # Fallback to local file
        with open(PROFILE_PATH, "w") as f:
            json.dump(profile, f, indent=2)

    return f"Profile updated successfully. Current profile: {json.dumps(profile)}"
