"""Gmail Watcher — polls Gmail inbox and writes task files to Vault/Inbox/.

Polls Gmail API every 120s. Filters: unread + (IMPORTANT label OR starred).
Deduplicates via WatcherState at ~/.config/fte/gmail_watcher_state.json.
Crash-resilient: catches all exceptions, sleeps 15s, retries.

T026-T028 implementation.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from fte.logger import log_action

POLL_INTERVAL = 120  # seconds between Gmail API polls
RETRY_SLEEP = 15     # seconds after a crash before retrying
STATE_MAX_IDS = 10000  # FIFO cap for processed_ids
SCHEMA_VERSION = "1"

STATE_PATH = Path(
    os.environ.get("GMAIL_WATCHER_STATE", Path.home() / ".config" / "fte" / "gmail_watcher_state.json")
)


# ---------------------------------------------------------------------------
# WatcherState — T027
# ---------------------------------------------------------------------------

class WatcherState:
    """Persist the set of already-processed Gmail message IDs.

    Schema:
        {
          "last_poll": "<ISO8601>",
          "processed_ids": ["id1", ...],
          "processed_ids_max": 10000,
          "schema_version": "1"
        }
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._ids: list[str] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._ids = data.get("processed_ids", [])
        except Exception as exc:
            print(f"[gmail-watcher] WatcherState load error: {exc}", file=sys.stderr)
            self._ids = []

    def contains(self, message_id: str) -> bool:
        return message_id in self._ids

    def add(self, message_id: str) -> None:
        if message_id not in self._ids:
            self._ids.append(message_id)
        # Enforce FIFO cap
        if len(self._ids) > STATE_MAX_IDS:
            self._ids = self._ids[-STATE_MAX_IDS:]

    def save(self) -> None:
        """Atomic write via temp file + rename."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "last_poll": datetime.now(timezone.utc).isoformat(),
            "processed_ids": self._ids,
            "processed_ids_max": STATE_MAX_IDS,
            "schema_version": SCHEMA_VERSION,
        }
        tmp = self.path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            os.replace(str(tmp), str(self.path))
        except Exception as exc:
            print(f"[gmail-watcher] WatcherState save error: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Task file writer
# ---------------------------------------------------------------------------

def _write_inbox_file(vault_path: Path, msg: dict) -> Path | None:
    """Write an EMAIL_<message-id>.md task file to Vault/Inbox/."""
    msg_id = msg["message_id"]
    filename = f"EMAIL_{msg_id}.md"
    dest = vault_path / "Inbox" / filename

    if dest.exists():
        return None  # Already written (race condition guard)

    # Determine priority
    labels = msg.get("labels", [])
    is_starred = "STARRED" in labels
    is_important = "IMPORTANT" in labels
    priority = "high" if (is_starred or is_important) else "normal"

    received = msg.get("date", datetime.now(timezone.utc).isoformat())
    from_addr = msg.get("from", "")
    subject = msg.get("subject", "(No Subject)")
    body_text = msg.get("body_text", "").strip()
    thread_id = msg.get("thread_id", "")

    # Extract from_name from "Name <email>" format
    from_name = from_addr
    if "<" in from_addr:
        from_name = from_addr.split("<")[0].strip().strip('"')

    # Known-sender check (simple: check if @reply-to address looks like internal contact)
    # For now just flag unknown if there's no display name
    flags = []
    if not from_name or from_name == from_addr:
        flags.append("unknown_sender")

    flags_yaml = "\n".join(f"  - {f}" for f in flags) if flags else ""
    flags_block = f"flags:\n{flags_yaml}" if flags_yaml else "flags: []"

    content = f"""\
---
type: email
source: gmail
status: unprocessed
message_id: "{msg_id}"
thread_id: "{thread_id}"
from: "{from_addr}"
from_name: "{from_name}"
subject: "{subject}"
received: "{received}"
priority: {priority}
has_attachments: false
labels: {json.dumps(labels)}
{flags_block}
---

# Email — Requires Action

**From**: {from_name} (`{from_addr}`)
**Subject**: {subject}
**Received**: {received}

