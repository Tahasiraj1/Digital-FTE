"""Create calendar event tool."""

from __future__ import annotations

import logging
from typing import Any

from googleapiclient.errors import HttpError

from mcp_servers.calendar.services.calendar_service import get_calendar_service

logger = logging.getLogger(__name__)


def create_event(
    title: str,
    date: str,
    start_time: str,
    end_time: str,
    timezone: str = "Asia/Karachi",
    attendees: list[str] | None = None,
    description: str = "",
) -> dict[str, Any]:
    """Create a Google Calendar event.

    Args:
        title: Event title/summary.
        date: Event date in ISO 8601 format (YYYY-MM-DD).
        start_time: Start time in HH:MM (24-hour) format.
        end_time: End time in HH:MM (24-hour) format.
        timezone: IANA timezone string (default: Asia/Karachi).
        attendees: List of attendee email addresses.
        description: Optional event description.

    Returns:
        {"event_id": str, "html_link": str} on success.
    """
    if not title or not title.strip():
        return {"error": {"code": "BAD_REQUEST", "message": "title is required"}, "isError": True}
    if not date or not date.strip():
        return {"error": {"code": "BAD_REQUEST", "message": "date is required"}, "isError": True}
    if not start_time or not start_time.strip():
        return {"error": {"code": "BAD_REQUEST", "message": "start_time is required"}, "isError": True}
    if not end_time or not end_time.strip():
        return {"error": {"code": "BAD_REQUEST", "message": "end_time is required"}, "isError": True}

    # Validate ISO date format
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return {"error": {"code": "BAD_REQUEST", "message": "date must be in YYYY-MM-DD format"}, "isError": True}

    event_body: dict[str, Any] = {
        "summary": title,
        "description": description,
        "start": {
            "dateTime": f"{date}T{start_time}:00",
            "timeZone": timezone,
        },
        "end": {
            "dateTime": f"{date}T{end_time}:00",
            "timeZone": timezone,
        },
    }

    if attendees:
        event_body["attendees"] = [{"email": email} for email in attendees]

    try:
        service = get_calendar_service()
        event = service.events().insert(
            calendarId="primary",
            body=event_body,
            sendUpdates="all" if attendees else "none",
        ).execute()

        return {
            "event_id": event.get("id", ""),
            "html_link": event.get("htmlLink", ""),
        }

    except HttpError as e:
        error_code = e.resp.status if hasattr(e, "resp") else 500
        if error_code == 401:
            return {"error": {"code": "UNAUTHORIZED", "message": "Google token invalid."}, "isError": True}
        elif error_code == 403:
            return {"error": {"code": "FORBIDDEN", "message": "Calendar API quota exceeded or insufficient permissions."}, "isError": True}
        elif error_code == 429:
            return {"error": {"code": "RATE_LIMITED", "message": "Calendar API rate limit exceeded."}, "isError": True}
        else:
            logger.error(f"Calendar API error: {e}", exc_info=True)
            return {"error": {"code": "INTERNAL_ERROR", "message": str(e)}, "isError": True}

    except Exception as e:
        logger.error(f"Unexpected error in create_event: {e}", exc_info=True)
        return {"error": {"code": "INTERNAL_ERROR", "message": str(e)}, "isError": True}
