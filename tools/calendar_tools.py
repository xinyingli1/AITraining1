import os
import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from opentelemetry import trace
from tools.telemetry import get_tracer
from typing import Annotated
from pydantic import validate_call, Field

IsoDateTime = Annotated[
    str,
    Field(
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$",
        description="ISO 8601 datetime string (e.g. 2026-06-30T19:00:00-07:00)",
    ),
]



tracer = get_tracer()

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# We look for credentials in the workspace root
CREDENTIALS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "credentials.json"
)
TOKEN_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "token.json"
)



def get_calendar_service():
    creds = None

    # 1. Try Application Default Credentials (ADC) - standard for Google Cloud/Enterprise
    try:
        creds, _ = google.auth.default(scopes=SCOPES)
        # Refresh the credentials to make sure they are valid
        creds.refresh(Request())
    except Exception:
        creds = None

    # 2. Fallback to local OAuth flow (token.json / credentials.json) for local development
    if not creds:
        if os.path.exists(TOKEN_PATH):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            except Exception:
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None

            if not creds:
                if not os.path.exists(CREDENTIALS_PATH):
                    return None
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        CREDENTIALS_PATH, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    # Save the credentials for the next run
                    with open(TOKEN_PATH, "w") as token:
                        token.write(creds.to_json())
                except Exception as e:
                    print(f"Authentication flow failed: {e}")
                    return None


    try:
        service = build("calendar", "v3", credentials=creds)
        return service
    except Exception as e:
        print(f"Error building calendar service: {e}")
        return None


@tracer.start_as_current_span("schedule_meal")
@validate_call
def schedule_meal(
    summary: Annotated[str, Field(min_length=1, description="The title of the event.")],
    start_time_iso: IsoDateTime,
    end_time_iso: IsoDateTime,
    description: str = "",
) -> str:

    """Schedules a meal, grocery shopping trip, or cooking session on the user's Google Calendar.

    Args:
        summary: The title of the event (e.g., "Dinner: Vegan Chili" or "Grocery Shopping").
        start_time_iso: The start time in ISO 8601 format (e.g., "2026-06-30T19:00:00-07:00").
        end_time_iso: The end time in ISO 8601 format (e.g., "2026-06-30T20:00:00-07:00").
        description: Optional description of the event (e.g., recipe link, ingredients, or notes).

    Returns:
        A success message with the event link, or an error instruction.
    """
    span = trace.get_current_span()
    span.set_attribute("calendar.event_summary", summary)
    span.set_attribute("calendar.start_time", start_time_iso)
    span.set_attribute("calendar.end_time", end_time_iso)

    service = get_calendar_service()
    if not service:
        return (
            "Error: Google Calendar integration is not configured.\n"
            "To enable this, the user must:\n"
            "1. Go to Google Cloud Console (https://console.cloud.google.com/)\n"
            "2. Create a project, enable the Google Calendar API.\n"
            "3. Configure OAuth consent screen and create OAuth 2.0 Client ID credentials.\n"
            "4. Download the credentials JSON, rename it to 'credentials.json', and place it in the project root directory."
        )

    event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_time_iso,
        },
        "end": {
            "dateTime": end_time_iso,
        },
    }

    try:
        event = service.events().insert(calendarId="primary", body=event).execute()
        span.set_attribute("calendar.event_id", event.get("id", ""))
        return f"Successfully scheduled '{summary}' on Google Calendar! Event link: {event.get('htmlLink')}"
    except Exception as e:
        span.record_exception(e)
        return f"Failed to create calendar event: {str(e)}"


@tracer.start_as_current_span("list_calendar_events")
@validate_call
def list_calendar_events(
    start_time_iso: IsoDateTime, end_time_iso: IsoDateTime
) -> str:

    """Lists Google Calendar events within a specific time range to help identify free slots or existing plans.

    Args:
        start_time_iso: Start of the range in ISO 8601 format (e.g., "2026-06-30T00:00:00-07:00").
        end_time_iso: End of the range in ISO 8601 format (e.g., "2026-06-30T23:59:59-07:00").

    Returns:
        A list of scheduled events, or an error/empty message.
    """
    span = trace.get_current_span()
    span.set_attribute("calendar.query_start", start_time_iso)
    span.set_attribute("calendar.query_end", end_time_iso)

    service = get_calendar_service()

    if not service:
        return (
            "Error: Google Calendar integration is not configured. "
            "Please place 'credentials.json' in the project root."
        )

    try:
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_time_iso,
                timeMax=end_time_iso,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            return "No events scheduled in this time range. You are free!"

        result = ["Scheduled events in this time range:"]
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            result.append(f"- {event['summary']} ({start} to {end})")
        return "\n".join(result)
    except Exception as e:
        return f"Failed to list calendar events: {str(e)}"
