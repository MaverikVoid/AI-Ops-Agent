import base64
import re
import json
import os
from groq import Groq
from google.auth.transport.requests import Request
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]
def decode_body(payload):
    """
    Recursively extract email body (text/plain preferred)
    """
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part["body"].get("data")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            # recurse
            result = decode_body(part)
            if result:
                return result
    else:
        data = payload["body"].get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    return ""

def read_unread(gmail_service, max_results: int = 1):
    results = gmail_service.users().messages().list(
        userId="me",
        q="is:unread",
        maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        return None

    msg = messages[0]

    full_msg = gmail_service.users().messages().get(
        userId="me",
        id=msg["id"],
        format="full"
    ).execute()

    headers = full_msg["payload"]["headers"]

    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
    sender = next((h["value"] for h in headers if h["name"] == "From"), "")

    body = decode_body(full_msg["payload"])

    return {
        "message_id": msg["id"],
        "thread_id": full_msg["threadId"],
        "from": sender,
        "subject": subject,
        "body": body,
    }


def clean_email_text(text: str) -> str:
    # Remove URLs
    text = re.sub(r"http[s]?://\S+", "", text)

    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove common boilerplate phrases
    blacklist = [
        "View job",
        "trackingId",
        "midToken",
        "midSig",
        "New jobs match your preferences",
        "Your job alert for"
    ]

    for phrase in blacklist:
        text = text.replace(phrase, "")

    return text.strip()[:800]  # HARD LIMIT
from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
Classify the email into ONE of:
support, sales, ops, spam, urgent

Return ONLY valid JSON:
{
  "intent": "...",
  "confidence": 0.0,
  "reason": "short reason"
}
"""
def classify_email(subject: str, body: str):
    subject = clean_email_text(subject)
    body = clean_email_text(body)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Subject: {subject}\n\nBody:\n{body}"
            }
        ],
        temperature=0
    )

    text = response.choices[0].message.content
    start, end = text.find("{"), text.rfind("}") + 1
    return json.loads(text[start:end])

def generate_reply(intent: str, subject: str, body: str):
    prompt = f"""
You are an operations assistant.

Write a short, professional reply for this email. Make it personalised and it should sound like human.

Intent: {intent}
Subject: {subject}
Body: {body}
The reply should be from "Meet Dabgar". Don't Mention that you are an Operations Assistant.
Tone: polite, concise, professional.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response.choices[0].message.content

from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os

def send_reply(
    gmail_service,
    to_email: str,
    subject: str,
    body: str,
    thread_id: str
):
    if os.getenv("AUTO_SEND_EMAILS") != "true":
        raise RuntimeError("AUTO_SEND_EMAILS is disabled")

    message = MIMEText(body)
    message["to"] = to_email
    message["subject"] = subject

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    payload = {
        "raw": raw_message,
        "threadId": thread_id
    }

    gmail_service.users().messages().send(
        userId="me",
        body=payload
    ).execute()

def mark_as_read(gmail_service, message_id: str):
    """
    Removes the UNREAD label from a Gmail message.
    """
    gmail_service.users().messages().modify(
        userId="me",
        id=message_id,
        body={
            "removeLabelIds": ["UNREAD"]
        }
    ).execute()

def get_gmail_credentials():
    creds = Credentials(
        token=None,  # let Google fetch it
        refresh_token=os.getenv("GMAIL_REFRESH_TOKEN"),
        token_uri=os.getenv("GOOGLE_TOKEN_URI"),
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=[
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]
    )

    # This will auto-refresh if needed
    creds.refresh(Request())
    return creds

from googleapiclient.discovery import build

def get_gmail_service():
    creds = get_gmail_credentials()
    return build("gmail", "v1", credentials=creds)