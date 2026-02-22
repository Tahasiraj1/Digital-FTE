"""Tests for fte.watcher — filesystem watcher behaviour."""

import time
from pathlib import Path

import pytest
from fte.watcher import InboxHandler


@pytest.fixture
def handler(vault: Path) -> InboxHandler:
    return InboxHandler(vault)


def test_move_file_adds_timestamp_prefix(vault: Path, handler: InboxHandler):
    src = vault / "Inbox" / "task.md"
    src.write_text("some content")

    handler._move_file(src)

    moved = list((vault / "Needs_Action").iterdir())
    assert len(moved) == 1
    assert moved[0].name.endswith("-task.md")
    # Timestamp prefix: YYYY-MM-DD-HHMMSS-
    parts = moved[0].name.split("-")
    assert len(parts) >= 4  # at least year-month-day-...


def test_move_preserves_file_content(vault: Path, handler: InboxHandler):
    src = vault / "Inbox" / "note.md"
    src.write_text("important content")

    handler._move_file(src)

    moved = next((vault / "Needs_Action").iterdir())
    assert moved.read_text() == "important content"


def test_source_removed_after_move(vault: Path, handler: InboxHandler):
    src = vault / "Inbox" / "task.md"
    src.write_text("content")
    handler._move_file(src)
    assert not src.exists()


def test_move_logs_file_move_action(vault: Path, handler: InboxHandler):
    src = vault / "Inbox" / "task.md"
    src.write_text("content")
    handler._move_file(src)

    log_file = next((vault / "Logs").glob("*.json"))
    content = log_file.read_text()
    assert "file_move" in content
    assert "watcher" in content


def test_move_non_markdown_file(vault: Path, handler: InboxHandler):
    """Watcher is format-agnostic — must handle any file type."""
    src = vault / "Inbox" / "report.pdf"
    src.write_bytes(b"%PDF fake content")
    handler._move_file(src)

    moved = list((vault / "Needs_Action").iterdir())
    assert len(moved) == 1
    assert moved[0].name.endswith("-report.pdf")


def test_multiple_files_all_moved(vault: Path, handler: InboxHandler):
    files = ["a.md", "b.md", "c.txt"]
    for name in files:
        (vault / "Inbox" / name).write_text(f"content of {name}")

    for name in files:
        handler._move_file(vault / "Inbox" / name)

    moved = list((vault / "Needs_Action").iterdir())
    assert len(moved) == 3


def test_error_on_missing_source_logged(vault: Path, handler: InboxHandler):
    """Moving a non-existent file must log an error, not crash."""
    ghost = vault / "Inbox" / "ghost.md"
    # Don't create it — simulate race condition
    handler._move_file(ghost)

    log_file = next((vault / "Logs").glob("*.json"))
    content = log_file.read_text()
    assert "error" in content
