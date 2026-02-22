"""Tests for fte.orchestrator — polling and Claude invocation."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fte.orchestrator import (
    _list_needs_action,
    _move_to_in_progress,
    invoke_claude,
)


# ---------------------------------------------------------------------------
# _list_needs_action
# ---------------------------------------------------------------------------

def test_list_needs_action_empty(vault: Path):
    assert _list_needs_action(vault) == []


def test_list_needs_action_returns_files(vault: Path, needs_action_file: Path):
    files = _list_needs_action(vault)
    assert len(files) == 1
    assert files[0] == needs_action_file


def test_list_needs_action_sorted(vault: Path):
    for name in ["c.md", "a.md", "b.md"]:
        (vault / "Needs_Action" / name).write_text("content")
    files = _list_needs_action(vault)
    names = [f.name for f in files]
    assert names == sorted(names)


def test_list_needs_action_ignores_dirs(vault: Path):
    (vault / "Needs_Action" / "subdir").mkdir()
    files = _list_needs_action(vault)
    assert files == []


def test_list_needs_action_missing_dir(tmp_path: Path):
    """Should return empty list when Needs_Action/ doesn't exist."""
    assert _list_needs_action(tmp_path) == []


# ---------------------------------------------------------------------------
# _move_to_in_progress
# ---------------------------------------------------------------------------

def test_move_to_in_progress(vault: Path, needs_action_file: Path):
    _move_to_in_progress(vault, [needs_action_file])
    assert not needs_action_file.exists()
    assert (vault / "In_Progress" / needs_action_file.name).exists()


def test_move_to_in_progress_logs_action(vault: Path, needs_action_file: Path):
    _move_to_in_progress(vault, [needs_action_file])
    log_file = next((vault / "Logs").glob("*.json"))
    content = log_file.read_text()
    assert "file_move" in content
    assert "orchestrator" in content


def test_move_to_in_progress_multiple_files(vault: Path):
    files = []
    for name in ["task1.md", "task2.md", "task3.md"]:
        f = vault / "Needs_Action" / name
        f.write_text("content")
        files.append(f)

    _move_to_in_progress(vault, files)

    in_progress = list((vault / "In_Progress").iterdir())
    assert len(in_progress) == 3
    for f in files:
        assert not f.exists()


# ---------------------------------------------------------------------------
# invoke_claude — mocked subprocess
# ---------------------------------------------------------------------------

def test_invoke_claude_success(vault: Path, needs_action_file: Path):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = invoke_claude(vault, [needs_action_file])

    assert result is True
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "claude"
    assert "-p" in cmd
    assert "--add-dir" in cmd


def test_invoke_claude_prompt_mentions_files(vault: Path, needs_action_file: Path):
    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        invoke_claude(vault, [needs_action_file])

    prompt = mock_run.call_args[0][0][2]  # third element is the prompt
    assert needs_action_file.name in prompt


def test_invoke_claude_not_found(vault: Path, needs_action_file: Path):
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = invoke_claude(vault, [needs_action_file])

    assert result is False
    log_file = next((vault / "Logs").glob("*.json"))
    content = log_file.read_text()
    assert "error" in content
    assert "not found" in content.lower()


def test_invoke_claude_nonzero_exit(vault: Path, needs_action_file: Path):
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "some error"

    with patch("subprocess.run", return_value=mock_result):
        result = invoke_claude(vault, [needs_action_file])

    assert result is False
    log_file = next((vault / "Logs").glob("*.json"))
    content = log_file.read_text()
    assert "error" in content


def test_invoke_claude_timeout(vault: Path, needs_action_file: Path):
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=120)):
        result = invoke_claude(vault, [needs_action_file])

    assert result is False
    log_file = next((vault / "Logs").glob("*.json"))
    content = log_file.read_text()
    assert "timeout" in content.lower()


def test_invoke_claude_logs_success(vault: Path, needs_action_file: Path):
    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("subprocess.run", return_value=mock_result):
        invoke_claude(vault, [needs_action_file])

    log_file = next((vault / "Logs").glob("*.json"))
    entries = [json.loads(l) for l in log_file.read_text().splitlines() if l.strip()]
    reasoning_entries = [e for e in entries if e["action_type"] == "reasoning"]
    assert len(reasoning_entries) == 1
    assert reasoning_entries[0]["result"] == "success"
