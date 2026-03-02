"""Vault initialization — create Obsidian folder structure."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fte.logger import log_action

if TYPE_CHECKING:
    pass

REQUIRED_DIRS = [
    "Inbox",
    "Needs_Action",
    "Plans",
    "Pending_Approval",
    "Approved",
    "Rejected",
    "Done",
    "In_Progress",
    "Logs",
]

COMPANY_HANDBOOK_CONTENT = """\
# Company Handbook

## Rules of Engagement

All outbound actions require explicit human approval. No auto-approve thresholds active.

### Email Rules
- All email replies require approval regardless of sender
- Replies to unknown senders MUST include `unknown_sender` in the approval file `flags` field
- Maximum 10 emails per hour

### LinkedIn Rules
- All posts require approval. Maximum 10 posts per day.
- Posts must not contain specific pricing or legal commitments without flagging `requires_human_review`

### Calendar Rules
- All calendar event creation requires approval
- Default timezone: Asia/Karachi (PKT, UTC+5)

### General Rules
- Never execute an action without an approved file in `Vault/Approved/`
- All actions are logged to `Vault/Logs/YYYY-MM-DD.json`

## Auto-Approve Thresholds

- All actions: NEVER (always require approval)

## Business Context

- [Describe your business here for Claude's reference]
- [e.g., "I run an AI consulting business serving SMEs"]
"""

DASHBOARD_CONTENT = """\
# Dashboard

> This file will be populated automatically in Silver tier.
> For now it serves as a placeholder.

## Status

- Vault initialized: yes
- Watcher: not running
- Orchestrator: not running
"""


def init_vault(vault_path: str | Path) -> list[tuple[str, str]]:
    """Create the vault folder structure idempotently.

    Returns a list of ``(item_name, "created" | "exists")`` tuples.
    """
    vault = Path(vault_path).expanduser().resolve()
    results: list[tuple[str, str]] = []

    # Create root
    created_root = not vault.exists()
    vault.mkdir(parents=True, exist_ok=True)

    # Create required subdirectories
    for dirname in REQUIRED_DIRS:
        dirpath = vault / dirname
        existed = dirpath.exists()
        dirpath.mkdir(parents=True, exist_ok=True)
        results.append((f"{dirname}/", "exists" if existed else "created"))

    # Create Company_Handbook.md (only if missing)
    handbook = vault / "Company_Handbook.md"
    if handbook.exists():
        results.append(("Company_Handbook.md", "exists"))
    else:
        handbook.write_text(COMPANY_HANDBOOK_CONTENT, encoding="utf-8")
        results.append(("Company_Handbook.md", "created"))

    # Create Dashboard.md (only if missing)
    dashboard = vault / "Dashboard.md"
    if dashboard.exists():
        results.append(("Dashboard.md", "exists"))
    else:
        dashboard.write_text(DASHBOARD_CONTENT, encoding="utf-8")
        results.append(("Dashboard.md", "created"))

    log_action(
        vault,
        action_type="vault_init",
        actor="system",
        destination=str(vault),
        parameters={"created_root": created_root},
        result="success",
    )

    return results
