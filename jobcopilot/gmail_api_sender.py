"""Send the digest via the Gmail API over HTTPS instead of raw SMTP. Used by the cloud
routine, whose sandbox network policy allows outbound HTTPS to allowlisted domains but
appears to block SMTP (port 465) entirely. Needs only `requests` — no Google client
libraries — since it's just two plain HTTPS calls (refresh the access token, then send).

Requires a one-time local OAuth setup (see scripts/gmail_oauth_setup.py) to obtain a
refresh token, then GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN,
GMAIL_ADDRESS, and DIGEST_RECIPIENT_EMAIL as environment variables.
"""
from __future__ import annotations

import base64
import os
from email.mime.text import MIMEText

import requests

from jobcopilot import email_sender
from jobcopilot.models import ScoredJob

TOKEN_URL = "https://oauth2.googleapis.com/token"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


class GmailApiNotConfigured(Exception):
    pass


def _credentials() -> tuple[str, str, str, str, str]:
    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")
    address = os.environ.get("GMAIL_ADDRESS")
    recipient = os.environ.get("DIGEST_RECIPIENT_EMAIL") or address
    if not all([client_id, client_secret, refresh_token, address, recipient]):
        raise GmailApiNotConfigured(
            "GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET / GMAIL_REFRESH_TOKEN / GMAIL_ADDRESS "
            "/ DIGEST_RECIPIENT_EMAIL not fully set"
        )
    return client_id, client_secret, refresh_token, address, recipient


def _get_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    resp = requests.post(TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()["access_token"]


def send_digest_via_gmail_api(scored_jobs: list[ScoredJob], warnings: list[str]) -> None:
    client_id, client_secret, refresh_token, address, recipient = _credentials()
    subject, html_body = email_sender.build_digest(scored_jobs, warnings)

    access_token = _get_access_token(client_id, client_secret, refresh_token)

    msg = MIMEText(html_body, "html")
    msg["to"] = recipient
    msg["from"] = address
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    resp = requests.post(
        SEND_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        json={"raw": raw},
        timeout=15,
    )
    resp.raise_for_status()
