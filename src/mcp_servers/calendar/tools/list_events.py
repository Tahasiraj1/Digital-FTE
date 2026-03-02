"""List calendar events tool."""

from __future__ import annotations

import logging
from typing import Any

from googleapiclient.errors import HttpError

from mcp_servers.calendar.services.calendar_service import get_calendar_service

logger = logging.getLogger(__name__)


def list_events(
    date_from: str,
    date_to: str,
    max_results: int = 10,
) -> dict[str, Any]:
    """List Google Calendar events within a date range.

    Args:
        date_from: Start date in ISO 8601 format (YYYY-MM-DD or full RFC3339).
        date_to: End date in ISO 8601 format (YYYY-MM-DD or full RFC3339).
        max_results: Maximum number of events to return (1–50).

    Returns:
        {"events": [...], "total_count": int}
    """
    if not date_from:
        return {"error": {"code": "BAD_REQUEST", "message": "date_from is required"}, "isError": True}
    if not date_to:
        return {"error": {"code": "BAD_REQUEST", "message": "date_to is required"}, "isError": True}

    max_results = min(max(1, max_results), 50)

    # Convert YYYY-MM-DD to RFC3339 if needed
    if len(date_from) == 10:
        date_from = f"{date_from}T00:00:00Z"
    if len(date_to) == 10:
        date_to = f"{date_to}T23:59:59Z"

    try:
        service = get_calendar_service()
        result = service.events().list(
            calendarId="primary",
            timeMin=date_from,
            timeMax=date_to,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        items = result.get("items", [])
        events_list = []
        for item in items:
            start = item.get("start", {})
            end = item.get("end", {})
            attendees = [
                a.get("email", "") for a in item.get("attendees", [])
            ]
            events_list.append({
                "event_id": item.get("id", ""),
                "title": item.get("summary", "(No Title)"),
                "description": item.get("description", ""),
                "start": start.get("dateTime") or start.get("date", ""),
                "end": end.get("dateTime") or end.get("date", ""),
                "timezone": start.get("timeZone", "UTC"),
                "attendees": attendees,
                "html_link": item.get("htmlLink", ""),
                "status": item.get("status", ""),
            })

        return {"events": events_list, "total_count": len(events_list)}

    except HttpError as e:
        error_code = e.resp.status if hasattr(e, "resp") else 500
        if error_code == 401:
            return {"error": {"code": "UNAUTHORIZED", "message": "Google token invalid."}, "isError": True}
        elif error_code == 403:
            return {"error": {"code": "FORBIDDEN", "message": "Calendar API quota exceeded."}, "isError": True}
        else:
            logger.error(f"Calendar API error: {e}", exc_info=True)
            return {"error": {"code": "INTERNAL_ERROR", "message": str(e)}, "isError": True}

    except Exception as e:
        logger.error(f"Unexpected error in list_events: {e}", exc_info=True)
        return {"error": {"code": "INTERNAL_ERROR", "message": str(e)}, "isError": True}
