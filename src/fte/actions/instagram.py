"""Instagram publishing via agent-browser — Gold Tier.

Uses agent-browser subprocess with persistent session for Instagram posting.
Session stored at ~/.agent-browser/sessions/instagram/ (auto-managed).

Handler: publish_instagram_post_handler
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
    """Check if browser output indicates session expiry."""
    indicators = ["login", "log in", "sign in", "password", "create account"]
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


def publish_instagram_post_handler(approved_path: Path, vault: Path) -> None:
    """Publish an Instagram post via agent-browser.

    Pre-dispatch guard in executor.py rejects files with
    image_required=true and image_path=null before this handler runs.
    """
    post = frontmatter.load(str(approved_path))
    post_text = post.get("post_text", "")
    session_name = post.get("session_name", "instagram")
    image_path = post.get("image_path")

    if not post_text:
        raise ValueError("No post_text in approval file")

    dev_mode = os.environ.get("DEV_MODE", "").lower() in ("true", "1", "yes")
    if dev_mode:
        print(f"[instagram] DEV_MODE — would publish: {post_text[:100]}...")
        return

    # Navigate to Instagram
    # NOTE: Selectors may need updating if Instagram UI changes.
    try:
        _browser(session_name, "open", "https://instagram.com")
        output = _browser(session_name, "snapshot", "-i")

        if _detect_session_expiry(output):
            _write_session_alert(vault, "instagram")
            raise BrowserActionError("Instagram session expired — login required")

        # Click the create post button (+)
        _browser(session_name, "click", "New post")

        # If image is provided, upload it
        if image_path and os.path.exists(image_path):
            _browser(session_name, "upload", image_path)

        _browser(session_name, "type", post_text)
        _browser(session_name, "click", "Share")  # Submit button

        # Save session after successful post
        _browser(session_name, "state", "save",
                 os.path.expanduser("~/.config/fte/instagram-session.json"))

        print(f"[instagram] Post published successfully ({len(post_text)} chars)")

    except subprocess.TimeoutExpired:
        raise BrowserActionError("Instagram post timed out after 60s")
