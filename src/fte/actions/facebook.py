"""Facebook publishing via agent-browser — Gold Tier.

Uses agent-browser subprocess with persistent session for Facebook posting.
Session stored at ~/.agent-browser/sessions/facebook/ (auto-managed).

Handler: publish_facebook_post_handler
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import frontmatter

BROWSER_TIMEOUT = 60  # seconds


class BrowserActionError(Exception):
    """Raised when agent-browser returns a non-zero exit code."""


def _browser(session: str, *args: str, timeout: int = BROWSER_TIMEOUT) -> str:
    """Run an agent-browser command with the given session."""
    result = subprocess.run(
        ["agent-browser", "--session-name", session, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise BrowserActionError(result.stderr or result.stdout)
    return result.stdout


def _detect_session_expiry(output: str) -> bool:
    """Check if the browser output indicates a session expiry (login page)."""
    indicators = ["login", "log in", "sign in", "password", "create new account"]
    lower = output.lower()
    return any(ind in lower for ind in indicators)


def _write_session_alert(vault: Path, platform: str) -> None:
    """Write a SYSTEM_social-session-expired.md alert."""
    now = datetime.now(timezone.utc).isoformat()
    alert_path = vault / "Needs_Action" / "SYSTEM_social-session-expired.md"
    alert_path.write_text(
        f"---\ntype: system_alert\nalert_type: social_session_expired\n"
        f"platform: {platform}\ncreated_at: \"{now}\"\n---\n\n"
        f"# Social Session Expired\n\n"
        f"The {platform.title()} browser session has been invalidated.\n\n"
        f"**Action required**: Run `agent-browser --session-name {platform} open "
        f"https://{platform}.com` and log in manually.\n",
        encoding="utf-8",
    )


def publish_facebook_post_handler(approved_path: Path, vault: Path) -> None:
    """Publish a Facebook post via agent-browser."""
    post = frontmatter.load(str(approved_path))
    post_text = post.get("post_text", "")
    session_name = post.get("session_name", "facebook")

    if not post_text:
        raise ValueError("No post_text in approval file")

    dev_mode = os.environ.get("DEV_MODE", "").lower() in ("true", "1", "yes")
    if dev_mode:
        print(f"[facebook] DEV_MODE — would publish: {post_text[:100]}...")
        return

    # Navigate to Facebook
    # NOTE: Selectors may need updating if Facebook UI changes.
    # Steps: open → snapshot → click post box → type → submit
    try:
        _browser(session_name, "open", "https://facebook.com")
        output = _browser(session_name, "snapshot", "-i")

        if _detect_session_expiry(output):
            _write_session_alert(vault, "facebook")
            raise BrowserActionError("Facebook session expired — login required")

        # Click the "What's on your mind?" post box
        _browser(session_name, "click", "What's on your mind")
        _browser(session_name, "type", post_text)
        _browser(session_name, "click", "Post")  # Submit button

        # Save session after successful post
        _browser(session_name, "state", "save",
                 os.path.expanduser("~/.config/fte/facebook-session.json"))

        print(f"[facebook] Post published successfully ({len(post_text)} chars)")

    except subprocess.TimeoutExpired:
        raise BrowserActionError("Facebook post timed out after 60s")
