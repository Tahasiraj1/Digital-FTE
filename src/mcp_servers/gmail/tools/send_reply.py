"""Send reply tool — adapted from D:\\Code.Taha\\email-app\\mcp_server\\tools\\send_reply.py.

Multi-user OAuth parameters removed. confirm: bool safety gate retained —
the executor always passes confirm=True after HITL approval.
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any

from googleapiclient.errors import HttpError

from mcp_servers.gmail.services.gmail_service import get_gmail_service

logger = logging.getLogger(__name__)


def send_reply(
    message_id: str,
    reply_content: str,
    confirm: bool,
) -> dict[str, Any]:
    """Send an email reply on the user's behalf.

    Args:
        message_id: Gmail message ID of the email to reply to.
        reply_content: Body text of the reply.
        confirm: MUST be True to send. Safety gate — executor always passes True.

    Returns:
        {"sent_message_id": str, "sent_at": str} on success.
    """
    if confirm is not True:
        return {
            "error": {
                "code": "BAD_REQUEST",
                "message": "'confirm' must be explicitly True to send email",
            },
            "isError": True,
        }

    if not message_id or not message_id.strip():
        return {"error": {"code": "BAD_REQUEST", "message": "message_id is required"}, "isError": True}

    if not reply_content or not reply_content.strip():
        return {"error": {"code": "BAD_REQUEST", "message": "reply_content is required"}, "isError": True}

    try:
        service = get_gmail_service()

        original_msg = service.users().messages().get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=["Subject", "From", "Message-ID"],
        ).execute()

        thread_id = original_msg.get("threadId")
        headers = {h["name"]: h["value"] for h in original_msg["payload"]["headers"]}
        to_addr = headers.get("From", "")
        original_subject = headers.get("Subject", "(No Subject)")
        original_message_id = headers.get("Message-ID", "")

        reply = EmailMessage()
        reply["To"] = to_addr
        reply["Subject"] = f"Re: {original_subject}" if not original_subject.startswith("Re:") else original_subject
        if original_message_id:
            reply["In-Reply-To"] = original_message_id
            reply["References"] = original_message_id
        reply.set_content(reply_content)

        raw_message = base64.urlsafe_b64encode(reply.as_bytes()).decode()
        sent_msg = service.users().messages().send(
            userId="me",
            body={"raw": raw_message, "threadId": thread_id},
        ).execute()

        sent_message_id = sent_msg.get("id", "")
        sent_at = datetime.now(timezone.utc).isoformat()

        return {"sent_message_id": sent_message_id, "sent_at": sent_at}

    except HttpError as e:
        error_code = e.resp.status if hasattr(e, "resp") else 500
        if error_code == 401:
            return {"error": {"code": "UNAUTHORIZED", "message": "Gmail token invalid."}, "isError": True}
        elif error_code == 404:
            return {"error": {"code": "NOT_FOUND", "message": f"Email {message_id} not found"}, "isError": True}
        else:
            logger.error(f"Gmail send error: {e}", exc_info=True)
            return {"error": {"code": "INTERNAL_ERROR", "message": str(e)}, "isError": True}

    except Exception as e:
        logger.error(f"Unexpected error in send_reply: {e}", exc_info=True)
        return {"error": {"code": "INTERNAL_ERROR", "message": str(e)}, "isError": True}
