"""Calendar action handler — creates approved calendar events directly via Calendar API.

The executor calls create_calendar_event_handler(approved_path, vault).
On success: caller moves file to Done/. On failure: raises RuntimeError.
"""

from __future__ import annotations

import os
from pathlib import Path

import frontmatter


def create_calendar_event_handler(approved_path: Path, vault: Path) -> None:
    """Create an approved calendar event via Google Calendar API.

    Args:
        approved_path: Path to the approved .md file in Vault/Approved/.
        vault: Root vault directory.

    Raises:
        RuntimeError: On missing fields or Calendar API failure.
    """
    post = frontmatter.load(str(approved_path))

    event_title = str(post.get("event_title", "")).strip()
    event_date = str(post.get("event_date", "")).strip()
    event_time_start = str(post.get("event_time_start", "10:00")).strip()
    event_time_end = str(post.get("event_time_end", "11:00")).strip()
    event_timezone = str(post.get("event_timezone", "Asia/Karachi")).strip()
    attendees = post.get("attendees", [])
    event_description = str(post.get("event_description", "")).strip()

    if not event_title:
        raise RuntimeError(f"No event_title in {approved_path.name}")
    if not event_date:
        raise RuntimeError(f"No event_date in {approved_path.name}")

    # Set token path for Calendar service
    token_path = os.environ.get(
        "CALENDAR_TOKEN_PATH",
        str(Path.home() / ".config" / "fte" / "gmail_token.json"),
    )
    os.environ["CALENDAR_TOKEN_PATH"] = token_path

    from mcp_servers.calendar.tools.create_event import create_event

    result = create_event(
        title=event_title,
        date=event_date,
        start_time=event_time_start,
        end_time=event_time_end,
        timezone=event_timezone,
        attendees=list(attendees) if attendees else None,
        description=event_description,
    )

    if result.get("isError"):
        error = result.get("error", {})
        raise RuntimeError(f"Calendar API error: {error.get('code')} — {error.get('message')}")

    event_id = result.get("event_id", "?")
    link = result.get("html_link", "")
    print(f"[calendar-action] Event created (id={event_id}): {event_title} on {event_date} | {link}")
