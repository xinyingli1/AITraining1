import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

# We look for credentials in the workspace root
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'credentials.json')
TOKEN_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'token.json')

def get_calendar_service():
    creds = None
    
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception:
            creds = None
            
    # If there are no (valid) credentials available, let the user log in.
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
                    CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open(TOKEN_PATH, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                print(f"Authentication flow failed: {e}")
                return None

    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Error building calendar service: {e}")
        return None

def schedule_meal(summary: str, start_time_iso: str, end_time_iso: str, description: str = "") -> str:
    """Schedules a meal, grocery shopping trip, or cooking session on the user's Google Calendar.
    
    Args:
        summary: The title of the event (e.g., "Dinner: Vegan Chili" or "Grocery Shopping").
        start_time_iso: The start time in ISO 8601 format (e.g., "2026-06-30T19:00:00-07:00").
        end_time_iso: The end time in ISO 8601 format (e.g., "2026-06-30T20:00:00-07:00").
        description: Optional description of the event (e.g., recipe link, ingredients, or notes).
        
    Returns:
        A success message with the event link, or an error instruction.
    """
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
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time_iso,
        },
        'end': {
            'dateTime': end_time_iso,
        },
    }
    
    try:
        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Successfully scheduled '{summary}' on Google Calendar! Event link: {event.get('htmlLink')}"
    except Exception as e:
        return f"Failed to create calendar event: {str(e)}"

def list_calendar_events(start_time_iso: str, end_time_iso: str) -> str:
    """Lists Google Calendar events within a specific time range to help identify free slots or existing plans.
    
    Args:
        start_time_iso: Start of the range in ISO 8601 format (e.g., "2026-06-30T00:00:00-07:00").
        end_time_iso: End of the range in ISO 8601 format (e.g., "2026-06-30T23:59:59-07:00").
        
    Returns:
        A list of scheduled events, or an error/empty message.
    """
    service = get_calendar_service()
    if not service:
        return (
            "Error: Google Calendar integration is not configured. "
            "Please place 'credentials.json' in the project root."
        )
        
    try:
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=start_time_iso,
            timeMax=end_time_iso,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        
        if not events:
            return "No events scheduled in this time range. You are free!"
            
        result = ["Scheduled events in this time range:"]
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            result.append(f"- {event['summary']} ({start} to {end})")
        return "\n".join(result)
    except Exception as e:
        return f"Failed to list calendar events: {str(e)}"
