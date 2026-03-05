"""Unit tests for src/fte/actions/odoo.py — mock JSON-RPC."""

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import frontmatter as fm

from fte.vault import init_vault


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    init_vault(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def _odoo_env(monkeypatch):
    """Set Odoo env vars for all tests."""
    monkeypatch.setenv("ODOO_URL", "http://localhost:8069")
    monkeypatch.setenv("ODOO_DB", "fte_db")
    monkeypatch.setenv("ODOO_USERNAME", "admin")
    monkeypatch.setenv("ODOO_API_KEY", "test-key")


def _make_draft_approval(vault: Path) -> Path:
    """Create a sample create_odoo_invoice approval file."""
    path = vault / "Approved" / "ODOO_DRAFT_acme_20260303-100000.md"
    post = fm.Post(
        "# Draft Invoice — Acme Corp\n",
        action_type="create_odoo_invoice",
        source_task="INVOICE_REQUEST_abc123_20260303.md",
        ralph_loop_id="ralph-20260303-abc123",
        client_name="Acme Corp",
        client_email="billing@acme.com",
        line_items=[{"description": "AI Consulting", "quantity": 5, "unit_price": 100.0}],
        amount_total=500.0,
        requires_human_review=True,
        created_at="2026-03-03T10:00:00Z",
        expiry_at="2026-03-04T10:00:00Z",
        status="approved",
        chain_step=0,
    )
    path.write_text(fm.dumps(post), encoding="utf-8")
    return path


def _make_confirm_approval(vault: Path) -> Path:
    """Create a sample confirm_odoo_invoice approval file."""
    path = vault / "Approved" / "ODOO_CONFIRM_42_20260303-100100.md"
    post = fm.Post(
        "# Confirm Invoice 42\n",
        action_type="confirm_odoo_invoice",
        odoo_invoice_id=42,
        client_name="Acme Corp",
        client_email="billing@acme.com",
        ralph_loop_id="ralph-20260303-abc123",
        created_at="2026-03-03T10:01:00Z",
        expiry_at="2026-03-04T10:01:00Z",
        status="approved",
    )
    path.write_text(fm.dumps(post), encoding="utf-8")
    return path


@patch("fte.actions.odoo._jsonrpc")
def test_create_invoice_writes_confirm_approval(mock_rpc, vault: Path) -> None:
    from fte.actions.odoo import create_odoo_invoice_handler, _auth_cache
    _auth_cache.clear()

    # Mock: login returns uid=2, create returns invoice_id=42
    mock_rpc.side_effect = [2, 42]

    approved = _make_draft_approval(vault)
    create_odoo_invoice_handler(approved, vault)

    # Verify confirm approval was written
    confirms = list((vault / "Pending_Approval").glob("ODOO_CONFIRM_42_*.md"))
    assert len(confirms) == 1

    post = fm.load(str(confirms[0]))
    assert post.get("action_type") == "confirm_odoo_invoice"
    assert post.get("odoo_invoice_id") == 42
    assert post.get("requires_human_review") is True
    assert post.get("ralph_loop_id") == "ralph-20260303-abc123"


@patch("fte.actions.odoo._jsonrpc")
def test_confirm_invoice_calls_action_post(mock_rpc, vault: Path) -> None:
    from fte.actions.odoo import confirm_odoo_invoice_handler, _auth_cache
    _auth_cache.clear()

    # Mock: login returns uid=2, action_post returns True, email returns True
    mock_rpc.side_effect = [2, True, True]

    approved = _make_confirm_approval(vault)
    confirm_odoo_invoice_handler(approved, vault)

    # Verify two execute_kw calls were made (action_post + action_invoice_sent)
    assert mock_rpc.call_count == 3  # login + action_post + email


@patch("fte.actions.odoo._jsonrpc")
def test_odoo_unreachable_writes_system_alert(mock_rpc, vault: Path) -> None:
    from fte.actions.odoo import create_odoo_invoice_handler, _auth_cache
    _auth_cache.clear()

    mock_rpc.side_effect = ConnectionError("Connection refused")

    approved = _make_draft_approval(vault)
    with pytest.raises(ConnectionError):
        create_odoo_invoice_handler(approved, vault)

    # Verify system alert was written
    alert = vault / "Needs_Action" / "SYSTEM_odoo-unreachable.md"
    assert alert.exists()
    content = alert.read_text()
    assert "odoo-unreachable" in content


@patch("fte.actions.odoo._jsonrpc")
def test_create_invoice_requires_human_review_flag(mock_rpc, vault: Path) -> None:
    from fte.actions.odoo import create_odoo_invoice_handler, _auth_cache
    _auth_cache.clear()

    mock_rpc.side_effect = [2, 99]

    approved = _make_draft_approval(vault)
    create_odoo_invoice_handler(approved, vault)

    confirms = list((vault / "Pending_Approval").glob("ODOO_CONFIRM_99_*.md"))
    assert len(confirms) == 1
    post = fm.load(str(confirms[0]))
    assert post.get("requires_human_review") is True
