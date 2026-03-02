"""LinkedIn OAuth2 setup — one-time browser authorization flow.

Run: uv run python -m fte.linkedin_auth
Or:  fte linkedin-auth

Saves token to ~/.config/fte/linkedin_token.json (chmod 600).
Idempotent — skips if token already exists and is valid.
"""

from __future__ import annotations

import http.server
import json
import os
import secrets
import stat
import sys
import threading
import urllib.parse
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

TOKEN_PATH = Path(
    os.environ.get("LINKEDIN_TOKEN_PATH", Path.home() / ".config" / "fte" / "linkedin_token.json")
)

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_PROFILE_URL = "https://api.linkedin.com/v2/userinfo"
REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"

SCOPES = "openid profile email w_member_social"


def _token_is_valid() -> bool:
    if not TOKEN_PATH.exists():
        return False
    try:
        data = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
        expires_at_str = data.get("expires_at", "")
        if not expires_at_str:
            return False
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        # Valid if more than 7 days remain
        return expires_at > datetime.now(timezone.utc) + timedelta(days=7)
    except Exception:
        return False


def _write_token(data: dict) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    TOKEN_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)  # chmod 600


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Capture the OAuth2 callback."""

    code: str | None = None
    state: str | None = None

    error: str | None = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = urllib.parse.parse_qs(parsed.query)
        _CallbackHandler.code = params.get("code", [None])[0]
        _CallbackHandler.state = params.get("state", [None])[0]
        _CallbackHandler.error = params.get("error", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        if _CallbackHandler.error:
            error_desc = params.get("error_description", ["Unknown error"])[0]
            body = (
                f"<html><body style='font-family:sans-serif;max-width:500px;margin:50px auto;'>"
                f"<h2 style='color:red'>Authorization Failed</h2>"
                f"<p><b>Error:</b> {_CallbackHandler.error}</p>"
                f"<p>{error_desc}</p>"
                f"</body></html>"
            ).encode()
        else:
            body = b"""
        <html><body style="font-family:sans-serif;max-width:500px;margin:50px auto;">
        <h2>FTE LinkedIn Authorization</h2>
        <p>Authorization complete! You can close this window.</p>
        </body></html>
        """
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # Suppress server logs


def run_auth_flow() -> None:
    client_id = os.environ.get("LINKEDIN_CLIENT_ID", "")
    client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print(
            "\n[ERROR] LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in .env\n"
            "Steps:\n"
            "  1. Go to developer.linkedin.com → Create App\n"
            "  2. Products → Request 'Share on LinkedIn'\n"
            "  3. Auth tab → Add redirect URL: http://localhost:8765/callback\n"
            "  4. Add to .env: LINKEDIN_CLIENT_ID=... LINKEDIN_CLIENT_SECRET=...\n"
        )
        sys.exit(1)

    state = secrets.token_urlsafe(16)
    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "scope": SCOPES,
    }
    auth_url = LINKEDIN_AUTH_URL + "?" + urllib.parse.urlencode(auth_params)

    # Start local callback server
    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    print(f"\nOpening browser for LinkedIn authorization...")
    webbrowser.open(auth_url)
    print(f"If browser didn't open, visit:\n  {auth_url}\n")

    # Wait for callback (poll with timeout)
    import time
    timeout = 300
    elapsed = 0
    while _CallbackHandler.code is None and _CallbackHandler.error is None and elapsed < timeout:
        time.sleep(0.5)
        elapsed += 0.5

    server.shutdown()

    if _CallbackHandler.error:
        print(f"\n[ERROR] LinkedIn authorization failed: {_CallbackHandler.error}")
        print("This usually means the app is missing required LinkedIn Products.")
        print("In LinkedIn Developer Portal → your app → Products:")
        print("  - Add 'Sign In with LinkedIn using OpenID Connect' (for openid/profile/email)")
        print("  - Add 'Share on LinkedIn' (for w_member_social)")
        sys.exit(1)

    if _CallbackHandler.code is None:
        print(f"\n[ERROR] Timed out waiting for LinkedIn callback after {timeout}s")
        sys.exit(1)

    if _CallbackHandler.state != state:
        print("\n[ERROR] State mismatch — possible CSRF attack")
        sys.exit(1)

    # Exchange code for tokens
    print("Exchanging authorization code for tokens...")
    try:
        resp = httpx.post(
            LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": _CallbackHandler.code,
                "redirect_uri": REDIRECT_URI,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        print(f"[DEBUG] Token exchange status: {resp.status_code}")
        print(f"[DEBUG] Token exchange response: {resp.text[:500]}")
        resp.raise_for_status()
        token_data = resp.json()
    except httpx.HTTPStatusError as exc:
        print(f"\n[ERROR] Token exchange failed: HTTP {exc.response.status_code}")
        print(f"[ERROR] Response body: {exc.response.text[:500]}")
        sys.exit(1)
    except Exception as exc:
        print(f"\n[ERROR] Token exchange failed: {exc}")
        sys.exit(1)

    # Fetch LinkedIn user ID
    profile_resp = httpx.get(
        LINKEDIN_PROFILE_URL,
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
        timeout=10,
    )
    profile = profile_resp.json() if profile_resp.status_code == 200 else {}
    linkedin_user_id = profile.get("sub", "")

    now = datetime.now(timezone.utc)
    expires_in = token_data.get("expires_in", 5184000)  # default 60 days
    refresh_expires_in = token_data.get("refresh_token_expires_in", 31536000)  # 365 days

    token_file = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token", ""),
        "expires_at": (now + timedelta(seconds=expires_in)).isoformat(),
        "refresh_token_expires_at": (now + timedelta(seconds=refresh_expires_in)).isoformat(),
        "scope": token_data.get("scope", SCOPES),
        "token_type": token_data.get("token_type", "Bearer"),
        "linkedin_user_id": linkedin_user_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    _write_token(token_file)
    print(f"\n[OK] LinkedIn token saved to {TOKEN_PATH} (chmod 600)")
    if linkedin_user_id:
        print(f"     User ID: {linkedin_user_id}")
    print("\nNext step: run 'fte execute' to start the action executor.")


def main() -> None:
    print("FTE — LinkedIn OAuth2 Setup")
    print("=" * 40)

    if _token_is_valid():
        print(f"[OK] Token already valid at {TOKEN_PATH}. No action needed.")
        return

    run_auth_flow()


if __name__ == "__main__":
    main()
