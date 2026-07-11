import json
import os
from typing import Annotated
from pydantic import validate_call, Field
from opentelemetry import trace
from tools.telemetry import get_tracer

from google.cloud import firestore

tracer = get_tracer()

# Store the profile in the user's workspace for easy access
PROFILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "user_profile.json",
)

# Initialize Firestore client with automatic database check and creation
_db = None


def _ensure_firestore_db() -> firestore.Client | None:
    global _db
    if _db is not None:
        return _db

    try:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            try:
                import google.auth
                _, project = google.auth.default()
            except Exception:
                pass

        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        database_id = "(default)"

        # Check and create the Firestore database if it does not exist
        if project:
            try:
                from google.cloud import firestore_admin_v1
                from google.api_core.exceptions import NotFound

                admin = firestore_admin_v1.FirestoreAdminClient()
                db_name = f"projects/{project}/databases/{database_id}"
                try:
                    admin.get_database(name=db_name)
                except NotFound:
                    print(f"Firestore database {database_id} not found in {project}. Creating now...")
                    db_obj = firestore_admin_v1.types.Database(
                        location_id=location,
                        type_=firestore_admin_v1.types.Database.DatabaseType.FIRESTORE_NATIVE,
                    )
                    operation = admin.create_database(
                        parent=f"projects/{project}",
                        database_id=database_id,
                        database=db_obj,
                    )
                    operation.result(timeout=180)
                    print(f"✅ Successfully created Firestore database {database_id} in {project}.")
            except Exception as admin_err:
                # If admin check/creation fails (e.g. local credentials lack admin permission), proceed to client
                pass

        _db = firestore.Client(project=project)
        return _db
    except Exception as e:
        print(f"Could not initialize Firestore client: {e}")
        return None


def _get_firestore_profile() -> dict | None:
    db = _ensure_firestore_db()
    if not db:
        return None
    try:
        user_id = os.environ.get("USER_ID", "default_user")
        doc_ref = db.collection("meal_planning_profiles").document(user_id)
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
    db = _ensure_firestore_db()
    if not db:
        return False
    try:
        user_id = os.environ.get("USER_ID", "default_user")
        doc_ref = db.collection("meal_planning_profiles").document(user_id)
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
@validate_call
def update_user_profile(
    preferences: Annotated[
        list[Annotated[str, Field(min_length=1)]] | None,
        Field(
            default=None,
            description="List of food preferences to add (e.g., ['Italian', 'spicy food']).",
        ),
    ] = None,
    allergies: Annotated[
        list[Annotated[str, Field(min_length=1)]] | None,
        Field(
            default=None,
            description="List of allergies to add (e.g., ['peanuts', 'shellfish']).",
        ),
    ] = None,
    restrictions: Annotated[
        list[Annotated[str, Field(min_length=1)]] | None,
        Field(
            default=None,
            description="List of dietary restrictions to add (e.g., ['vegetarian', 'gluten-free']).",
        ),
    ] = None,
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
        profile["restrictions"] = list(
            set(profile.get("restrictions", []) + restrictions)
        )

    # 3. Save profile
    saved_to_firestore = _update_firestore_profile(profile)
    if not saved_to_firestore:
        # Fallback to local file
        with open(PROFILE_PATH, "w") as f:
            json.dump(profile, f, indent=2)

    return f"Profile updated successfully. Current profile: {json.dumps(profile)}"
