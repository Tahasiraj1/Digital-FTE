"""WhatsApp action handler — sends approved replies via IPC bridge.

The executor calls send_whatsapp_handler(approved_path, vault).
Sends POST to http://localhost:8766/send — the watcher.js IPC bridge.
30-second timeout. On failure: raises RuntimeError (caller moves to Rejected/).
"""

from __future__ import annotations

import sys
from pathlib import Path

import frontmatter
import httpx

IPC_URL = "http://127.0.0.1:8766/send"
HTTP_TIMEOUT = 30  # seconds


def send_whatsapp_handler(approved_path: Path, vault: Path) -> None:
    """Send an approved WhatsApp reply via the watcher.js IPC bridge.

    Args:
        approved_path: Path to the approved .md file in Vault/Approved/.
        vault: Root vault directory.

    Raises:
        RuntimeError: On IPC failure, timeout, or missing frontmatter fields.
    """
    post = frontmatter.load(str(approved_path))

    to_jid = post.get("to_jid", "").strip()
    to_display = post.get("to_display", "")
    proposed_reply = post.get("proposed_reply", "").strip()

    if not to_jid:
        raise RuntimeError(f"No to_jid in {approved_path.name}")
    if not proposed_reply:
        raise RuntimeError(f"No proposed_reply in {approved_path.name}")

    # Enforce 500-char limit per Company_Handbook rules
    if len(proposed_reply) > 500:
        proposed_reply = proposed_reply[:497] + "..."

    try:
        response = httpx.post(
            IPC_URL,
            json={"to_jid": to_jid, "message": proposed_reply},
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "sent":
            raise RuntimeError(f"IPC returned unexpected response: {data}")

        print(f"[whatsapp-action] Reply sent to {to_display} ({to_jid})")

    except httpx.ConnectError:
        raise RuntimeError(
            f"Cannot connect to WhatsApp IPC bridge at {IPC_URL}. "
            "Is fte-whatsapp-watcher running?"
        )
    except httpx.TimeoutException:
        raise RuntimeError(f"WhatsApp IPC bridge timed out after {HTTP_TIMEOUT}s")
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"IPC bridge HTTP error {exc.response.status_code}: {exc.response.text[:200]}")
