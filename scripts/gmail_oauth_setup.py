"""One-time local setup: obtain a Gmail API refresh token for the cloud routine to use.

Prerequisites (do these in Google Cloud Console first — see README.md):
1. Create/select a project, enable the Gmail API.
2. Configure the OAuth consent screen (External, Testing mode is fine for personal use;
   add your own Gmail address as a test user — no Google verification needed).
3. Create an OAuth client ID of type "Desktop app". Download its client_id + client_secret.

Usage:
    python scripts/gmail_oauth_setup.py --client-id ... --client-secret ...
(or set GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET env vars instead of flags)

Opens a browser for you to sign in and approve "send email" access, then prints the
refresh token to save as GMAIL_REFRESH_TOKEN (alongside GMAIL_CLIENT_ID/GMAIL_CLIENT_SECRET)
in both .env (local) and the cloud environment's secrets.

Requires: pip install google-auth-oauthlib (dev-only — not needed at runtime).
"""
from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", default=os.environ.get("GOOGLE_OAUTH_CLIENT_ID"))
    parser.add_argument("--client-secret", default=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET"))
    args = parser.parse_args()

    if not args.client_id or not args.client_secret:
        print(
            "Missing client ID/secret. Pass --client-id/--client-secret, or set "
            "GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET env vars.\n"
            "Get these from Google Cloud Console -> APIs & Services -> Credentials "
            "-> an OAuth client ID of type 'Desktop app'.",
            file=sys.stderr,
        )
        return 1

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print(
            "Missing dependency. Run: pip install google-auth-oauthlib",
            file=sys.stderr,
        )
        return 1

    client_config = {
        "installed": {
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(
        client_config, scopes=["https://www.googleapis.com/auth/gmail.send"]
    )
    credentials = flow.run_local_server(port=0)

    print("\nSuccess. Set these as environment variables (in .env for the local path,")
    print("and in the cloud environment's secrets for the routine):\n")
    print(f"GMAIL_CLIENT_ID={args.client_id}")
    print(f"GMAIL_CLIENT_SECRET={args.client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={credentials.refresh_token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
