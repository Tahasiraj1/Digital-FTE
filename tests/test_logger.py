"""Tests for fte.logger — structured JSONL logging."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fte.logger import log_action


def test_creates_log_file(tmp_path: Path):
    log_action(tmp_path, action_type="file_move", actor="watcher", result="success")
    logs = list((tmp_path / "Logs").glob("*.json"))
    assert len(logs) == 1


def test_log_entry_is_valid_json(tmp_path: Path):
    log_action(tmp_path, action_type="file_move", actor="watcher", result="success")
    log_file = next((tmp_path / "Logs").glob("*.json"))
    line = log_file.read_text().strip()
    entry = json.loads(line)
    assert isinstance(entry, dict)


def test_log_entry_has_required_fields(tmp_path: Path):
    log_action(
        tmp_path,
        action_type="file_move",
        actor="watcher",
        source="/src",
        destination="/dst",
        result="success",
    )
    log_file = next((tmp_path / "Logs").glob("*.json"))
    entry = json.loads(log_file.read_text().strip())

    required = ["timestamp", "action_type", "actor", "source", "destination",
                "parameters", "result", "error_message", "duration_ms"]
    for field in required:
        assert field in entry, f"Missing field: {field}"


def test_timestamp_is_iso_utc(tmp_path: Path):
    log_action(tmp_path, action_type="test", actor="system", result="success")
    log_file = next((tmp_path / "Logs").glob("*.json"))
    entry = json.loads(log_file.read_text().strip())
    # Should parse without error
    dt = datetime.fromisoformat(entry["timestamp"])
    assert dt.tzinfo is not None


def test_multiple_entries_appended(tmp_path: Path):
    for i in range(3):
        log_action(tmp_path, action_type=f"action_{i}", actor="test", result="success")

    log_file = next((tmp_path / "Logs").glob("*.json"))
    lines = [l for l in log_file.read_text().splitlines() if l.strip()]
    assert len(lines) == 3


def test_each_line_independently_parseable(tmp_path: Path):
    for i in range(5):
        log_action(tmp_path, action_type="event", actor="test",
                   parameters={"i": i}, result="success")

    log_file = next((tmp_path / "Logs").glob("*.json"))
    for line in log_file.read_text().splitlines():
        if line.strip():
            entry = json.loads(line)
            assert entry["action_type"] == "event"


def test_creates_logs_dir_if_missing(tmp_path: Path):
    logs_dir = tmp_path / "Logs"
    assert not logs_dir.exists()
    log_action(tmp_path, action_type="test", actor="system", result="success")
    assert logs_dir.exists()


def test_error_fields_populated(tmp_path: Path):
    log_action(
        tmp_path,
        action_type="error",
        actor="watcher",
        result="error",
        error_message="Permission denied",
    )
    log_file = next((tmp_path / "Logs").glob("*.json"))
    entry = json.loads(log_file.read_text().strip())
    assert entry["result"] == "error"
    assert entry["error_message"] == "Permission denied"


def test_does_not_raise_on_bad_vault_path(tmp_path: Path):
    """Logger must never crash the caller even with a bad path."""
    bad_path = tmp_path / "nonexistent" / "vault"
    # Should not raise — creates Logs/ under bad_path
    log_action(bad_path, action_type="test", actor="system", result="success")
