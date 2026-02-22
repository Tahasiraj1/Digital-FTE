"""PID-based lockfile manager for single-instance enforcement."""

from __future__ import annotations

import os
import sys
from pathlib import Path

LOCK_FILENAME = ".watcher.lock"


def _is_pid_running(pid: int) -> bool:
    """Check whether a process with the given PID is alive."""
    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        SYNCHRONIZE = 0x00100000
        handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            # Process exists but we can't signal it.
            return True


def acquire_lock(vault_path: str | Path) -> Path:
    """Create a lockfile with the current PID.

    Returns the lockfile path on success.
    Raises ``RuntimeError`` if another live instance holds the lock.
    """
    lock_path = Path(vault_path) / LOCK_FILENAME

    if lock_path.exists():
        try:
            existing_pid = int(lock_path.read_text().strip())
        except (ValueError, OSError):
            existing_pid = None

        if existing_pid is not None and _is_pid_running(existing_pid):
            raise RuntimeError(
                f"Another instance is running (PID {existing_pid}). "
                f"Remove {lock_path} if this is stale."
            )

    lock_path.write_text(str(os.getpid()), encoding="utf-8")
    return lock_path


def release_lock(vault_path: str | Path) -> None:
    """Remove the lockfile if it exists."""
    lock_path = Path(vault_path) / LOCK_FILENAME
    try:
        lock_path.unlink(missing_ok=True)
    except OSError:
        pass
