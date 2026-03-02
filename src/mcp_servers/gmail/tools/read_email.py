"""Read email tool — adapted from D:\\Code.Taha\\email-app\\mcp_server\\tools\\read_email.py.

Multi-user OAuth parameters removed. All Gmail API call logic retained.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from googleapiclient.errors import HttpError

from mcp_servers.gmail.services.gmail_service import get_gmail_service

logger = logging.getLogger(__name__)


def read_email(message_id: str) -> dict[str, Any]:
    """Retrieve the full content of a specific email message.

    Args:
        message_id: Gmail message ID.

    Returns:
        {"message_id": str, "subject": str, "from": str, "to": list,
         "date": str, "body_text": str, "body_html": str, "thread_id": str, "labels": list}
    """
    if not message_id or not message_id.strip():
        return {"error": {"code": "BAD_REQUEST", "message": "message_id is required"}, "isError": True}

    try:
        service = get_gmail_service()
        msg_data = service.users().messages().get(
            userId="me",
            id=message_id,
            format="full",
        ).execute()

        thread_id = msg_data.get("threadId")
        labels = msg_data.get("labelIds", [])
        headers = msg_data.get("payload", {}).get("headers", [])
        header_dict = {h["name"]: h["value"] for h in headers}

        subject = header_dict.get("Subject", "(No Subject)")
        from_addr = header_dict.get("From", "")
        to_addr = header_dict.get("To", "")
        date_str = header_dict.get("Date", "")
        message_id_header = header_dict.get("Message-ID", "")

        body_text = ""
        body_html = ""

        def extract_body(payload: dict) -> None:
            nonlocal body_text, body_html
            mime_type = payload.get("mimeType", "")
            body_data = payload.get("body", {}).get("data", "")
            if body_data:
                decoded = base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")
                if mime_type == "text/plain":
                    body_text = decoded
                elif mime_type == "text/html":
                    body_html = decoded
            for part in payload.get("parts", []):
                extract_body(part)

        extract_body(msg_data.get("payload", {}))

        return {
            "message_id": message_id,
            "message_id_header": message_id_header,
            "thread_id": thread_id,
            "subject": subject,
            "from": from_addr,
            "to": [to_addr] if to_addr else [],
            "date": date_str,
            "labels": labels,
            "body_text": body_text,
            "body_html": body_html,
        }

    except HttpError as e:
        error_code = e.resp.status if hasattr(e, "resp") else 500
        if error_code == 404:
            return {"error": {"code": "NOT_FOUND", "message": f"Email {message_id} not found"}, "isError": True}
        elif error_code == 401:
            return {"error": {"code": "UNAUTHORIZED", "message": "Gmail token invalid."}, "isError": True}
        else:
            logger.error(f"Gmail API error: {e}", exc_info=True)
            return {"error": {"code": "INTERNAL_ERROR", "message": str(e)}, "isError": True}

    except Exception as e:
        logger.error(f"Unexpected error in read_email: {e}", exc_info=True)
        return {"error": {"code": "INTERNAL_ERROR", "message": str(e)}, "isError": True}
