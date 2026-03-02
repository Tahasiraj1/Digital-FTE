"""LinkedIn action handler — publishes approved posts via LinkedIn REST API.

The executor calls publish_linkedin_post_handler(approved_path, vault).
No MCP needed — direct POST to https://api.linkedin.com/v2/ugcPosts via httpx.

Rate limit: max 10 posts/day (enforced by counting today's log entries).
Token: proactively refreshes if expires within 7 days (T049).
"""

from __future__ import annotations

import json
import os
import stat
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import frontmatter
import httpx

TOKEN_PATH = Path(
    os.environ.get("LINKEDIN_TOKEN_PATH", Path.home() / ".config" / "fte" / "linkedin_token.json")
)

LINKEDIN_UGC_URL = "https://api.linkedin.com/v2/ugcPosts"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
HTTP_TIMEOUT = 30  # seconds
DAILY_POST_LIMIT = 10


# ---------------------------------------------------------------------------
# Token management — T049
# ---------------------------------------------------------------------------

def _load_token() -> dict:
    if not TOKEN_PATH.exists():
        raise RuntimeError(
            f"LinkedIn token not found at {TOKEN_PATH}. "
            "Run: fte linkedin-auth"
        )
    return json.loads(TOKEN_PATH.read_text(encoding="utf-8"))


def _write_token(data: dict) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    TOKEN_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)  # chmod 600


def _proactive_refresh(token_data: dict) -> dict:
    """Refresh the LinkedIn access token if it expires within 7 days (T049).

    Always overwrites both access_token and refresh_token (LinkedIn rotates them).
    If refresh fails, writes an alert to Vault/Needs_Action/ if vault path is available.
    """
    expires_at_str = token_data.get("expires_at", "")
    if not expires_at_str:
        return token_data

    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
    except ValueError:
        return token_data

    threshold = datetime.now(timezone.utc) + timedelta(days=7)
    if expires_at > threshold:
        return token_data  # Still valid, no refresh needed

    refresh_token = token_data.get("refresh_token", "")
    if not refresh_token:
        raise RuntimeError("LinkedIn access token expired and no refresh_token available. Re-run linkedin-auth.")

    client_id = os.environ.get("LINKEDIN_CLIENT_ID", "")
    client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET", "")

    try:
        resp = httpx.post(
            LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        new_tokens = resp.json()

        now = datetime.now(timezone.utc)
        expires_in = new_tokens.get("expires_in", 5184000)
        refresh_expires_in = new_tokens.get("refresh_token_expires_in", 31536000)

        token_data = {
            **token_data,
            "access_token": new_tokens["access_token"],
            "refresh_token": new_tokens.get("refresh_token", refresh_token),
            "expires_at": (now + timedelta(seconds=expires_in)).isoformat(),
            "refresh_token_expires_at": (now + timedelta(seconds=refresh_expires_in)).isoformat(),
            "updated_at": now.isoformat(),
        }
        _write_token(token_data)
        print("[linkedin-action] Token refreshed successfully")
        return token_data

    except Exception as exc:
        raise RuntimeError(f"LinkedIn token refresh failed: {exc}. Re-run 'fte linkedin-auth'.")


# ---------------------------------------------------------------------------
# Rate limit enforcement — T050
# ---------------------------------------------------------------------------

def _count_today_posts(vault: Path) -> int:
    """Count LinkedIn posts published today from the vault log."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = vault / "Logs" / f"{today}.json"
    if not log_file.exists():
        return 0

    try:
        log_data = json.loads(log_file.read_text(encoding="utf-8"))
        if not isinstance(log_data, list):
            return 0
        return sum(
            1 for entry in log_data
            if entry.get("action_type") == "publish_linkedin_post"
            and entry.get("result") == "success"
        )
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# LinkedIn UGC post schema builder
# ---------------------------------------------------------------------------

def _build_ugc_post(user_id: str, text: str) -> dict:
    """Build the LinkedIn UGC post request body."""
    return {
        "author": f"urn:li:person:{user_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": text,
                },
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
        },
    }


# ---------------------------------------------------------------------------
# Action handler — T048
# ---------------------------------------------------------------------------

def publish_linkedin_post_handler(approved_path: Path, vault: Path) -> None:
    """Publish an approved LinkedIn post via the LinkedIn REST API.

    Args:
        approved_path: Path to the approved .md file in Vault/Approved/.
        vault: Root vault directory.

    Raises:
        RuntimeError: On API failure, rate limit exceeded, or token issues.
    """
    post = frontmatter.load(str(approved_path))

    proposed_post = str(post.get("proposed_post", "")).strip()
    character_count = len(proposed_post)

    if not proposed_post:
        raise RuntimeError(f"No proposed_post in {approved_path.name}")

    if character_count > 3000:
        raise RuntimeError(
            f"Post exceeds 3000 character limit ({character_count} chars). "
            "Needs human review before publishing."
        )

    # Rate limit check — T050
    today_count = _count_today_posts(vault)
    if today_count >= DAILY_POST_LIMIT:
        # Write alert to Needs_Action/
        alert_file = vault / "Needs_Action" / f"SYSTEM_linkedin-rate-limit_{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        try:
            alert_file.write_text(
                f"---\ntype: system_alert\nalert: linkedin_rate_limit\n"
                f"posts_today: {today_count}\nlimit: {DAILY_POST_LIMIT}\n---\n\n"
                f"LinkedIn daily post limit ({DAILY_POST_LIMIT}) reached. "
                f"Rejected post moved to Rejected/.\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        raise RuntimeError(
            f"LinkedIn daily rate limit reached ({today_count}/{DAILY_POST_LIMIT} posts today)"
        )

    # Load and refresh token if needed — T049
    token_data = _load_token()
    token_data = _proactive_refresh(token_data)

    access_token = token_data.get("access_token", "")
    user_id = token_data.get("linkedin_user_id", "")

    if not access_token:
        raise RuntimeError("No access_token in LinkedIn token file. Re-run 'fte linkedin-auth'.")
    if not user_id:
        raise RuntimeError("No linkedin_user_id in token file. Re-run 'fte linkedin-auth'.")

    ugc_body = _build_ugc_post(user_id, proposed_post)

    try:
        resp = httpx.post(
            LINKEDIN_UGC_URL,
            json=ugc_body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        post_id = resp.headers.get("x-restli-id", "unknown")
        print(f"[linkedin-action] Post published (ID: {post_id}, {character_count} chars)")

    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        body = exc.response.text[:300]
        if status == 401:
            raise RuntimeError(f"LinkedIn token invalid/expired (401). Re-run 'fte linkedin-auth'.")
        elif status == 429:
            raise RuntimeError(f"LinkedIn API rate limited (429). Try again later.")
        elif status == 403:
            raise RuntimeError(f"LinkedIn API 403 Forbidden: {body}")
        else:
            raise RuntimeError(f"LinkedIn API error {status}: {body}")
    except httpx.TimeoutException:
        raise RuntimeError(f"LinkedIn API timed out after {HTTP_TIMEOUT}s")
    except httpx.ConnectError:
        raise RuntimeError("Cannot connect to LinkedIn API. Check internet connection.")
