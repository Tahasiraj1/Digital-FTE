"""Gmail action handler — sends approved email replies directly via Gmail API.

The executor calls send_email_handler(approved_path, vault).
The function reads the approved file's frontmatter and calls send_reply() directly.
On success: caller moves file to Done/. On failure: raises RuntimeError.
"""

from __future__ import annotations

import os
from pathlib import Path

import frontmatter


def send_email_handler(approved_path: Path, vault: Path) -> None:
    """Send an approved email reply via Gmail API.

    Args:
        approved_path: Path to the approved .md file in Vault/Approved/.
        vault: Root vault directory.

    Raises:
        RuntimeError: On missing fields or Gmail API failure.
    """
    post = frontmatter.load(str(approved_path))

    message_id = str(post.get("message_id", "")).strip('"').strip()
    to = post.get("to", "")
    subject = post.get("subject", "")
    proposed_reply = str(post.get("proposed_reply", "")).strip()

    if not message_id:
        raise RuntimeError(f"No message_id in {approved_path.name}")
    if not proposed_reply:
        raise RuntimeError(f"No proposed_reply in {approved_path.name}")

    # Set token path for Gmail service
    token_path = os.environ.get(
        "GMAIL_TOKEN_PATH",
        str(Path.home() / ".config" / "fte" / "gmail_token.json"),
    )
    os.environ["GMAIL_TOKEN_PATH"] = token_path

    from mcp_servers.gmail.tools.send_reply import send_reply

    result = send_reply(
        message_id=message_id,
        reply_content=proposed_reply,
        confirm=True,
    )

    if result.get("isError"):
        error = result.get("error", {})
        raise RuntimeError(f"Gmail API error: {error.get('code')} — {error.get('message')}")

    sent_id = result.get("sent_message_id", "?")
    print(f"[gmail-action] Email reply sent (id={sent_id}): to={to} subject={subject}")
