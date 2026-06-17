# src/tools/slack_tools.py
"""
Slack alert helper for the AI Employee Agent.
Provides a single LangChain @tool that posts a formatted message to a
Slack channel. Authentication uses the SLACK_BOT_TOKEN environment
variable.
"""

import os
from typing import Literal

import httpx
from langchain_core.tools import tool  # LangChain 0.2+


@tool
def send_slack_alert(
    channel: str,
    title: str,
    message: str,
    priority: Literal["high", "medium", "low"] = "low",
) -> bool:
    """Post an alert to a Slack channel.

    Parameters
    ----------
    channel: str
        Slack channel name or ID (e.g., "#alerts" or "C01234ABCD").
    title: str
        Short heading for the alert.
    message: str
        Full message body (markdown supported).
    priority: Literal["high","medium","low"]
        Visual priority – high adds a red border, medium amber, low green.

    Returns
    -------
    bool
        True if Slack accepted the message, False otherwise.
    """
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN environment variable not set")

    color_map = {"high": "#FF4B4B", "medium": "#FFAA33", "low": "#36C5F0"}
    payload = {
        "channel": channel,
        "attachments": [
            {
                "color": color_map.get(priority, "#36C5F0"),
                "title": title,
                "text": message,
                "mrkdwn_in": ["text", "title"],
            }
        ],
    }
    try:
        resp = httpx.post(
            "https://slack.com/api/chat.postMessage",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack API error: {data.get('error')}")
        return True
    except Exception as exc:
        raise RuntimeError(f"send_slack_alert failed: {exc}") from exc
