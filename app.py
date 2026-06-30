import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.antigravity import Agent, LocalAgentConfig, types

# Import the core agent components
from meal_planning_agent import SYSTEM_INSTRUCTIONS, POLICIES
from tools.profile_tools import get_user_profile, update_user_profile
from tools.calendar_tools import schedule_meal, list_calendar_events
from tools.search_tools import search_web
from tools.payment_tools import process_payment
from tools.telemetry import init_telemetry, get_tracer

# Configuration
SAVE_DIR = os.environ.get("CONVERSATION_SAVE_DIR", "/tmp/conversations")
os.makedirs(SAVE_DIR, exist_ok=True)

# Tracer
tracer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tracer
    # Initialize OpenTelemetry on startup
    init_telemetry("meal-planning-agent-service")
    tracer = get_tracer()
    print("Meal Planning Agent Web Service is starting up...")
    yield
    print("Meal Planning Agent Web Service is shutting down...")

app = FastAPI(
    title="Meal Planning Agent Service",
    description="Enterprise API endpoint for the Meal Planning Agent",
    version="1.0.0",
    lifespan=lifespan
)

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    user_id: str | None = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str

@app.get("/healthz")
async def healthz():
    """Liveness and readiness probe for Google Cloud Run."""
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint for interacting with the agent."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # If user_id is provided, set it in the environment so the Firestore profile tool can pick it up.
    # This enables multi-tenant profile management.
    if request.user_id:
        os.environ["USER_ID"] = request.user_id
    else:
        # Default fallback
        os.environ["USER_ID"] = "default_user"

    # Configure the agent specifically for this request's conversation
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
        policies=POLICIES,
        capabilities=types.CapabilitiesConfig(
            enable_subagents=True,
        ),
        conversation_id=request.conversation_id,
        save_dir=SAVE_DIR
    )

    global tracer
    if tracer is None:
        tracer = get_tracer()

    try:
        # Wrap the execution in an OpenTelemetry span
        with tracer.start_as_current_span("api_chat_request") as span:
            span.set_attribute("api.user_id", os.environ["USER_ID"])
            if request.conversation_id:
                span.set_attribute("api.conversation_id", request.conversation_id)
            
            async with Agent(config) as agent:
                # Execute the agent chat
                response = await agent.chat(request.message)
                # Compile the full response text (non-streaming for REST API simplicity)
                response_text = await response.text()
                
                span.set_attribute("api.response_length", len(response_text))
                
                return ChatResponse(
                    response=response_text,
                    conversation_id=agent.conversation_id
                )

    except Exception as e:
        print(f"Error handling chat request: {e}")
        raise HTTPException(status_code=500, detail=str(e))
