"""List emails tool — adapted from D:\\Code.Taha\\email-app\\mcp_server\\tools\\list_emails.py.

Multi-user OAuth parameters (_oauth_token, _user_identity) removed.
All Gmail API call logic and error handling retained as-is.
"""

from __future__ import annotations

import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from googleapiclient.errors import HttpError

from mcp_servers.gmail.services.gmail_service import get_gmail_service

logger = logging.getLogger(__name__)


def list_emails(
    query: str | None = None,
    max_results: int = 10,
) -> dict[str, Any]:
    """Fetch a list of email messages from Gmail inbox.

    Args:
        query: Gmail search query (e.g. "from:example@gmail.com is:unread").
        max_results: Maximum number of results (1–50).

    Returns:
        {"emails": [...], "total_count": int}
    """
    if max_results < 1:
        raise ValueError("max_results must be at least 1")
    if max_results > 50:
        raise ValueError("max_results cannot exceed 50")

    try:
        service = get_gmail_service()

        query_params: dict[str, Any] = {
            "userId": "me",
            "maxResults": min(max_results, 50),
        }
        if query:
            query_params["q"] = query

        results = service.users().messages().list(**query_params).execute()
        messages = results.get("messages", [])
        total_count = results.get("resultSizeEstimate", len(messages))

        emails_list = []
        for msg in messages:
            msg_id = msg.get("id")
            if not msg_id:
                continue
            try:
                msg_data = service.users().messages().get(
                    userId="me",
                    id=msg_id,
                    format="metadata",
                    metadataHeaders=["Subject", "From", "To", "Date"],
                ).execute()

                thread_id = msg_data.get("threadId")
                labels = msg_data.get("labelIds", [])
                headers = msg_data.get("payload", {}).get("headers", [])
                header_dict = {h["name"]: h["value"] for h in headers}

                subject = header_dict.get("Subject", "(No Subject)")
                from_addr = header_dict.get("From", "(No Sender)")
                to_addr = header_dict.get("To", "")
                date_str = header_dict.get("Date", "")

                date_obj = None
                if date_str:
                    try:
                        date_obj = parsedate_to_datetime(date_str)
                    except Exception:
                        internal_date = msg_data.get("internalDate")
                        if internal_date:
                            date_obj = datetime.fromtimestamp(int(internal_date) / 1000)

                emails_list.append({
                    "message_id": msg_id,
                    "thread_id": thread_id,
                    "subject": subject,
                    "from": from_addr,
                    "to": [to_addr] if to_addr else [],
                    "date": date_obj.isoformat() + "Z" if date_obj else None,
                    "labels": labels,
                })
            except HttpError as e:
                logger.warning(f"Failed to get metadata for message {msg_id}: {e}")
                continue

        return {"emails": emails_list, "total_count": total_count}

    except HttpError as e:
        error_code = e.resp.status if hasattr(e, "resp") else 500
        if error_code == 401:
            return {"error": {"code": "UNAUTHORIZED", "message": "Gmail token invalid. Re-run oauth_setup.py."}, "isError": True}
        elif error_code == 400:
            return {"error": {"code": "BAD_REQUEST", "message": str(e)}, "isError": True}
        else:
            logger.error(f"Gmail API error: {e}", exc_info=True)
            return {"error": {"code": "INTERNAL_ERROR", "message": "Failed to fetch emails."}, "isError": True}

    except Exception as e:
        logger.error(f"Unexpected error in list_emails: {e}", exc_info=True)
        return {"error": {"code": "INTERNAL_ERROR", "message": str(e)}, "isError": True}
