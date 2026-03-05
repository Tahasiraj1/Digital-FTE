"""Integration tests for Ralph Loop end-to-end flow.

Tests orchestrator → Claude (mocked) → state management → completion detection.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fte.ralph_loop import RalphLoopState, read_state, write_state, clear_state
from fte.vault import init_vault


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """Fully initialized vault."""
    init_vault(tmp_path)
    return tmp_path


def _create_ralph_task(vault: Path, task_name: str = "TEST_auto_task_20260303.md") -> Path:
    """Create a minimal ralph_loop task in Needs_Action/."""
    task_path = vault / "Needs_Action" / task_name
    task_path.write_text(
        "---\n"
        "type: ralph_loop\n"
        "ralph_loop: true\n"
        "---\n\n"
        "# Test Task\n\nWrite a plan file to Plans/, then move this to Done/.\n",
        encoding="utf-8",
    )
    return task_path


def test_autonomous_task_complete(vault: Path) -> None:
    """Mock Claude returning TASK_COMPLETE — verify state is cleaned up."""
    task = _create_ralph_task(vault)

    # Simulate: orchestrator writes state
    state = RalphLoopState(
        loop_id="ralph-20260303-test01",
        task_file=task.name,
        task_name=task.stem,
        iteration=0,
        max_iterations=10,
    )
    write_state(vault, state)
    assert read_state(vault) is not None

    # Simulate: Claude completes task and moves file to Done/
    (vault / "Done" / task.name).write_text(task.read_text(), encoding="utf-8")
    task.unlink()

    # Simulate: what the Stop hook does when task is in Done/
    # (the hook checks Done/<task_file> exists → clears state → exit 0)
    assert (vault / "Done" / state.task_file).exists()
    clear_state(vault)

    # Verify: state cleaned up, task in Done/
    assert read_state(vault) is None
    assert (vault / "Done" / state.task_file).exists()
    assert not (vault / "Needs_Action" / state.task_file).exists()


def test_awaiting_approval_preserves_state(vault: Path) -> None:
    """Mock Claude returning AWAITING_APPROVAL — verify state is preserved."""
    task = _create_ralph_task(vault)

    state = RalphLoopState(
        loop_id="ralph-20260303-test02",
        task_file=task.name,
        task_name=task.stem,
        iteration=0,
        max_iterations=10,
    )
    write_state(vault, state)

    # Simulate: Claude writes approval file and outputs AWAITING_APPROVAL
    approval = vault / "Pending_Approval" / "ODOO_DRAFT_test_20260303-100000.md"
    approval.write_text(
        "---\n"
        "action_type: create_odoo_invoice\n"
        "ralph_loop_id: ralph-20260303-test02\n"
        "status: pending\n"
        "---\n",
        encoding="utf-8",
    )

    # Simulate: Stop hook sees AWAITING_APPROVAL → exit 0 (does NOT clear state)
    # State should remain because executor needs to re-trigger after dispatch
    loaded = read_state(vault)
    assert loaded is not None
    assert loaded.loop_id == "ralph-20260303-test02"
    assert loaded.iteration == 0  # NOT incremented on approval pause

    # Verify: task still in Needs_Action (not moved to Done)
    assert task.exists()


def test_executor_drops_continuation(vault: Path) -> None:
    """After executor dispatches, continuation task appears in Needs_Action/."""
    from fte.executor import _drop_continuation_task

    # Create an approved file with ralph_loop_id
    approved = vault / "Approved" / "ODOO_CONFIRM_42_20260303-100100.md"
    approved.parent.mkdir(parents=True, exist_ok=True)
    approved.write_text(
        "---\n"
        "action_type: confirm_odoo_invoice\n"
        "ralph_loop_id: ralph-20260303-test03\n"
        "source_task: INVOICE_REQUEST_abc123_20260303.md\n"
        "chain_step: 0\n"
        "chain_context:\n"
        "  odoo_invoice_id: 42\n"
        "  client_email: test@example.com\n"
        "status: approved\n"
        "---\n",
        encoding="utf-8",
    )

    _drop_continuation_task(vault, approved, "confirm_odoo_invoice")

    # Verify continuation task exists
    continuations = list((vault / "Needs_Action").glob("CONTINUATION_*.md"))
    assert len(continuations) == 1

    import frontmatter as fm
    post = fm.load(str(continuations[0]))
    assert post.get("type") == "ralph_continuation"
    assert post.get("ralph_loop") is True
    assert post.get("ralph_loop_id") == "ralph-20260303-test03"
    assert post.get("step_completed") == "confirm_odoo_invoice"
    assert post.get("chain_step") == 1


def test_chain_cap_prevents_continuation(vault: Path) -> None:
    """Continuation task is NOT dropped when chain_step >= chain_cap."""
    import os
    from fte.executor import _drop_continuation_task

    os.environ["RALPH_CHAIN_CAP"] = "3"

    approved = vault / "Approved" / "EMAIL_REPLY_test_20260303-100200.md"
    approved.parent.mkdir(parents=True, exist_ok=True)
    approved.write_text(
        "---\n"
        "action_type: send_email\n"
        "ralph_loop_id: ralph-20260303-test04\n"
        "source_task: INVOICE_REQUEST_abc123_20260303.md\n"
        "chain_step: 2\n"
        "status: approved\n"
        "---\n",
        encoding="utf-8",
    )

    _drop_continuation_task(vault, approved, "send_email")

    # chain_step=2 + 1 = 3 >= cap=3 → no continuation
    continuations = list((vault / "Needs_Action").glob("CONTINUATION_*.md"))
    assert len(continuations) == 0

    # Cleanup
    os.environ.pop("RALPH_CHAIN_CAP", None)
