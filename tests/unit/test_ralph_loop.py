"""Unit tests for src/fte/ralph_loop.py — Ralph Loop state management."""

import json
import os
from pathlib import Path

import pytest

from fte.ralph_loop import (
    RalphLoopState,
    clear_state,
    read_state,
    write_state,
    write_timeout_alert,
)


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """Minimal vault directory for Ralph Loop tests."""
    (tmp_path / "Needs_Action").mkdir()
    (tmp_path / "Done").mkdir()
    return tmp_path


@pytest.fixture
def sample_state() -> RalphLoopState:
    return RalphLoopState(
        loop_id="ralph-20260303-abc123",
        task_file="INVOICE_REQUEST_abc123_20260303.md",
        task_name="INVOICE_REQUEST_abc123_20260303",
        iteration=0,
        max_iterations=10,
        continuation_prompt="Continue working on the current task.",
        started_at="2026-03-03T10:00:00+00:00",
        chain_step=0,
        chain_cap=3,
    )


def test_read_state_missing_returns_none(vault: Path) -> None:
    """read_state returns None when ralph_state.json does not exist."""
    assert read_state(vault) is None


def test_write_read_roundtrip(vault: Path, sample_state: RalphLoopState) -> None:
    """Writing and reading state produces identical data."""
    write_state(vault, sample_state)

    loaded = read_state(vault)
    assert loaded is not None
    assert loaded.loop_id == sample_state.loop_id
    assert loaded.task_file == sample_state.task_file
    assert loaded.iteration == sample_state.iteration
    assert loaded.max_iterations == sample_state.max_iterations
    assert loaded.chain_step == sample_state.chain_step
    assert loaded.chain_cap == sample_state.chain_cap


def test_clear_state_removes_file(vault: Path, sample_state: RalphLoopState) -> None:
    """clear_state removes ralph_state.json."""
    write_state(vault, sample_state)
    assert (vault / "ralph_state.json").exists()

    clear_state(vault)
    assert not (vault / "ralph_state.json").exists()


def test_clear_state_noop_when_missing(vault: Path) -> None:
    """clear_state does not raise when no state file exists."""
    clear_state(vault)  # Should not raise


def test_timeout_alert_creates_file(vault: Path, sample_state: RalphLoopState) -> None:
    """write_timeout_alert creates SYSTEM_ralph-loop-timeout.md in Needs_Action/."""
    write_timeout_alert(vault, sample_state)

    alert_path = vault / "Needs_Action" / "SYSTEM_ralph-loop-timeout.md"
    assert alert_path.exists()

    content = alert_path.read_text(encoding="utf-8")
    assert "ralph_loop_timeout" in content
    assert sample_state.loop_id in content
    assert sample_state.task_file in content
    assert str(sample_state.max_iterations) in content


def test_write_state_atomic(vault: Path, sample_state: RalphLoopState) -> None:
    """Verify no temporary files are left on disk after write_state."""
    write_state(vault, sample_state)

    # Check no .tmp files remain
    tmp_files = list(vault.glob(".ralph_state_*.tmp"))
    assert len(tmp_files) == 0

    # Verify the state file exists and is valid JSON
    state_path = vault / "ralph_state.json"
    assert state_path.exists()
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["loop_id"] == sample_state.loop_id


def test_read_state_corrupt_json(vault: Path) -> None:
    """read_state returns None for corrupt JSON."""
    (vault / "ralph_state.json").write_text("not valid json{{{", encoding="utf-8")
    assert read_state(vault) is None


def test_write_state_overwrites(vault: Path, sample_state: RalphLoopState) -> None:
    """Writing state twice overwrites the previous state."""
    write_state(vault, sample_state)
    sample_state.iteration = 5
    write_state(vault, sample_state)

    loaded = read_state(vault)
    assert loaded is not None
    assert loaded.iteration == 5
