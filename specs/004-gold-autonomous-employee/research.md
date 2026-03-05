# Phase 0 Research: Gold Tier — Autonomous Employee

**Date**: 2026-03-03 | **Branch**: `004-gold-autonomous-employee`

---

## 1. Ralph Wiggum Loop (Stop Hook Pattern)

**Decision**: Implement a custom `scripts/ralph-loop.sh` Stop hook with dual-completion strategy, adapted from the Anthropic reference plugin.

**How Stop hooks work in Claude Code**:
- Configured in `.claude/settings.json` under `hooks.Stop`
- When Claude finishes its turn and tries to exit, the Stop hook script runs
- Hook receives a JSON object on stdin with `last_output` (Claude's full final response) and `transcript_path`
- **Exit 0** → Claude exits normally (loop stops)
- **Exit non-zero** → Claude Code re-injects a new prompt and iterates (loop continues)

**Dual-completion strategy (per spec FR-002)**:

| Condition | Detection | Exit |
|-----------|-----------|------|
| Approval gate reached | `<promise>AWAITING_APPROVAL</promise>` in `last_output` | 0 (clean exit; executor re-triggers after dispatch) |
| Task complete (autonomous) | Task file found in `Vault/Done/` | 0 (clean exit) |
| Not done, within limit | Neither of above | 1 (re-inject continuation prompt) |
| Max iterations reached | `iteration >= max_iterations` | 0 (write timeout alert, clean exit) |

**State management**: `Vault/ralph_state.json` — persists between iterations, visible in Obsidian.
```json
{
  "loop_id": "ralph-20260303-abc123",
  "task_file": "INVOICE_REQUEST_abc123_20260303.md",
  "iteration": 2,
  "max_iterations": 10,
  "continuation_prompt": "...",
  "started_at": "2026-03-03T10:00:00Z"
}
```

**Continuation task pattern (FR-004)**: Executor drops `CONTINUATION_<task>_<ts>.md` into `Needs_Action/` after dispatching an approved action that belongs to a Ralph Loop chain. The presence of `ralph_loop_id` frontmatter field on the approval file signals this.

**Reference plugin**: `https://github.com/anthropics/claude-code/tree/main/.claude/plugins/ralph-wiggum` — exists but requires adaptation for FTE's vault paths and dual-completion logic.

**Token cost per iteration** (claude-sonnet-4-6 at ~30k token context):
- Input: ~30,000 tokens ≈ $0.09
- Output: ~2,000–4,000 tokens ≈ $0.012–$0.024
- **Per-iteration total: ~$0.10–$0.12**
- Typical 5-step chain with 2 HITL pauses ≈ **$0.70–$0.85 total**
- No idle-spinning cost during HITL pauses (promise exit stops the loop)

**Rationale**: Custom bash script (~80 lines) is the correct approach — no distributed package exists, and FTE needs vault-specific paths and the dual-completion logic that the generic reference plugin does not provide.

**Alternatives considered**:
- Persistent daemon polling loop: rejected (burns CPU and tokens even when idle)
- systemd timer re-invocation: rejected (loses in-progress chain state between runs)

---

## 2. agent-browser (Vercel Labs)

**Decision**: Use `agent-browser` npm package with `--session-name` for persistent sessions. Invoke as subprocess from Python executor action handlers.

**Installation**: `npm install -g agent-browser`

**Architecture**: Rust CLI + Node.js daemon. Daemon starts automatically on first use and persists between commands (no manual daemon management needed).

**Session persistence**:
- Sessions stored automatically in `~/.agent-browser/sessions/` when `--session-name` flag is used
- `agent-browser --session-name facebook open facebook.com` → automatically loads/saves session
- Manual backup: `agent-browser state save ~/.config/fte/facebook-session.json`
- Session restore: `agent-browser state load ~/.config/fte/facebook-session.json`
- Encryption: `AGENT_BROWSER_ENCRYPTION_KEY` env var
- Auto-expiry: `AGENT_BROWSER_STATE_EXPIRE_DAYS`

**Key CLI pattern for FTE**:
```bash
# Facebook post
agent-browser --session-name facebook open facebook.com
agent-browser --session-name facebook snapshot -i    # get accessibility tree
agent-browser --session-name facebook click @e5      # click post box
agent-browser --session-name facebook type "Post text..."
agent-browser --session-name facebook click @e12     # submit
agent-browser --session-name facebook close
```

**Token efficiency**: 200–400 tokens per snapshot vs 3,000–5,000 for full DOM — critical for keeping Ralph Loop iteration costs low.

**Python subprocess integration**:
```python
import subprocess
result = subprocess.run(
    ["agent-browser", "--session-name", "facebook", "open", "https://facebook.com"],
    capture_output=True, text=True, timeout=30
)
```

**Known issues**:
- Facebook/Instagram UI changes can break selectors — executor must detect `browser-automation-failed` pattern and create system alert
- Platform rate limits and account restrictions must be detected via page content check (not just HTTP status)
- Session invalidation (platform logout) requires re-authentication flow — handled by `SYSTEM_social-session-expired.md` alert

**Rationale**: agent-browser avoids Meta API review entirely, uses same persistent session pattern as WhatsApp in Silver, and integrates cleanly as a subprocess. No daemon management overhead.

**Alternatives considered**:
- Playwright MCP: 10–15× more tokens per action; rejected
- Meta Graph API: requires Business account + app review; rejected for personal accounts
- Selenium: requires chromedriver management; more fragile; rejected

---

## 3. Odoo Community — MCP Server

**Decision**: Use `mcp-odoo-adv` by AlanOgic via `npx -y mcp-odoo-adv`. Deploy Odoo 17/18 via Docker Compose (odoo:19 image not yet available on Docker Hub as of research date; upgrade when released).

**MCP server config** (`.mcp.json` or `~/.claude.json`):
```json
{
  "mcpServers": {
    "odoo": {
      "command": "npx",
      "args": ["-y", "mcp-odoo-adv"],
      "env": {
        "ODOO_URL": "http://localhost:8069",
        "ODOO_DB": "fte_db",
        "ODOO_USERNAME": "admin",
        "ODOO_PASSWORD": "${ODOO_API_KEY}"
      }
    }
  }
}
```

**Key JSON-RPC operations** (all via `/web/dataset/call_kw`):

| Operation | Model | Method |
|-----------|-------|--------|
| Create draft invoice | `account.move` | `create` with `move_type: out_invoice` |
| Confirm invoice | `account.move` | `action_post` with invoice ID |
| Query outstanding invoices | `account.move` | `search_read` with payment_state != paid |
| Monthly revenue | `account.move` | `read_group` aggregated by month |

**Docker Compose** (`deploy/docker-compose.odoo.yml`):
- `postgres:15` + `odoo:17` (upgrade to `odoo:19` when tag available)
- Ports: `8069` (HTTP), `8072` (long-polling)
- Volumes: `pgdata`, `odoodata`

**Executor-side Odoo actions** (`src/fte/actions/odoo.py`):
- `confirm_and_send_invoice(invoice_id, recipient_email)` — calls `action_post` then triggers email via Odoo's built-in send mechanism
- All calls use direct JSON-RPC (not MCP server) since executor actions run outside Claude Code context

**Known issues**:
- No `odoo:19` Docker tag as of August 2025 — use `odoo:17` or `odoo:18`, plan upgrade path
- `action_post` returns `True` (not action dict) via JSON-RPC in Odoo 16+ — handle accordingly
- Use Odoo API keys (Settings → Technical → API Keys) not raw passwords in `.env`

**Rationale**: `mcp-odoo-adv` exposes `odoo_call_method` needed for `action_post`. `npx` means no local install maintenance. Docker isolates Odoo from FTE Python environment.

**Alternatives considered**:
- Direct JSON-RPC Python client only: rejected — Claude needs MCP to reason about Odoo at runtime
- xmlrpc.client forks: fewer tools, less maintained; rejected

---

## 4. Cross-Domain Continuation Task Pattern

**Decision**: Approval files belonging to a Ralph Loop chain carry a `ralph_loop_id` frontmatter field. After executor dispatches the action, it drops a `CONTINUATION_<original_task>_<ts>.md` into `Needs_Action/` to re-trigger the loop.

**Continuation file schema**:
```yaml
---
type: ralph_continuation
ralph_loop_id: "ralph-20260303-abc123"
original_task: "INVOICE_REQUEST_abc123_20260303.md"
step_completed: "confirm_odoo_invoice"
created_at: "2026-03-03T10:05:00Z"
---

# Task Continuation

Step `confirm_odoo_invoice` completed. Resume the invoice chain: send thank-you email and update client status.
```

**Chain cap**: 3 downstream actions (config value `RALPH_CHAIN_CAP=3` in `.env`).

**Deduplication**: Orchestrator checks `ralph_state.json.loop_id` before starting a new loop — if an active loop with the same ID exists, the trigger is dropped and logged.

---

## 5. Orchestrator Briefing Scheduler

**Decision**: New method `_check_briefing_schedule(vault_path)` added to the orchestrator main loop. Reads `Vault/briefing_state.json`, compares with configured schedule (default: Sunday 23:00 PKT = 18:00 UTC), drops briefing task if due.

**State file** (`Vault/briefing_state.json`):
```json
{
  "last_run": "2026-03-01T18:00:00Z",
  "schedule_utc_weekday": 6,
  "schedule_utc_hour": 18,
  "schedule_utc_minute": 0
}
```

**Logic**:
1. On every orchestrator poll cycle, `_check_briefing_schedule()` runs
2. Computes next scheduled time from `last_run` + schedule config
3. If `now >= next_scheduled_time`: write `CEO_BRIEFING_<date>.md` to `Needs_Action/`, update `last_run`
4. If machine was offline during scheduled time, triggers on next poll cycle (catch-up behavior from FR-019)
