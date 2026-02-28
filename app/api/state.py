from langgraph.graph import StateGraph, START,END
from typing import TypedDict, Optional
import os
from dotenv import load_dotenv
from app.api.helpers import read_unread
from app.api.helpers import classify_email
from app.api.helpers import generate_reply
from app.api.helpers import send_reply, mark_as_read 
from app.api.helpers import get_gmail_service, decode_body
load_dotenv()
# Initialize the Gmail client lazily inside node factories to avoid
# running network/credential refresh at import time.
class EmailState(TypedDict):
    email_id: Optional[str]
    thread_id: Optional[str]
    from_addr: Optional[str]
    subject: Optional[str]
    body: Optional[str]

    intent: Optional[str]
    intent_confidence: Optional[float]
    intent_reason: Optional[str]

    action: Optional[str]
    draft_reply: Optional[str]
    approved: Optional[bool]


from bs4 import BeautifulSoup

def clean_email_body(raw_body: str) -> str:
    soup = BeautifulSoup(raw_body, "html.parser")

    # remove scripts/styles
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    return " ".join(text.split())


def make_fetch_email_node():
    def fetch_email_node(state: EmailState) -> EmailState:
        gmail_service = get_gmail_service()
        email = read_unread(gmail_service)
        if not email:
            raise RuntimeError("No unread emails")

        clean_body = clean_email_body(email["body"])

        return {
            **state,
            "email_id": email["message_id"],
            "thread_id": email["thread_id"],
            "from_addr": email["from"],
            "subject": email["subject"],
            "body": clean_body
        }

    return fetch_email_node

def classify_intent_node(state: EmailState) -> EmailState:
    result = classify_email(
        subject=clean_email_body(state["subject"]),
        body=clean_email_body(state["body"])
    )

    return {
        **state,
        "intent": result["intent"],
        "intent_confidence": result["confidence"],
        "intent_reason": result["reason"]
    }

def decide_action_node(state: EmailState) -> EmailState:
    intent = state["intent"]
    confidence = state["intent_confidence"]

    # High-confidence spam → ignore
    if intent == "spam" and confidence >= 0.7:
        action = "ignore"

    # Urgent or low-confidence → human in loop
    elif intent == "urgent" or confidence < 0.6:
        action = "human_review"

    # Legitimate categories → auto reply
    elif intent in ["support", "sales", "ops"]:
        action = "reply"

    # Fallback safety
    else:
        action = "human_review"

    return {
        **state,
        "action": action
    }

def draft_reply_node(state: EmailState) -> EmailState:
    reply = generate_reply(
        intent=state["intent"],
        subject=state["subject"],
        body=state["body"]
    )

    return {
        **state,
        "draft_reply": reply
    }

from langgraph.types import interrupt

def human_approval_node(state: EmailState) -> EmailState:
    """
    Interrupts the graph and waits for human approval or edit.
    """
    raise interrupt(
        {
            "email_id": state["email_id"],
            "thread_id": state["thread_id"],
            "from": state["from_addr"],
            "subject": state["subject"],
            "draft_reply": state["draft_reply"],
            "message": "Approve, edit, or reject this reply"
        }
    )


def make_send_reply_node():
    def send_reply_node(state: EmailState) -> EmailState:
        gmail_service = get_gmail_service()
        # Safety check (graph-level, not Gmail-level)
        if not state.get("draft_reply"):
            raise RuntimeError("No draft_reply present for send_reply")

        send_reply(
            gmail_service=gmail_service,
            to_email=state["from_addr"],
            subject=state["subject"],
            body=state["draft_reply"],
            thread_id=state["thread_id"],
        )

        # Mark original email as read to avoid reprocessing
        mark_as_read(
            gmail_service,
            state["email_id"]
        )

        return state

    return send_reply_node

def log_result_node(state: EmailState) -> EmailState:
    print("\n=== EMAIL PROCESSED ===")
    print("ID:", state["email_id"])
    print("Subject:", state["subject"])
    print("Intent:", state["intent"])
    print("Action:", state["action"])
    print("======================\n")
    return state


def route_after_decision(state: EmailState):
    if state["action"] == "ignore":
        return "log_result"

    if state["action"] == "reply":
        return "draft_reply"

    if state["action"] == "human_review":
        return "draft_reply"

    # safety fallback
    return "log_result"

def route_after_draft(state: EmailState):

    # Needs approval and not yet approved → go to approval
    if state["action"] == "human_review" and not state.get("approved"):
        return "human_approval"

    # Otherwise continue execution
    return "send_reply"


builder = StateGraph(EmailState)
builder.add_node("fetch_email", make_fetch_email_node())
builder.add_node("classify_intent", classify_intent_node)
builder.add_node("decide_action", decide_action_node)
builder.add_node("draft_reply", draft_reply_node)
builder.add_node("human_approval", human_approval_node)
builder.add_node("send_reply", make_send_reply_node())
builder.add_node("log_result", log_result_node)

builder.set_entry_point("fetch_email")
builder.add_edge("fetch_email", "classify_intent")
builder.add_edge("classify_intent", "decide_action")

builder.add_conditional_edges(
    "decide_action",
    route_after_decision,
    {
        "draft_reply": "draft_reply",
        "log_result": "log_result",
    }
)
builder.add_conditional_edges(
    "draft_reply",
    route_after_draft,
    {
        "human_approval": "human_approval",
        "send_reply": "send_reply",
    }
)
builder.add_edge("send_reply", "log_result")
builder.add_edge("log_result", END)
graph = builder.compile()


if __name__ == "__main__":
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

    if "__interrupt__" in result:
        print("Waiting for approval:")
        print(result["__interrupt__"])

