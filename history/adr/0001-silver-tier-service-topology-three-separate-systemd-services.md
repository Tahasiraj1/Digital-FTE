# ADR-0001: Silver Tier Service Topology — Three Separate Systemd Services

- **Status:** Accepted
- **Date:** 2026-02-27
- **Feature:** 003-silver-functional-assistant
- **Context:** Silver tier must add inbound monitoring (Gmail, WhatsApp) and outbound action execution (email reply, WhatsApp reply, calendar event, LinkedIn post) to the existing Bronze system. The question is whether to extend the existing `fte-orchestrator` Python process to handle all new responsibilities, or introduce separate services for each new pipeline stage.

  The existing orchestrator runs Claude Code as a blocking subprocess with a 120s timeout, protected by an `in_flight` boolean guard (`orchestrator.py:184`). A new outbound action executor must execute approved actions within 30s (FR-007). These two responsibilities have fundamentally incompatible timeout and concurrency requirements.

## Decision

Add three new systemd services alongside the two existing Bronze services:

- **fte-gmail-watcher**: Python daemon, polls Gmail every 2 minutes, writes `EMAIL_*.md` to `Vault/Inbox/`
- **fte-whatsapp-watcher**: Node.js daemon using whatsapp-web.js, event-driven, writes `WHATSAPP_*.md` to `Vault/Inbox/`
- **fte-action-executor**: Python daemon, polls `Vault/Approved/`, dispatches approved actions via Claude subprocess (30s timeout), runs expiry enforcement as background thread

Each service owns exactly one pipeline stage transition:
```
fte-watcher          → Inbox/ → Needs_Action/
fte-orchestrator     → Needs_Action/ → Plans/ + Pending_Approval/
fte-gmail-watcher    → Gmail inbox → Inbox/
fte-whatsapp-watcher → WhatsApp events → Inbox/
fte-action-executor  → Approved/ → action execution → Done/
```

## Consequences

### Positive

- Independent restart policies — an executor crash does not interrupt Claude reasoning; a watcher crash does not block approvals
- Independent timeout budgets — executor enforces 30s without contending with orchestrator's 120s Claude timeout
- Mirrors and extends the established Bronze pattern (each service owns one stage) — low cognitive overhead
- Existing `lockfile.py` pattern reusable directly for all three new services
- Each service can be deployed, monitored, and scaled independently

### Negative

- Five systemd services to manage instead of two — higher operational surface area
- `deploy/install-silver.sh` and `deploy/uninstall-silver.sh` required in addition to Bronze deploy scripts
- WhatsApp watcher introduces Node.js as a second runtime alongside Python — see ADR-0002

## Alternatives Considered

**Alternative A: Extend orchestrator to watch Approved/ in the same process**
- Rejected: The orchestrator's 120s Claude timeout and `in_flight` guard create a de facto single-threaded event loop. An approval arriving during a Claude invocation would wait up to 120s before processing, violating the 30s action SLA. Merging the roles also violates single-responsibility and makes the orchestrator harder to test.

**Alternative B: Merge all Silver functionality into the orchestrator with threading**
- Rejected: Adds significant complexity to a process that already has a sensitive timeout/interrupt model. The Claude subprocess interaction is not thread-safe without careful locking. The risk of subtle concurrency bugs outweighs the operational simplicity of one fewer service.

**Alternative C: Single "Silver daemon" wrapping all three new responsibilities**
- Rejected: Gmail polling (2-min interval), WhatsApp events (real-time), and action execution (on-demand, 30s) have incompatible event models. A single daemon would need a complex async event loop. Separate services with simple polling are easier to reason about and restart independently.

## References

- Feature Spec: `specs/003-silver-functional-assistant/spec.md` (FR-004, FR-007)
- Implementation Plan: `specs/003-silver-functional-assistant/plan.md` — Service Topology section
- Research: `specs/003-silver-functional-assistant/research.md` — Decision 2
- Related ADRs: ADR-0002 (WhatsApp library), ADR-0004 (action execution pattern)
