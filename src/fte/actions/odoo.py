"""Odoo JSON-RPC action handlers — Gold Tier.

Executor-side actions for Odoo invoice management. Uses direct JSON-RPC
(not MCP) since executor runs outside Claude Code context.

Handlers:
  create_odoo_invoice_handler — creates draft invoice, writes confirm approval
  confirm_odoo_invoice_handler — posts invoice + triggers email send
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

import frontmatter

JSONRPC_TIMEOUT = 15  # seconds

# Module-level auth cache
_auth_cache: dict[str, object] = {}


def _get_odoo_config() -> tuple[str, str, str, str]:
    """Read Odoo connection details from environment."""
    url = os.environ.get("ODOO_URL", "http://localhost:8069")
    db = os.environ.get("ODOO_DB", "fte_db")
    username = os.environ.get("ODOO_USERNAME", "")
    password = os.environ.get("ODOO_API_KEY", os.environ.get("ODOO_PASSWORD", "admin"))
    return url, db, username, password


def _jsonrpc(url: str, service: str, method: str, args: list) -> object:
    """Execute a JSON-RPC call to Odoo."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": service,
            "method": method,
            "args": args,
        },
        "id": 1,
    }).encode("utf-8")

    req = Request(
        f"{url}/jsonrpc",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urlopen(req, timeout=JSONRPC_TIMEOUT) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if "error" in result:
                raise RuntimeError(f"Odoo JSON-RPC error: {result['error']}")
            return result.get("result")
    except URLError as exc:
        raise ConnectionError(f"Cannot reach Odoo at {url}: {exc}") from exc


def _authenticate(url: str, db: str, username: str, password: str) -> int:
    """Authenticate with Odoo and return uid."""
    cache_key = f"{url}:{db}:{username}"
    if cache_key in _auth_cache:
        return _auth_cache[cache_key]  # type: ignore[return-value]

    uid = _jsonrpc(url, "common", "login", [db, username, password])
    if not uid:
        raise RuntimeError("Odoo authentication failed")
    _auth_cache[cache_key] = uid
    return uid  # type: ignore[return-value]


def _write_system_alert(vault: Path, alert_type: str, details: str) -> None:
    """Write a SYSTEM_ alert to Needs_Action/."""
    now = datetime.now(timezone.utc).isoformat()
    alert_path = vault / "Needs_Action" / f"SYSTEM_{alert_type}.md"
    alert_path.write_text(
        f"---\ntype: system_alert\nalert_type: {alert_type}\ncreated_at: \"{now}\"\n---\n\n"
        f"# {alert_type.replace('-', ' ').title()}\n\n{details}\n",
        encoding="utf-8",
    )


def create_odoo_invoice_handler(approved_path: Path, vault: Path) -> None:
    """Create a draft invoice in Odoo from an approved request.

    After creating the draft, writes a confirm approval file to Pending_Approval/.
    """
    post = frontmatter.load(str(approved_path))

    url, db, username, password = _get_odoo_config()

    try:
        uid = _authenticate(url, db, username, password)
    except ConnectionError:
        _write_system_alert(
            vault, "odoo-unreachable",
            f"Could not connect to Odoo at `{url}`. The action `create_odoo_invoice` was not dispatched.\n\n"
            f"**Action required**: Start Odoo with `docker compose -f deploy/docker-compose.odoo.yml up -d` and retry."
        )
        raise

    # Build invoice line items
    line_items = post.get("line_items", [])
    invoice_lines = []
    for item in line_items:
        invoice_lines.append([0, 0, {
            "name": item.get("description", "Service"),
            "quantity": float(item.get("quantity", 1)),
            "price_unit": float(item.get("unit_price", 0)),
        }])

    # Create draft invoice
    invoice_id = _jsonrpc(url, "object", "execute_kw", [
        db, uid, password,
        "account.move", "create",
        [{
            "move_type": "out_invoice",
            "invoice_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "invoice_line_ids": invoice_lines,
        }],
    ])

    # Write confirm approval to Pending_Approval/
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d-%H%M%S")
    confirm_path = vault / "Pending_Approval" / f"ODOO_CONFIRM_{invoice_id}_{ts}.md"

    client_name = post.get("client_name", "Unknown")
    client_email = post.get("client_email", "")
    amount_total = post.get("amount_total", 0)
    ralph_loop_id = post.get("ralph_loop_id", "")
    source_task = post.get("source_task", approved_path.name)

    confirm_fm = {
        "action_type": "confirm_odoo_invoice",
        "source_task": source_task,
        "odoo_invoice_id": invoice_id,
        "client_name": client_name,
        "client_email": client_email,
        "amount_total": amount_total,
        "requires_human_review": True,
        "created_at": now.isoformat(),
        "expiry_at": (now + timedelta(hours=24)).isoformat(),
        "status": "pending",
        "flags": [],
    }
    if ralph_loop_id:
        confirm_fm["ralph_loop_id"] = ralph_loop_id
        confirm_fm["chain_step"] = int(post.get("chain_step", 0))
        confirm_fm["chain_context"] = {
            "odoo_invoice_id": invoice_id,
            "client_email": client_email,
            "client_name": client_name,
        }

    confirm_post = frontmatter.Post(
        f"# Confirm Odoo Invoice — {client_name}\n\n"
        f"Invoice ID: {invoice_id}\n"
        f"Amount: {amount_total}\n\n"
        f"**To Approve**: Move this file to Approved/\n"
        f"**To Reject**: Move this file to Rejected/\n",
        **confirm_fm,
    )
    confirm_path.write_text(frontmatter.dumps(confirm_post), encoding="utf-8")
    print(f"[odoo] Draft invoice {invoice_id} created. Confirm approval written: {confirm_path.name}")


def confirm_odoo_invoice_handler(approved_path: Path, vault: Path) -> None:
    """Confirm (post) an Odoo invoice and trigger email send."""
    post = frontmatter.load(str(approved_path))
    invoice_id = post.get("odoo_invoice_id")
    if not invoice_id:
        raise ValueError("Missing odoo_invoice_id in approval file")

    url, db, username, password = _get_odoo_config()

    try:
        uid = _authenticate(url, db, username, password)
    except ConnectionError:
        _write_system_alert(
            vault, "odoo-unreachable",
            f"Could not connect to Odoo at `{url}`. The action `confirm_odoo_invoice` was not dispatched.\n\n"
            f"**Action required**: Start Odoo with `docker compose -f deploy/docker-compose.odoo.yml up -d` and retry."
        )
        raise

    # Confirm invoice (action_post)
    _jsonrpc(url, "object", "execute_kw", [
        db, uid, password,
        "account.move", "action_post",
        [[invoice_id]],
    ])

    # Trigger email send
    _jsonrpc(url, "object", "execute_kw", [
        db, uid, password,
        "account.move", "action_invoice_sent",
        [[invoice_id]],
    ])

    print(f"[odoo] Invoice {invoice_id} confirmed and email triggered.")
