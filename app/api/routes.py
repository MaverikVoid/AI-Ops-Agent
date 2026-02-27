from fastapi import APIRouter
from app.api.state import graph, EmailState
from google_auth_oauthlib.flow import Flow
import os
router = APIRouter()

# store last interrupt in memory (temporary storage)
LAST_INTERRUPT = None
LAST_STATE = None

@router.post("/run")
def run_agent():
    global LAST_INTERRUPT, LAST_STATE

    initial_state: EmailState = {
        "email_id": None,
        "thread_id": None,
        "from_addr": None,
        "subject": None,
        "body": None,
        "intent": None,
        "intent_confidence": None,
        "intent_reason": None,
        "action": None,
        "draft_reply": None,
        "approved": None,
    }

    result = graph.invoke(initial_state)

    # interrupt triggered
    if "__interrupt__" in result:
        LAST_INTERRUPT = result["__interrupt__"]
        LAST_STATE = result
        return {
            "status": "needs_approval",
            "data": LAST_INTERRUPT
        }

    return {
        "status": "completed",
        "result": result
    }

@router.post("/approve")
def approve_email(approved: bool, edited_reply: str | None = None):
    global LAST_STATE

    if LAST_STATE is None:
        return {"error": "No pending approval"}

    state = LAST_STATE.copy()
    state["approved"] = approved

    if edited_reply:
        state["draft_reply"] = edited_reply

    # ⭐ IMPORTANT FIX
    state.pop("__interrupt__", None)

    result = graph.invoke(state)


    return {
        "status": "resumed",
        "result": result
    }

auth_router = APIRouter(prefix = "/auth")

SCOPES=[
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

# @auth_router.get("/login")
# def login():
#     flow = Flow.from_client_secrets_file(
#         "client_secret.json",
#         scopes=SCOPES,
#         redirect_uri = "http://localhost:8000/auth/callback"
#     )
#     auth_url, _ = flow.authorization_url(prompt="consent")
#     return {"auth":auth_url}

# @auth_router.get("/callback")
# def callback(code:str):
#     flow = Flow.from_client_secrets_file(
#         "client_secret.json",
#         scopes=SCOPES,
#         redirect_uri = "http://localhost:8000/auth/callback"
#     )
#     flow.fetch_token(code=code)
#     creds = flow.credentials

#     return {
#         "access_token" : creds.token,
#         "refresh_token": creds.refresh_token
#     }
def get_flow():
    """
    Creates the OAuth flow. Uses environment variables if available (Production),
    otherwise falls back to the client_secret.json file (Local).
    """
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
    
    # Check if we are on Render (using Env Vars)
    if os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"):
        client_config = {
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        return Flow.from_client_config(
            client_config, 
            scopes=SCOPES, 
            redirect_uri=redirect_uri
        )
    
    # Fallback for local development
    return Flow.from_client_secrets_file(
        "client_secret.json",
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

@auth_router.get("/login")
def login():
    flow = get_flow()  # Use the helper
    auth_url, _ = flow.authorization_url(prompt="consent")
    return {"auth": auth_url}

@auth_router.get("/callback")
def callback(code: str):
    flow = get_flow()  # Use the helper
    flow.fetch_token(code=code)
    creds = flow.credentials

    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token
    }
