import os
import json
import pytest
from tools import profile_tools


@pytest.fixture
def temp_profile_path(tmp_path, monkeypatch):
    # Create a temporary file path for the profile
    temp_file = tmp_path / "user_profile.json"
    # Monkeypatch the PROFILE_PATH in profile_tools to point to our temp file
    monkeypatch.setattr(profile_tools, "PROFILE_PATH", str(temp_file))
    return temp_file


def test_get_user_profile_creates_default_if_not_exists(temp_profile_path):
    # Ensure file doesn't exist initially
    assert not os.path.exists(temp_profile_path)

    # Call get_user_profile
    profile_str = profile_tools.get_user_profile()

    # Check that file was created
    assert os.path.exists(temp_profile_path)

    # Check content
    profile_data = json.loads(profile_str)
    assert profile_data == {"preferences": [], "allergies": [], "restrictions": []}


def test_get_user_profile_reads_existing(temp_profile_path):
    # Pre-populate the file
    existing_data = {
        "preferences": ["Spicy"],
        "allergies": ["Peanuts"],
        "restrictions": ["Vegetarian"],
    }
    with open(temp_profile_path, "w") as f:
        json.dump(existing_data, f)

    profile_str = profile_tools.get_user_profile()
    profile_data = json.loads(profile_str)
    assert profile_data == existing_data


def test_update_user_profile(temp_profile_path):
    # Initial update
    profile_tools.update_user_profile(
        preferences=["Italian"], allergies=["Peanuts"], restrictions=["Gluten-Free"]
    )

    # Verify file content
    with open(temp_profile_path, "r") as f:
        data = json.load(f)
    assert "Italian" in data["preferences"]
    assert "Peanuts" in data["allergies"]
    assert "Gluten-Free" in data["restrictions"]

    # Cumulative update (should not duplicate and should append)
    profile_tools.update_user_profile(
        preferences=["Italian", "Mexican"], allergies=["Shellfish"]
    )

    with open(temp_profile_path, "r") as f:
        data = json.load(f)
    assert set(data["preferences"]) == {"Italian", "Mexican"}
    assert set(data["allergies"]) == {"Peanuts", "Shellfish"}
    assert set(data["restrictions"]) == {"Gluten-Free"}


def test_update_user_profile_invalid_arguments(temp_profile_path):
    from pydantic import ValidationError

    # Test empty string inside list
    with pytest.raises(ValidationError):
        profile_tools.update_user_profile(preferences=[""])

    # Test invalid type (string instead of list)
    with pytest.raises(ValidationError):
        profile_tools.update_user_profile(preferences="Italian")  # type: ignore
