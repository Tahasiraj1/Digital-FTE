"""Integration test for the full Gold chain: invoice → approve → continuation → cap.

Mocks Claude invocations and Odoo JSON-RPC to test the complete chain flow.
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
import frontmatter as fm

from fte.vault import init_vault
from fte.executor import _drop_continuation_task


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    init_vault(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("RALPH_CHAIN_CAP", "3")


def _make_approved_file(
    vault: Path, name: str, action_type: str, chain_step: int = 0, **extra
) -> Path:
    """Create an approved file with ralph_loop_id."""
    path = vault / "Approved" / name
    data = {
        "action_type": action_type,
        "ralph_loop_id": "ralph-20260303-chain1",
        "source_task": "INVOICE_REQUEST_abc123_20260303.md",
        "chain_step": chain_step,
        "chain_context": extra.get("chain_context", {}),
        "status": "approved",
        "created_at": "2026-03-03T10:00:00Z",
        "expiry_at": "2026-03-04T10:00:00Z",
        **{k: v for k, v in extra.items() if k != "chain_context"},
    }
    post = fm.Post(f"# {action_type}\n", **data)
    path.write_text(fm.dumps(post), encoding="utf-8")
    return path


def test_full_invoice_chain_with_cap(vault: Path) -> None:
    """Test complete chain: step 0 → step 1 → step 2 → cap (no step 3).

    Each step is tested independently to avoid timestamp-collision on
    CONTINUATION filenames (same second = same filename = overwrite).
    """
    import time

    # Step 0: create_odoo_invoice → continuation at step 1
    a0 = _make_approved_file(
        vault, "ODOO_DRAFT_acme_20260303-100000.md",
        "create_odoo_invoice", chain_step=0,
        chain_context={"odoo_invoice_id": 42, "client_email": "test@example.com"},
    )
    _drop_continuation_task(vault, a0, "create_odoo_invoice")

    conts = sorted((vault / "Needs_Action").glob("CONTINUATION_*.md"))
    assert len(conts) == 1
    p0 = fm.load(str(conts[0]))
    assert p0.get("chain_step") == 1
    assert p0.get("step_completed") == "create_odoo_invoice"

    # Remove the first continuation to avoid filename collision
    conts[0].unlink()
    time.sleep(0.01)

    # Step 1: confirm_odoo_invoice → continuation at step 2
    a1 = _make_approved_file(
        vault, "ODOO_CONFIRM_42_20260303-100100.md",
        "confirm_odoo_invoice", chain_step=1,
        chain_context={"odoo_invoice_id": 42, "client_email": "test@example.com"},
    )
    _drop_continuation_task(vault, a1, "confirm_odoo_invoice")

    conts = sorted((vault / "Needs_Action").glob("CONTINUATION_*.md"))
    assert len(conts) == 1
    p1 = fm.load(str(conts[0]))
    assert p1.get("chain_step") == 2

    # Remove to avoid collision
    conts[0].unlink()

    # Step 2: send_email → chain_step becomes 3 which == cap → NO continuation
    a2 = _make_approved_file(
        vault, "EMAIL_REPLY_test_20260303-100200.md",
        "send_email", chain_step=2,
    )
    _drop_continuation_task(vault, a2, "send_email")

    conts = sorted((vault / "Needs_Action").glob("CONTINUATION_*.md"))
    assert len(conts) == 0  # Cap reached, no continuation


def test_no_continuation_without_ralph_loop_id(vault: Path) -> None:
    """Approved files without ralph_loop_id should NOT trigger continuations."""
    path = vault / "Approved" / "EMAIL_REPLY_normal_20260303-100300.md"
    post = fm.Post(
        "# Normal email\n",
        action_type="send_email",
        source_task="EMAIL_test.md",
        status="approved",
    )
    path.write_text(fm.dumps(post), encoding="utf-8")

    _drop_continuation_task(vault, path, "send_email")

    conts = list((vault / "Needs_Action").glob("CONTINUATION_*.md"))
    assert len(conts) == 0


def test_chain_context_propagated(vault: Path) -> None:
    """Verify chain_context from approved file appears in continuation task."""
    ctx = {"odoo_invoice_id": 99, "client_email": "billing@corp.com"}
    a = _make_approved_file(
        vault, "ODOO_DRAFT_corp_20260303-100400.md",
        "create_odoo_invoice", chain_step=0,
        chain_context=ctx,
    )
    _drop_continuation_task(vault, a, "create_odoo_invoice")

    conts = list((vault / "Needs_Action").glob("CONTINUATION_*.md"))
    assert len(conts) == 1

    content = conts[0].read_text()
    assert "99" in content  # odoo_invoice_id propagated
    assert "billing@corp.com" in content  # client_email propagated
