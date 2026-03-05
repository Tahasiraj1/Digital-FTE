# Implementation Plan: Gold Tier — Autonomous Employee

**Branch**: `004-gold-autonomous-employee` | **Date**: 2026-03-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-gold-autonomous-employee/spec.md`

---

## Summary

Gold tier transforms the Silver FTE from a single-action HITL assistant into a **multi-step autonomous employee**. Three new integrations ship (Odoo ERP, Facebook, Instagram) alongside the **Ralph Wiggum loop** — a Claude Code Stop hook that keeps Claude iterating across a task chain until completion or explicit approval pause. The CEO Briefing provides a weekly autonomous audit of all domains.

The core architectural insight is the **dual-completion + continuation-task pattern**: the loop exits cleanly at approval gates (promise-based) so tokens are never burned idle, and the executor re-triggers the loop after each dispatch by dropping a continuation task into `Needs_Action/`. All new capabilities build on Silver's existing file-movement pipeline with zero changes to the core HITL safety model.

---

## Technical Context

**Language/Version**: Python 3.13+ (all FTE Python code) | Bash (ralph-loop.sh) | Node.js (agent-browser, mcp-odoo-adv)
**Primary Dependencies**:
  - `agent-browser` — npm global (`npm install -g agent-browser`); browser automation for Facebook + Instagram
  - `mcp-odoo-adv` — npx (`npx -y mcp-odoo-adv`); Odoo JSON-RPC MCP server; no local install
  - `python-frontmatter` — already in pyproject.toml; used by ralph_loop.py state management
  - `docker` + `docker compose` — Odoo + PostgreSQL container orchestration

**Storage**:
  - `Vault/ralph_state.json` — Ralph Loop iteration state (single file, atomic writes)
  - `Vault/briefing_state.json` — CEO Briefing schedule tracker
  - `~/.agent-browser/sessions/` — Facebook/Instagram browser sessions (agent-browser native)
  - `~/.config/fte/` — session backups
  - `~/.env` — Odoo API key, Ralph config (never in vault)

**Testing**: pytest (unit tests for ralph_loop.py, odoo.py helpers); manual integration tests per domain

**Target Platform**: Linux WSL2 (primary); scripts use absolute vault paths from env

**Performance Goals**:
  - Odoo invoice confirmed + emailed ≤ 2 min after approval (SC-002)
  - Social post published ≤ 60s after approval (SC-003)
  - CEO Briefing generated ≤ 3 min after trigger (SC-004)
  - Ralph Loop complete task chain ≤ 10 min including one HITL pause (SC-001)

**Constraints**:
  - Cross-domain chain cap: 3 downstream actions (`RALPH_CHAIN_CAP=3` in `.env`)
  - Ralph Loop max iterations: 10 per loop (`RALPH_MAX_ITERATIONS=10` in `.env`)
  - Odoo API key, not raw password, in env (Security principle V)
  - No financial data or session tokens leave local machine (SC-010)

**Scale/Scope**: Single-user (Taha). 1–5 Ralph Loop chains per day expected. No concurrent multi-user concerns.

---

## Constitution Check

*GATE: Pre-Phase 0. Re-evaluated post-design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Local-First Privacy** | ✅ PASS | Odoo runs in local Docker. Social sessions in `~/.agent-browser/sessions/`. No data leaves machine. `ralph_state.json` and `briefing_state.json` in vault. Session files gitignored. |
| **II. Human-in-the-Loop Safety (NON-NEGOTIABLE)** | ✅ PASS | Every outbound action (invoice confirm, email, social post) requires approval file in `Pending_Approval/`. Ralph Loop exits cleanly at approval gates via `<promise>AWAITING_APPROVAL</promise>`. FR-010 mandates `requires_human_review: true` on all Odoo financial actions. FR-016 mandates approval for all social posts. |
| **III. Perception-Reasoning-Action Pipeline** | ✅ PASS | Orchestrator (perception) drops tasks into `Needs_Action/`. Claude + Ralph Loop (reasoning) creates approval files and plans. Executor (action) dispatches only after approval. No layer bypasses another. |
| **IV. Agent Skill Architecture** | ✅ PASS | All Gold AI capabilities packaged as Claude Code skills: `odoo-invoice`, `social-post`, `ceo-briefing` (FR-005, SC-008). Ralph Loop itself is infrastructure, not a skill. |
| **V. Security by Default** | ✅ PASS | Odoo API key in `.env` (never plain text). Browser sessions gitignored. `DEV_MODE` gate on all real actions. |
| **VI. Observability & Auditability** | ✅ PASS | All Gold tier actions logged to `Vault/Logs/YYYY-MM-DD.json` with new action types (FR-023). Dashboard updated per cycle (FR-024). |
| **VII. Autonomous Persistence (Ralph Wiggum Pattern)** | ✅ PASS | Ralph Loop implements exactly this principle with dual-completion strategy. Max 10 iterations (configurable). Timeout creates system alert. |
| **VIII. Incremental Delivery** | ✅ PASS | Gold builds on Silver. No Silver functionality removed. Ralph Loop is additive. |

**Post-design re-check**: All gates still pass. No violations.

---

## Project Structure

### Documentation (this feature)

```text
specs/004-gold-autonomous-employee/
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # Entities, state transitions, log types
├── quickstart.md        # Setup guide for Gold tier
├── contracts/
│   ├── approval-schemas.md   # Frontmatter schemas for all new approval types
│   └── mcp-config.md         # Odoo MCP and agent-browser config
└── tasks.md             # Generated by /sp.tasks (NOT this command)
```

### Source Code (additions to existing structure)

```text
scripts/
└── ralph-loop.sh            # Stop hook script (~80 lines bash)

