import json
import os

# Store the profile in the user's workspace for easy access
PROFILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_profile.json")

def get_user_profile() -> str:
    """Retrieves the user's profile containing dietary preferences, allergies, and restrictions.
    
    Returns:
        A JSON string containing the user's profile.
    """
    if not os.path.exists(PROFILE_PATH):
        default_profile = {"preferences": [], "allergies": [], "restrictions": []}
        with open(PROFILE_PATH, "w") as f:
            json.dump(default_profile, f, indent=2)
        return json.dumps(default_profile)
    
    with open(PROFILE_PATH, "r") as f:
        return f.read()

def update_user_profile(preferences: list[str] = None, allergies: list[str] = None, restrictions: list[str] = None) -> str:
    """Updates the user's profile with new preferences, allergies, or restrictions.
    
    Args:
        preferences: List of food preferences to add (e.g., ["Italian", "spicy food"]).
        allergies: List of allergies to add (e.g., ["peanuts", "shellfish"]).
        restrictions: List of dietary restrictions to add (e.g., ["vegetarian", "gluten-free"]).
        
    Returns:
        A message indicating the profile was updated, along with the new profile.
    """
    profile = {"preferences": [], "allergies": [], "restrictions": []}
    if os.path.exists(PROFILE_PATH):
        with open(PROFILE_PATH, "r") as f:
            try:
                profile = json.load(f)
            except json.JSONDecodeError:
                pass
                
    if preferences is not None:
        profile["preferences"] = list(set(profile.get("preferences", []) + preferences))
    if allergies is not None:
        profile["allergies"] = list(set(profile.get("allergies", []) + allergies))
    if restrictions is not None:
        profile["restrictions"] = list(set(profile.get("restrictions", []) + restrictions))
        
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)
        
    return f"Profile updated successfully. Current profile: {json.dumps(profile)}"
