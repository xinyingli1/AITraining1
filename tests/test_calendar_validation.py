import pytest
from pydantic import ValidationError
from tools import calendar_tools


def test_schedule_meal_validation():
    # Test empty summary
    with pytest.raises(ValidationError):
        calendar_tools.schedule_meal(
            summary="",
            start_time_iso="2026-06-30T19:00:00Z",
            end_time_iso="2026-06-30T20:00:00Z",
        )

    # Test invalid start_time_iso format (missing T)
    with pytest.raises(ValidationError):
        calendar_tools.schedule_meal(
            summary="Dinner",
            start_time_iso="2026-06-30 19:00:00Z",
            end_time_iso="2026-06-30T20:00:00Z",
        )

    # Test invalid end_time_iso format (random string)
    with pytest.raises(ValidationError):
        calendar_tools.schedule_meal(
            summary="Dinner",
            start_time_iso="2026-06-30T19:00:00Z",
            end_time_iso="not-a-date",
        )


def test_list_calendar_events_validation():
    # Test invalid start_time_iso
    with pytest.raises(ValidationError):
        calendar_tools.list_calendar_events(
            start_time_iso="not-a-date", end_time_iso="2026-06-30T20:00:00Z"
        )
