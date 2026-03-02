"""Filesystem watcher — monitors Inbox/ and moves files to Needs_Action/."""

from __future__ import annotations

import shutil
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from fte.lockfile import acquire_lock, release_lock
from fte.logger import log_action


class InboxHandler(FileSystemEventHandler):
    """Handles new files appearing in Inbox/."""

    def __init__(self, vault_path: Path) -> None:
        super().__init__()
        self.vault_path = vault_path
        self.needs_action = vault_path / "Needs_Action"

    def on_created(self, event) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        source = Path(event.src_path)
        # Small delay to let the file finish writing
        time.sleep(0.2)
        if source.exists():
            self._move_file(source)

    def _move_file(self, source: Path) -> None:
        """Move a file from Inbox to Needs_Action with timestamp prefix."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
        dest_name = f"{ts}-{source.name}"
        dest = self.needs_action / dest_name

        start = time.monotonic()
        try:
            shutil.move(str(source), str(dest))
            duration = int((time.monotonic() - start) * 1000)
            print(f"[{ts}] Moved: {source.name} → Needs_Action/{dest_name}")
            log_action(
                self.vault_path,
                action_type="file_move",
                actor="watcher",
                source=str(source),
                destination=str(dest),
                result="success",
                duration_ms=duration,
            )
        except Exception as exc:
            duration = int((time.monotonic() - start) * 1000)
            print(f"[{ts}] Error moving {source.name}: {exc}", file=sys.stderr)
            log_action(
                self.vault_path,
                action_type="error",
                actor="watcher",
                source=str(source),
                result="error",
                error_message=str(exc),
                duration_ms=duration,
            )


def _process_existing(handler: InboxHandler, inbox: Path) -> int:
    """Process pre-existing files in Inbox (catch-up on startup)."""
    count = 0
    for item in sorted(inbox.iterdir()):
        if item.is_file():
            handler._move_file(item)
            count += 1
    return count


def run_watcher(vault_path: Path, *, interval: int = 5) -> None:
    """Run the filesystem watcher as a blocking loop.

    Acquires a lockfile, watches Inbox/ for new files, and moves them to
    Needs_Action/ with a timestamp prefix. Handles SIGINT/SIGTERM for
    graceful shutdown.
    """
    inbox = vault_path / "Inbox"
    if not inbox.exists():
        print(f"Error: Inbox/ not found in {vault_path}. Run 'fte init' first.", file=sys.stderr)
        sys.exit(1)

    # Acquire lockfile
    try:
        acquire_lock(vault_path)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    handler = InboxHandler(vault_path)
    observer = PollingObserver(timeout=interval)
    observer.schedule(handler, str(inbox), recursive=False)

    shutdown_requested = False

    def _shutdown(signum, frame):  # noqa: ARG001
        nonlocal shutdown_requested
        shutdown_requested = True

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Log startup
    log_action(
        vault_path,
        action_type="system_start",
        actor="watcher",
        parameters={"interval": interval, "vault_path": str(vault_path)},
        result="success",
    )

    # Catch-up: process existing files
    catchup_count = _process_existing(handler, inbox)
    if catchup_count:
        print(f"Catch-up: processed {catchup_count} existing file(s) from Inbox/")

    observer.start()
    print(f"Watcher started. Monitoring Inbox/ at {vault_path}/")

    try:
        while not shutdown_requested:
            time.sleep(interval)
    finally:
        observer.stop()
        observer.join()
        release_lock(vault_path)
        log_action(
            vault_path,
            action_type="system_shutdown",
            actor="watcher",
            result="success",
        )
        print("\nWatcher stopped.")
