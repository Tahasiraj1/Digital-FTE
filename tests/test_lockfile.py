"""Tests for fte.lockfile — PID-based single-instance guard."""

import os
from pathlib import Path

import pytest
from fte.lockfile import acquire_lock, release_lock, LOCK_FILENAME


def test_acquire_creates_lockfile(tmp_path: Path):
    acquire_lock(tmp_path)
    assert (tmp_path / LOCK_FILENAME).exists()
    release_lock(tmp_path)


def test_lockfile_contains_current_pid(tmp_path: Path):
    acquire_lock(tmp_path)
    pid = int((tmp_path / LOCK_FILENAME).read_text().strip())
    assert pid == os.getpid()
    release_lock(tmp_path)


def test_release_removes_lockfile(tmp_path: Path):
    acquire_lock(tmp_path)
    release_lock(tmp_path)
    assert not (tmp_path / LOCK_FILENAME).exists()


def test_acquire_raises_if_live_lock_exists(tmp_path: Path):
    acquire_lock(tmp_path)
    with pytest.raises(RuntimeError, match="Another instance is running"):
        acquire_lock(tmp_path)
    release_lock(tmp_path)


def test_stale_lock_overwritten(tmp_path: Path):
    """A lockfile with a dead PID should be silently replaced."""
    lock_path = tmp_path / LOCK_FILENAME
    # Write a PID that almost certainly doesn't exist
    lock_path.write_text("99999999")
    # Should not raise
    acquire_lock(tmp_path)
    assert int(lock_path.read_text().strip()) == os.getpid()
    release_lock(tmp_path)


def test_release_is_idempotent(tmp_path: Path):
    """Releasing when no lockfile exists must not raise."""
    release_lock(tmp_path)  # no lock acquired
    release_lock(tmp_path)  # again — should not raise


def test_acquire_returns_lock_path(tmp_path: Path):
    result = acquire_lock(tmp_path)
    assert result == tmp_path / LOCK_FILENAME
    release_lock(tmp_path)
