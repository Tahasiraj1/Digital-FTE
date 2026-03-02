"""One-time OAuth2 setup for Gmail and Google Calendar.

Run once to authorise the FTE agent:
    uv run python scripts/oauth_setup.py

The token is saved to ~/.config/fte/gmail_token.json (chmod 600).
Subsequent runs skip the flow if the token is already valid.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
]

TOKEN_PATH = Path(
    os.environ.get("GMAIL_TOKEN_PATH", Path.home() / ".config" / "fte" / "gmail_token.json")
)

CLIENT_SECRETS_PATH = Path(
    os.environ.get("GOOGLE_CLIENT_SECRETS", Path.home() / ".config" / "fte" / "client_secrets.json")
)


def _token_is_valid(token_path: Path) -> bool:
    """Return True if the existing token is valid (not expired or refreshable)."""
    if not token_path.exists():
        return False
    try:
        data = json.loads(token_path.read_text(encoding="utf-8"))
        creds = Credentials(
            token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=data.get("client_id") or os.environ.get("GOOGLE_CLIENT_ID", ""),
            client_secret=data.get("client_secret") or os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            scopes=data.get("scopes", SCOPES),
        )
        if not creds.expired:
            return True
        if creds.refresh_token:
            creds.refresh(Request())
            _write_token(token_path, creds, data)
            return True
        return False
    except Exception as exc:
        print(f"[oauth_setup] Existing token invalid: {exc}", file=sys.stderr)
        return False


def _write_token(token_path: Path, creds: Credentials, existing: dict) -> None:
    """Write token to disk with chmod 600."""
    token_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        **existing,
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or SCOPES),
    }
    token_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    token_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # chmod 600


def main() -> None:
    print("FTE — Google OAuth2 Setup")
    print("=" * 40)

    if _token_is_valid(TOKEN_PATH):
        print(f"[OK] Token already valid at {TOKEN_PATH}. No action needed.")
        return

    if not CLIENT_SECRETS_PATH.exists():
        print(
            f"\n[ERROR] client_secrets.json not found at {CLIENT_SECRETS_PATH}\n"
            "Steps:\n"
            "  1. Go to https://console.cloud.google.com/\n"
            "  2. Create OAuth2 credentials (Desktop app type)\n"
            "  3. Download JSON → save to ~/.config/fte/client_secrets.json\n"
            "  4. Re-run: uv run python scripts/oauth_setup.py\n"
        )
        sys.exit(1)

    print(f"\nStarting OAuth2 flow (client_secrets: {CLIENT_SECRETS_PATH})")
    print("A browser window will open. Please authorise the FTE application.\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRETS_PATH),
        scopes=SCOPES,
    )
    creds = flow.run_local_server(port=0, open_browser=True)

    _write_token(TOKEN_PATH, creds, {})
    print(f"\n[OK] Token saved to {TOKEN_PATH} (chmod 600)")
    print("\nNext steps:")
    print("  1. Register Gmail MCP in ~/.claude/settings.json")
    print("  2. Register Calendar MCP in ~/.claude/settings.json")
    print("  3. Run: fte execute --dry-run")
    print("\nSee specs/003-silver-functional-assistant/quickstart.md for details.")


if __name__ == "__main__":
    main()
