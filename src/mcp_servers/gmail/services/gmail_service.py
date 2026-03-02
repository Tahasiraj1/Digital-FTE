"""Gmail API service — single-user, local token file.

Adapted from D:\\Code.Taha\\email-app\\mcp_server\\services\\gmail_service.py.
Multi-user OAuth layer (TokenManager, @require_oauth) stripped and replaced
with a direct local token file reader.
"""

from __future__ import annotations

import json
import sys

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from mcp_servers.gmail.config import config


def get_gmail_service():
    """Build and return an authenticated Gmail v1 API service.

    Reads the OAuth2 token from ~/.config/fte/gmail_token.json.
    Automatically refreshes the access token if expired.

    Raises:
        FileNotFoundError: If the token file does not exist (run oauth_setup.py).
        ValueError: If the token file is malformed.
    """
    token_path = config.token_path
    if not token_path.exists():
        raise FileNotFoundError(
            f"Gmail token not found at {token_path}. "
            "Run: uv run python scripts/oauth_setup.py"
        )

    try:
        token_data = json.loads(token_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid token file at {token_path}: {exc}") from exc

    creds = Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token_data.get("client_id") or config.client_id,
        client_secret=token_data.get("client_secret") or config.client_secret,
        scopes=token_data.get("scopes", [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
        ]),
    )

    # Refresh access token if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Write refreshed token back to disk
            token_data["access_token"] = creds.token
            token_path.write_text(
                json.dumps(token_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"[gmail-mcp] Warning: token refresh failed: {exc}", file=sys.stderr)

    return build("gmail", "v1", credentials=creds)