src/fte/
├── ralph_loop.py            # Ralph Loop state management (read/write/check ralph_state.json)
├── actions/
│   ├── odoo.py              # Odoo JSON-RPC: confirm_invoice, get_summary
│   ├── facebook.py          # agent-browser subprocess: publish post, collect metrics
│   └── instagram.py         # agent-browser subprocess: publish post
├── executor.py              # EXTEND: add Gold action types, continuation task logic
└── orchestrator.py          # EXTEND: briefing scheduler, Ralph Loop task routing

.claude/
└── skills/
    ├── odoo-invoice/
    │   └── SKILL.md         # "Draft an Odoo invoice from a task file"
    ├── social-post/
    │   └── SKILL.md         # "Draft Facebook and Instagram posts from a task file"
    └── ceo-briefing/
        └── SKILL.md         # "Generate CEO Briefing from vault logs"

.claude/
└── settings.json            # EXTEND: add Stop hook for ralph-loop.sh

deploy/
└── docker-compose.odoo.yml  # Odoo 17/18 + PostgreSQL containers

tests/
├── unit/
│   ├── test_ralph_loop.py   # State management, completion detection, timeout
│   └── test_odoo_actions.py # Mock JSON-RPC: confirm, query
└── integration/
    └── test_gold_chain.py   # End-to-end: task → approval → continuation → done
```

**Structure Decision**: Single project (existing FTE Python package). All additions are extensions to the existing `src/fte/` package — no new top-level packages. `scripts/` is a new top-level directory for infrastructure scripts (ralph-loop.sh follows the same pattern as `deploy/` scripts).

---

## Architecture Design

### A. Ralph Wiggum Loop

**Component**: `scripts/ralph-loop.sh` (Stop hook) + `src/fte/ralph_loop.py` (state helper)

**Flow**:
```
orchestrator detects ralph_loop: true task
       ↓
writes Vault/ralph_state.json (loop_id, task_file, iteration=0, max=10)
       ↓
invokes: claude -p "<ralph skill prompt>" --add-dir Vault/Needs_Action/
       ↓
Claude works... tries to exit
       ↓
Stop hook: scripts/ralph-loop.sh fires
       ├── reads ralph_state.json from vault
       ├── checks last_output for <promise>AWAITING_APPROVAL</promise>
       │       → exit 0 (loop pauses, executor will re-trigger after dispatch)
       ├── checks Done/<task_file> exists
       │       → exit 0 (task complete, delete ralph_state.json)
       ├── iteration < max_iterations
       │       → increment iteration, write continuation_prompt, exit 1 (re-inject)
       └── iteration >= max_iterations
               → write SYSTEM_ralph-loop-timeout.md, exit 0
