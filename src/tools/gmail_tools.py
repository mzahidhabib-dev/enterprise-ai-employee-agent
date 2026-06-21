# src/tools/gmail_tools.py
"""
Gmail integration utilities for the AI Employee Agent.

Each function is exposed as a LangChain @tool, making it callable from
agent nodes (e.g. fetch_unread_emails, mark_email_read, send_reply).
OAuth2 credentials are read from environment variables:

- GMAIL_CLIENT_ID
- GMAIL_CLIENT_SECRET
- GMAIL_REFRESH_TOKEN
"""

import os
import base64
from typing import List, Dict

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from langchain_core.tools import tool  # LangChain 0.2+


def _build_service() -> "Resource":
    """Create an authorized Gmail API service instance using the refresh token flow."""
    creds = Credentials(
        token=None,
        refresh_token=os.getenv("GMAIL_REFRESH_TOKEN"),
        client_id=os.getenv("GMAIL_CLIENT_ID"),
        client_secret=os.getenv("GMAIL_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
    )
    try:
        return build("gmail", "v1", credentials=creds, cache_discovery=False)
    except Exception as exc:
        raise RuntimeError(f"Gmail service creation failed: {exc}") from exc


@tool
def fetch_unread_emails(max_results: int = 10) -> List[Dict]:
    """Retrieve up‑to `max_results` unread emails from the user's Gmail inbox.

    Returns a list of dicts with keys: id, threadId, subject, from, snippet, body.
    """
    service = _build_service()
    try:
        response = (
            service.users()
            .messages()
            .list(userId="me", q="is:unread", maxResults=max_results)
            .execute()
        )
        messages = response.get("messages", [])
        results: List[Dict] = []
        for msg in messages:
            msg_detail = (
                service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="full")
                .execute()
            )
            payload = msg_detail.get("payload", {})
            headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
            # Extract plain‑text body if present
            body = ""
            for part in payload.get("parts", []):
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        # Gmail uses urlsafe base64 encoding
                        decoded_bytes = base64.urlsafe_b64decode(data)
                        body = decoded_bytes.decode("utf-8", errors="replace")
                        break
            results.append(
                {
                    "id": msg_detail["id"],
                    "threadId": msg_detail["threadId"],
                    "subject": headers.get("Subject", ""),
                    "from": headers.get("From", ""),
                    "snippet": msg_detail.get("snippet", ""),
                    "body": body,
                }
            )
        return results
    except HttpError as err:
        raise RuntimeError(f"Gmail fetch_unread_emails failed: {err}") from err


@tool
def mark_email_read(message_id: str) -> bool:
    """Mark a Gmail message as read (remove the UNREAD label)."""
    service = _build_service()
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()
        return True
    except HttpError as err:
        raise RuntimeError(f"mark_email_read failed for {message_id}: {err}") from err


@tool
def send_reply(to: str, subject: str, body: str, thread_id: str) -> bool:
    """Send a reply email preserving the original thread.

    Parameters
    ----------
    to: str – recipient address
    subject: str – subject line (will be prefixed with "Re: " if needed)
    body: str – plain‑text body
    thread_id: str – Gmail thread ID for the reply
    """
    from email.mime.text import MIMEText
    import base64

    service = _build_service()
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    try:
        service.users().messages().send(
            userId="me",
            body={"raw": raw_message, "threadId": thread_id},
        ).execute()
        return True
    except HttpError as err:
        raise RuntimeError(f"send_reply failed: {err}") from err
