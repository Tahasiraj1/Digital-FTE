# ADR-0004: Action Execution via Claude Subprocess with Constrained Tool Access

- **Status:** Accepted
- **Date:** 2026-02-27
- **Feature:** 003-silver-functional-assistant
- **Context:** Silver tier requires executing four outbound action types after user approval: send email reply, send WhatsApp reply, create calendar event, post to LinkedIn. The `fte-action-executor` daemon must dispatch these actions within 30s of finding an `Approved/` file (FR-007). The question is what mechanism to use for dispatching: extend the existing `claude -p` subprocess pattern (already proven in Bronze), call action APIs directly from Python (no Claude involvement), or use direct MCP JSON-RPC calls.

  A critical safety constraint is that **zero outbound actions may occur without a file in `Approved/`** (FR-010 + SC-009). Any dispatch mechanism must preserve this guarantee. The orchestrator already uses `claude -p` successfully for planning; reusing this pattern for execution is architecturally consistent.

## Decision

Use **`claude -p` subprocess with `--allowedTools` constraint** for all action dispatch:

- **Mechanism**: `fte-action-executor` reads an `Approved/` file, invokes `claude -p --allowedTools "mcp__gmail__send_email,mcp__google-calendar__create_event,mcp__whatsapp__send_message,mcp__linkedin__create_post" -p "<action-specific system prompt>"` with a 30s timeout
- **Tool constraint**: `--allowedTools` explicitly whitelists only the four outbound tools — Claude cannot read inbox files, modify Plans/, or access filesystem outside the action boundary during execution
- **Safety gate**: Executor only invokes subprocess after reading a valid `Approved/` file with correct frontmatter (`action_type`, `expiry_at`, target fields). No file → no subprocess call. This is the sole HITL gate.
- **Dispatch table** (action_type → tools):
  - `email_reply` → `mcp__gmail__send_email`
  - `whatsapp_reply` → `mcp__whatsapp__send_message` (via IPC bridge to Node.js watcher)
  - `calendar_event` → `mcp__google-calendar__create_event`
  - `linkedin_post` → `mcp__linkedin__create_post` (LinkedIn MCP skill)
- **Post-dispatch**: Executor moves file to `Done/` on success or `Failed/` on timeout/error; writes result to frontmatter
- **Expiry enforcement**: Background thread in executor runs every 5 minutes, parses `expiry_at` from all `Approved/` and `Pending_Approval/` files, moves expired files to `Rejected/` without invoking subprocess
- **Timeout**: 30s `subprocess.run(timeout=30)` — hard kill on breach; file moved to `Failed/`

## Consequences

### Positive

- Claude interprets the action instructions from the approval frontmatter and maps them to the correct MCP tool call — no hardcoded parameter mapping in Python for each action type
- `--allowedTools` provides a hard boundary: even if the system prompt is manipulated via a crafted approval file, Claude cannot access tools outside the whitelist
- Architecturally consistent with the orchestrator pattern (Bronze) — same subprocess invocation model, same error handling, same timeout mechanism
- Expiry thread runs independently of dispatch — expired approvals are cleaned up even if the executor is idle with no new approvals
- Moving the file to `Done/`/`Failed/` after dispatch is atomic (rename, not copy+delete) — no duplicate execution on restart
- File-based dispatch log (frontmatter result field) is human-readable and auditable without a database

### Negative

- Each action dispatch spawns a new `claude -p` subprocess — ~2–4s Claude API latency added to every action, even simple ones like sending a pre-drafted message
- `--allowedTools` requires knowing all four tool names at deploy time — adding a fifth action type requires updating the executor's allowed-tools list (minor but not zero-cost)
- WhatsApp dispatch requires an IPC bridge (Unix socket or HTTP) from the Python executor to the Node.js whatsapp-web.js watcher — this cross-runtime boundary is the most fragile interface in Silver (documented as risk in plan.md)
- If Claude API is unavailable, all action dispatch halts until the API recovers — no offline fallback for outbound actions
- 30s timeout may be too tight for LinkedIn OAuth2 token refresh + API call in the same subprocess invocation; if so, timeout must be tuned per action type

## Alternatives Considered

**Alternative A: Direct Python API Calls (no Claude subprocess)**
- Pros: No Claude API latency; lower cost per action; deterministic execution (no LLM reasoning involved)
- Cons: Requires Python code for every action type's parameter mapping and API client; each new action type requires new Python implementation; loses the flexibility of Claude interpreting free-text instructions from approval files; more code to maintain and test
- Rejected: The approval file contains free-text instructions (e.g., "reply to this email saying thanks for reaching out, keep it brief") that require language understanding to convert to the correct API call — Python can't do this without reimplementing a rule engine

**Alternative B: Direct MCP JSON-RPC Calls from Python (no Claude subprocess)**
- Pros: No LLM involvement; faster than subprocess; direct protocol access
- Cons: Requires Python to implement MCP client protocol (stdio/socket transport, JSON-RPC framing, tool-call serialization) — significant implementation effort; the MCP tool call parameters must still be determined from free-text instructions (same problem as Alternative A)
- Rejected: Same language-understanding gap as Alternative A; adds MCP client implementation burden with no benefit over the proven subprocess pattern

**Alternative C: Extend Orchestrator to Handle Approved/ Directly**
- Rejected: Covered in ADR-0001 — incompatible timeout and concurrency requirements. The orchestrator's 120s Claude timeout and `in_flight` guard create an effective single-threaded event loop that cannot meet the 30s action SLA.

## References

- Feature Spec: `specs/003-silver-functional-assistant/spec.md` (FR-007, FR-010, SC-009)
- Implementation Plan: `specs/003-silver-functional-assistant/plan.md` — Phase 7 (action executor), Phase 8 (integration)
- Research: `specs/003-silver-functional-assistant/research.md` — Decision 4 (HITL architecture)
- Contracts: `specs/003-silver-functional-assistant/contracts/action-executor-interface.md`
- Related ADRs: ADR-0001 (service topology — defines executor as separate service), ADR-0003 (MCP servers — provides the tools used by executor)
