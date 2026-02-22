"""Structured JSONL logger for the FTE vault."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def log_action(
    vault_path: str | Path,
    *,
    action_type: str,
    actor: str,
    source: str | None = None,
    destination: str | None = None,
    parameters: dict | None = None,
    result: str = "success",
    error_message: str | None = None,
    duration_ms: int | None = None,
) -> None:
    """Append a single JSONL log entry to Logs/YYYY-MM-DD.json.

    Never raises — prints to stderr on failure so callers are not disrupted.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": action_type,
        "actor": actor,
        "source": source,
        "destination": destination,
        "parameters": parameters or {},
        "result": result,
        "error_message": error_message,
        "duration_ms": duration_ms,
    }

    try:
        logs_dir = Path(vault_path) / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = logs_dir / f"{today}.json"

        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(f"[FTE] Failed to write log: {exc}", file=sys.stderr)
