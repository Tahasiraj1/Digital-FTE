"""FTE Action Executor — watches Vault/Approved/ and dispatches approved actions.

Architecture:
  - Main thread: PollingObserver on Vault/Approved/ (on_created handler)
  - Main thread: PollingObserver on Vault/Rejected/ (on_created handler, log only)
  - Background thread: expiry enforcement (scans Pending_Approval/ every 300s)

Environment:
  DEV_MODE=true  — logs what would happen but skips actual dispatch (safe for testing)
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from fte.logger import log_action

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DISPATCH_TABLE: dict[str, str] = {
    "send_email": "fte.actions.gmail",
    "send_whatsapp": "fte.actions.whatsapp",
    "create_calendar_event": "fte.actions.calendar",
    "publish_linkedin_post": "fte.actions.linkedin",
}

EXPIRY_CHECK_INTERVAL = 300  # seconds
ACTION_TIMEOUT = 30  # seconds
STABILITY_SLEEP = 0.2  # seconds before reading a new file


# ---------------------------------------------------------------------------
# Silver-aware log helper
# ---------------------------------------------------------------------------

def _log(
    vault: Path,
    *,
    action_type: str,
    actor: str = "fte-action-executor",
    source_task: str | None = None,
    approved_file: str | None = None,
    approval_status: str = "approved",
    approved_at: str | None = None,
    target: str | None = None,
    result: str = "success",
    error_message: str | None = None,
    duration_ms: int | None = None,
) -> None:
    """Log a Silver-tier action with extended fields."""
    log_action(
        vault,
        action_type=action_type,
        actor=actor,
        source=source_task,
        destination=target,
        parameters={
            "approved_file": approved_file,
            "approval_status": approval_status,
            "approved_at": approved_at,
            "approved_by": "user",
        },
        result=result,
        error_message=error_message,
        duration_ms=duration_ms,
    )


# ---------------------------------------------------------------------------
# Approved/ event handler
# ---------------------------------------------------------------------------

class ApprovedHandler(FileSystemEventHandler):
    """Handles files appearing in Vault/Approved/."""

    def __init__(self, vault: Path, dev_mode: bool) -> None:
        self.vault = vault
        self.dev_mode = dev_mode

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix != ".md":
            return
        _dispatch(path, self.vault, self.dev_mode)


# ---------------------------------------------------------------------------
# Rejected/ event handler (FR-008: log user-driven rejections, no action)
# ---------------------------------------------------------------------------

class RejectedHandler(FileSystemEventHandler):
    """Handles files appearing in Vault/Rejected/ — log only, no action."""

    def __init__(self, vault: Path) -> None:
        self.vault = vault

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix != ".md":
            return

        time.sleep(STABILITY_SLEEP)
        try:
            post = frontmatter.load(str(path))
            action_type = post.get("action_type", "unknown")
            status = post.get("status", "unknown")
            # Determine actor: if status was 'pending' when moved → user rejected it
            # If status is 'expired' or 'failed' → system rejected it
            actor = "user" if status == "pending" else "fte-action-executor"
            _log(
                self.vault,
                action_type=action_type,
                actor=actor,
                approved_file=str(path.relative_to(self.vault)),
                approval_status="rejected",
                result="rejected",
            )
            print(f"[executor] Rejection logged: {path.name} (status={status}, actor={actor})")
        except Exception as exc:
            print(f"[executor] Failed to log rejection for {path.name}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def _dispatch(approved_path: Path, vault: Path, dev_mode: bool) -> None:
    """Dispatch a single approved action file."""
    time.sleep(STABILITY_SLEEP)

    # --- Pre-execution checks ---
    try:
        post = frontmatter.load(str(approved_path))
    except Exception as exc:
        print(f"[executor] Failed to parse {approved_path.name}: {exc}", file=sys.stderr)
        return

    action_type = post.get("action_type", "")
    expiry_at_raw = post.get("expiry_at", "")
    created_at = post.get("created_at", "")

    # Check expiry
    if expiry_at_raw:
        try:
            expiry_at = datetime.fromisoformat(str(expiry_at_raw).replace("Z", "+00:00"))
            if expiry_at < datetime.now(timezone.utc):
                print(f"[executor] {approved_path.name} expired — moving to Rejected/")
                _move_to_rejected(approved_path, vault, "expired")
                _log(vault, action_type=action_type, approval_status="expired",
                     approved_file=str(approved_path.name), result="rejected")
                return
        except ValueError:
            pass

    # Check action_type is supported
    if action_type not in DISPATCH_TABLE:
        print(f"[executor] Unknown action_type '{action_type}' in {approved_path.name}", file=sys.stderr)
        _move_to_rejected(approved_path, vault, "unknown_action_type")
        return

    # Mark as executing (in-place frontmatter edit to prevent double-processing)
    _set_status(approved_path, "executing")

    start_ms = int(time.monotonic() * 1000)

    if dev_mode:
        print(f"[executor] DEV_MODE — would dispatch {action_type} from {approved_path.name}")
        _move_to_done(approved_path, vault)
        _log(vault, action_type=action_type, approved_file=str(approved_path.name),
             approved_at=datetime.now(timezone.utc).isoformat(),
             result="dev_mode_skipped", duration_ms=0)
        return

    # --- Real dispatch ---
    module_path = DISPATCH_TABLE[action_type]
    try:
        import importlib
        module = importlib.import_module(module_path)
        importlib.reload(module)  # pick up editable-install changes without restart
        handler_fn = getattr(module, f"{action_type}_handler", None)
        if handler_fn is None:
            raise AttributeError(f"No handler function in {module_path}")

        handler_fn(approved_path, vault)
        duration_ms = int(time.monotonic() * 1000) - start_ms
        _set_status(approved_path, "done")
        _move_to_done(approved_path, vault)
        _log(vault, action_type=action_type, approved_file=str(approved_path.name),
             approved_at=datetime.now(timezone.utc).isoformat(),
             result="success", duration_ms=duration_ms)
        print(f"[executor] ✓ {action_type} dispatched ({duration_ms}ms)")

    except Exception as exc:
        duration_ms = int(time.monotonic() * 1000) - start_ms
        print(f"[executor] ✗ {action_type} failed: {exc}", file=sys.stderr)
        _move_to_rejected(approved_path, vault, "failed")
        _log(vault, action_type=action_type, approved_file=str(approved_path.name),
             result="error", error_message=str(exc), duration_ms=duration_ms)


# ---------------------------------------------------------------------------
# File movement helpers
# ---------------------------------------------------------------------------

def _set_status(path: Path, status: str) -> None:
    """Update the status field in a frontmatter file in-place."""
    try:
        post = frontmatter.load(str(path))
        post["status"] = status
        with path.open("w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))
    except Exception as exc:
        print(f"[executor] Failed to set status on {path.name}: {exc}", file=sys.stderr)


def _move_to_done(src: Path, vault: Path) -> None:
    dest = vault / "Done" / src.name
    shutil.move(str(src), str(dest))


def _move_to_rejected(src: Path, vault: Path, reason: str) -> None:
    _set_status(src, reason)
    dest = vault / "Rejected" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))


# ---------------------------------------------------------------------------
# Expiry enforcement thread (T008)
# ---------------------------------------------------------------------------

def _expiry_thread(vault: Path, stop_event: threading.Event) -> None:
    """Background thread: move expired Pending_Approval files to Rejected/."""
    while not stop_event.wait(EXPIRY_CHECK_INTERVAL):
        pending_dir = vault / "Pending_Approval"
        now = datetime.now(timezone.utc)
        for md_file in pending_dir.glob("*.md"):
            try:
                post = frontmatter.load(str(md_file))
                expiry_raw = post.get("expiry_at", "")
                if not expiry_raw:
                    continue
                expiry_at = datetime.fromisoformat(str(expiry_raw).replace("Z", "+00:00"))
                if expiry_at < now:
                    action_type = post.get("action_type", "unknown")
                    print(f"[executor] Expiry: moving {md_file.name} to Rejected/")
                    _move_to_rejected(md_file, vault, "expired")
                    _log(vault, action_type=action_type,
                         approved_file=str(md_file.name),
                         approval_status="expired", result="rejected")
            except Exception as exc:
                print(f"[executor] Expiry check error for {md_file.name}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_executor(vault_path: str | Path, interval: int = 5, dev_mode: bool = False) -> None:
    """Start the action executor service loop."""
    # Flush stdout/stderr immediately so systemd journal captures every print()
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]

    vault = Path(vault_path).expanduser().resolve()

    if not vault.exists():
        print(f"[executor] Error: Vault not found at {vault}. Run 'fte init' first.", file=sys.stderr)
        sys.exit(1)

    dev_mode = dev_mode or os.environ.get("DEV_MODE", "").lower() in ("true", "1", "yes")
    if dev_mode:
        print("[executor] DEV_MODE=true — no real actions will be dispatched")

    # Ensure required dirs exist
    for d in ("Approved", "Rejected", "Pending_Approval", "Done"):
        (vault / d).mkdir(parents=True, exist_ok=True)

    print(f"[executor] Watching {vault}/Approved/ ...")

    approved_handler = ApprovedHandler(vault, dev_mode)
    rejected_handler = RejectedHandler(vault)

    observer = PollingObserver(timeout=interval)
    observer.schedule(approved_handler, str(vault / "Approved"), recursive=False)
    observer.schedule(rejected_handler, str(vault / "Rejected"), recursive=False)
    observer.start()

    stop_event = threading.Event()
    expiry_t = threading.Thread(target=_expiry_thread, args=(vault, stop_event), daemon=True)
    expiry_t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        observer.stop()
        observer.join()
        print("[executor] Stopped.")