```

**Orchestrator changes** (`orchestrator.py`):
- Detect `ralph_loop: true` frontmatter in task files
- Route to Ralph skill instead of generic Claude invocation
- Write `ralph_state.json` before Claude invocation
- Clean up `ralph_state.json` after Claude exits cleanly

**Executor changes** (`executor.py`):
- After dispatching any action with `ralph_loop_id` frontmatter: drop `CONTINUATION_<task>_<ts>.md` into `Needs_Action/`
- Continuation file includes `ralph_loop: true`, `ralph_loop_id`, `step_completed`, and next-step hint

**Guard**: If `ralph_state.json` does not exist when the Stop hook fires, exit 0 immediately (no-op for normal orchestrator invocations).

---

### B. Odoo Integration

**Reasoning** (Claude + MCP during Ralph Loop):
- `mcp-odoo-adv` registered in `.mcp.json` — Claude calls `odoo_call_method` to create draft invoice
- Claude writes `ODOO_DRAFT_*.md` to `Pending_Approval/` with draft invoice details
- Claude outputs `<promise>AWAITING_APPROVAL</promise>` — loop exits cleanly

**Action** (executor after approval):
- `src/fte/actions/odoo.py` — direct JSON-RPC Python client (no MCP)
- `confirm_invoice(invoice_id)` → `action_post` → marks invoice as posted
- `send_invoice_email(invoice_id, email)` → Odoo built-in email trigger
- Returns invoice PDF path for logging

**New executor dispatch entries**:
```python
DISPATCH_TABLE = {
    ...  # existing Silver entries
    "create_odoo_invoice": "fte.actions.odoo",     # creates draft; writes confirm approval
    "confirm_odoo_invoice": "fte.actions.odoo",    # action_post + email send
}
```

**Odoo client authentication** (`odoo.py`):
- Auth once per executor restart, cache `(uid, session)` in module-level variable
- Re-auth on `AccessDenied` exception
- Timeout: 15s per JSON-RPC call

---

### C. Facebook & Instagram Integration

**Reasoning** (Claude during Ralph Loop):
- Claude reads social post task, drafts platform-specific content
- Uses the `social-post` skill — writes `SOCIAL_facebook_*.md` and `SOCIAL_instagram_*.md`
- Outputs `<promise>AWAITING_APPROVAL</promise>` for each platform

**Action** (executor after approval):
- `src/fte/actions/facebook.py` + `instagram.py` — subprocess calls to agent-browser CLI
- Session loaded automatically via `--session-name facebook` / `--session-name instagram`
- DEV_MODE: logs CLI command without executing it
- Error detection: check subprocess stdout for platform error indicators (rate limit, restriction)
- Session invalidation detection: check for login page redirect

**Session backup** (not in executor dispatch path — one-time manual setup):
- `agent-browser state save ~/.config/fte/<platform>-session.json`
- Run after initial login; repeat after session restore

**agent-browser subprocess pattern**:
```python
def _browser(session: str, *args, timeout: int = 60) -> str:
    result = subprocess.run(
        ["agent-browser", "--session-name", session, *args],
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        raise BrowserActionError(result.stderr)
    return result.stdout
```

---

### D. CEO Briefing Scheduler

**Orchestrator change** (`orchestrator.py`):

New private method `_check_briefing_schedule(vault_path)` called in the main polling loop after `_update_dashboard()`:

```python
def _check_briefing_schedule(vault_path: Path) -> None:
    state_file = vault_path / "briefing_state.json"
    # Read last_run + schedule config
    # Compute next scheduled time (next Sunday 18:00 UTC after last_run)
    # If now >= next_scheduled: write CEO_BRIEFING_<date>.md to Needs_Action/
    #   update last_run in state_file
    # Else: no-op
```

**Deduplication**: Before writing briefing task, check if `CEO_BRIEFING_<same-date>.md` already exists in `Needs_Action/` or `In_Progress/` — if so, skip and log.

**CEO Briefing task file** (dropped by orchestrator):
```yaml
---
type: ceo_briefing
ralph_loop: true
---
# CEO Briefing Request
Generate the weekly CEO briefing report for the week ending <date>.
Aggregate data from Vault/Logs/ for the past 7 days across all domains.
Write report to Vault/Plans/CEO_Briefing_<date>.md.
When complete, move this task to Done/ and output <promise>TASK_COMPLETE</promise>.
```

**Completion**: Fully autonomous — no approval gate. Loop exits via file-movement (CEO Briefing task → Done/) and `<promise>TASK_COMPLETE</promise>`.

---

### E. Cross-Domain Chain Architecture

**Chain cap enforcement**: Orchestrator reads `chain_step` from `ralph_state.json`. If `chain_step >= RALPH_CHAIN_CAP` (default 3), no more continuation tasks are dropped — log a chain-cap-reached entry and move task to Done/.

**Per-action approval**: Each outbound action gets its own approval file. A single approval file authorizes exactly one action (FR-022).

**Chain context propagation**: The continuation task carries a `chain_context` JSON object with relevant IDs (e.g., `odoo_invoice_id`, `client_email`) so Claude doesn't need to re-query Odoo on each step.

---

## Implementation Phases

### Phase 1 — Ralph Loop Foundation (prerequisite for all Gold features)
1. `scripts/ralph-loop.sh` — Stop hook with dual-completion logic
2. `src/fte/ralph_loop.py` — state read/write/check helpers
3. `.claude/settings.json` — Stop hook registration
4. `orchestrator.py` — Ralph Loop task routing + state init
5. `executor.py` — continuation task drop logic
6. Unit tests: `tests/unit/test_ralph_loop.py`

### Phase 2 — Odoo Integration
1. `deploy/docker-compose.odoo.yml` — Odoo + PostgreSQL
2. `.mcp.json` — `mcp-odoo-adv` config entry
3. `src/fte/actions/odoo.py` — JSON-RPC client
4. `.env` additions: `ODOO_API_KEY`, `ODOO_DB`, `ODOO_URL`
5. `executor.py` — add Odoo entries to DISPATCH_TABLE
6. `.claude/skills/odoo-invoice/SKILL.md` — Claude skill
7. Unit tests: `tests/unit/test_odoo_actions.py` (mock JSON-RPC)

### Phase 3 — Facebook & Instagram Integration
1. `npm install -g agent-browser` (documented in deploy script)
2. Session setup: manual login + `agent-browser state save`
3. `src/fte/actions/facebook.py` — agent-browser subprocess + session validation
4. `src/fte/actions/instagram.py` — agent-browser subprocess
5. `executor.py` — add social entries to DISPATCH_TABLE
6. `.claude/skills/social-post/SKILL.md` — Claude skill

### Phase 4 — CEO Briefing
1. `orchestrator.py` — `_check_briefing_schedule()` method
2. `Vault/briefing_state.json` — initial state file (created by `fte init` extension)
3. `.claude/skills/ceo-briefing/SKILL.md` — Claude skill
4. Integration test: manual trigger + verify report in `Plans/`

### Phase 5 — Integration & Audit Logging
1. `src/fte/logger.py` — add Gold tier action types
2. `orchestrator.py` — Dashboard updates for Gold metrics
3. Integration test: `tests/integration/test_gold_chain.py` — full invoice chain
4. Checkpoint validation (per Constitution principle VIII): trigger → reasoning → approval → action → log

---

## Risk Analysis

| Risk | Blast Radius | Mitigation |
|------|-------------|------------|
| Ralph Loop Stop hook fires on non-loop invocations | Medium — unexpected re-injection | Guard: check `ralph_state.json` exists before any logic; exit 0 if absent |
| Facebook/Instagram UI change breaks selectors | Low — posting fails gracefully | Browser action errors create system alert; no silent failures; selectors documented for manual update |
| Odoo Docker unavailable during chain | Medium — approval dispatch fails | `odoo.py` creates `SYSTEM_odoo-unreachable.md` alert; executor moves file to Rejected/ with reason |
| Ralph Loop idle-spinning (token waste) | Medium — billing | Promise-based exit at approval gates eliminates idle spin; max iterations cap as backstop |
| Chain exceeds cap mid-execution | Low — chain truncated | `chain_step` counter checked before each continuation drop; cap-reached logged and chain closed cleanly |

---

## Complexity Tracking

No constitution violations. No additional complexity justification required.

---

## ADR Suggestion

📋 **Architectural decision detected**: Ralph Loop dual-completion strategy (promise-based exit at HITL gates vs file-movement for autonomous steps) is a significant architectural decision with long-term consequences for all future multi-step capabilities.

Document reasoning and tradeoffs? Run `/sp.adr ralph-loop-dual-completion`