## Message Body

{body_text if body_text else "(empty body)"}

## Required Action

Review and respond. For outbound reply, the AI will create an approval
file in `Vault/Pending_Approval/`.
"""

    try:
        (vault_path / "Inbox").mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        print(f"[gmail-watcher] Wrote {filename}")
        return dest
    except Exception as exc:
        print(f"[gmail-watcher] Failed to write {filename}: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# GmailWatcher — T026
# ---------------------------------------------------------------------------

class GmailWatcher:
    """Polls Gmail inbox and writes task files to Vault/Inbox/."""

    def __init__(self, vault_path: Path) -> None:
        self.vault = vault_path
        self.state = WatcherState(STATE_PATH)

    def _fetch_unread_important(self) -> list[dict]:
        """Fetch unread emails from Gmail — IMPORTANT/starred only."""
        from mcp_servers.gmail.tools.list_emails import list_emails
        from mcp_servers.gmail.tools.read_email import read_email

        # Filter: unread AND (IMPORTANT label OR starred)
        result = list_emails(
            query="is:unread (label:important OR is:starred)",
            max_results=20,
        )

        if result.get("isError"):
            raise RuntimeError(f"Gmail list_emails error: {result.get('error')}")

        emails = result.get("emails", [])
        enriched = []
        for email_meta in emails:
            msg_id = email_meta.get("message_id", "")
            if not msg_id or self.state.contains(msg_id):
                continue

            # Fetch full content
            full = read_email(msg_id)
            if full.get("isError"):
                print(f"[gmail-watcher] read_email error for {msg_id}: {full.get('error')}", file=sys.stderr)
                continue

            enriched.append({
                **email_meta,
                "body_text": full.get("body_text", ""),
                "body_html": full.get("body_html", ""),
            })

        return enriched

    def poll_once(self) -> int:
        """Run a single poll cycle. Returns the number of new emails written."""
        emails = self._fetch_unread_important()
        count = 0
        for msg in emails:
            msg_id = msg["message_id"]
            written = _write_inbox_file(self.vault, msg)
            if written:
                self.state.add(msg_id)
                count += 1
                log_action(
                    self.vault,
                    action_type="email_received",
                    actor="fte-gmail-watcher",
                    source=msg_id,
                    destination=str(written),
                    result="success",
                )
        self.state.save()
        return count


# ---------------------------------------------------------------------------
# Run loop — T028 (crash recovery)
# ---------------------------------------------------------------------------

def run_gmail_watcher(vault_path: Path, interval: int = POLL_INTERVAL) -> None:
    """Run the Gmail watcher as a blocking polling loop.

    Catches all exceptions, sleeps 15s, retries (crash recovery per T028).
    Systemd Restart=always handles process-level restart.
    """
    shutdown_requested = False

    def _shutdown(signum, frame):  # noqa: ARG001
        nonlocal shutdown_requested
        shutdown_requested = True

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    watcher = GmailWatcher(vault_path)
    print(f"[gmail-watcher] Started. Polling Gmail every {interval}s.")

    log_action(
        vault_path,
        action_type="system_start",
        actor="fte-gmail-watcher",
        parameters={"interval": interval, "vault_path": str(vault_path)},
        result="success",
    )

    while not shutdown_requested:
        try:
            count = watcher.poll_once()
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] Gmail poll complete — {count} new email(s) written to Inbox/")
        except Exception as exc:
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] Gmail watcher error: {exc}", file=sys.stderr)
            log_action(
                vault_path,
                action_type="error",
                actor="fte-gmail-watcher",
                result="error",
                error_message=str(exc),
            )
            # Crash recovery: sleep and retry (T028)
            for _ in range(RETRY_SLEEP):
                if shutdown_requested:
                    break
                time.sleep(1)
            continue

        # Normal sleep between polls
        for _ in range(interval):
            if shutdown_requested:
                break
            time.sleep(1)

    log_action(
        vault_path,
        action_type="system_shutdown",
        actor="fte-gmail-watcher",
        result="success",
    )
    print("[gmail-watcher] Stopped.")
