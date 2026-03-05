# Feature Specification: Gold Tier — Autonomous Employee

**Feature Branch**: `004-gold-autonomous-employee`
**Created**: 2026-03-02
**Status**: Draft
**Input**: Gold tier: Autonomous AI Employee with Odoo ERP, Facebook/Instagram via browser automation, and Ralph Wiggum autonomous loop

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Autonomous Multi-Step Task Completion via Ralph Loop (Priority: P1)

A client sends an email requesting an invoice. The AI Employee detects the email, creates the invoice in Odoo, emails it to the client, posts a "closed a new deal" update on LinkedIn, and logs the transaction — all without Taha re-triggering anything. The Ralph Wiggum loop keeps Claude working through each step until the entire chain is marked Done.

**Why this priority**: This is the core leap from Silver to Gold. Silver handles one action per approval. Gold chains multiple actions across domains (email → Odoo → LinkedIn) autonomously. Without the Ralph Loop, Gold is just Silver with more integrations.

**Independent Test**: Drop a task file in `Needs_Action/` describing an invoice request. Start the Ralph Loop. Verify without manual re-triggering: Odoo invoice created, email draft in `Pending_Approval/`, once approved email sent, task file moved to `Done/`. The loop must stop automatically when the task reaches `Done/`.

**Acceptance Scenarios**:

1. **Given** a multi-step task file exists in `Needs_Action/`, **When** the Ralph Loop is started, **Then** Claude processes each step sequentially (plan → action → approval if needed → execute) without requiring manual re-triggering between steps.
2. **Given** a task file moves to `Done/`, **When** the Ralph Loop's Stop hook fires, **Then** the loop terminates automatically and does not re-process the completed task.
3. **Given** a step in the chain requires human approval (e.g., sending an email), **When** the approval file is placed in `Pending_Approval/`, **Then** the loop pauses and resumes automatically once the approval file is moved to `Approved/` or `Rejected/`.
4. **Given** a task step fails (e.g., Odoo API error), **When** the failure is logged, **Then** the loop writes an error entry to `Vault/Logs/` and halts that chain rather than silently continuing.
5. **Given** the loop reaches its max iteration limit, **When** the task is not yet complete, **Then** the system creates a `SYSTEM_ralph-loop-timeout.md` file in `Needs_Action/` and stops the loop.

---

### User Story 2 — Odoo Accounting Integration (Priority: P2)

A client asks via email for an invoice. The AI Employee creates the invoice in the local Odoo instance, emails it to the client, and logs the transaction. Taha can also request a business summary — revenue this month, outstanding invoices, top clients — and the AI reads from Odoo and writes a report to the vault.

**Why this priority**: Accounting transforms the AI from a communication tool into a business operations system. It enables the Monday Morning CEO Briefing and the cross-domain workflows that define Gold tier. It is the single most differentiating capability from Silver.

**Independent Test**: Send an email saying "Please send an invoice for the AI consulting project — $500 for 5 hours." Confirm: invoice draft created in Odoo with correct line items, approval file generated in `Pending_Approval/`, after approval invoice confirmed and emailed to sender, transaction logged in vault. Separately, trigger a business summary request and verify a report appears in `Plans/` with current Odoo figures.

**Acceptance Scenarios**:

1. **Given** a task file contains invoice creation intent (client name, amount, description), **When** the orchestrator processes it, **Then** a draft invoice is created in the local Odoo instance with the correct fields and an approval request is created in `Pending_Approval/`.
2. **Given** the invoice approval file is moved to `Approved/`, **When** the executor processes it, **Then** the invoice is confirmed in Odoo, a PDF is generated, and it is emailed to the client.
3. **Given** a business summary is requested, **When** the AI queries Odoo, **Then** a markdown summary report appears in `Plans/` within 2 minutes containing: total revenue this month, outstanding invoice count and value, and list of recent transactions.
4. **Given** any Odoo financial action is proposed, **When** the approval request is created, **Then** it is flagged with `requires_human_review` and never auto-approved regardless of threshold settings.
5. **Given** Odoo is unreachable, **When** an Odoo action is attempted, **Then** the system logs the failure and creates a `SYSTEM_odoo-unreachable.md` alert in `Needs_Action/` rather than silently failing.

---

### User Story 3 — Facebook & Instagram Publishing via Browser Automation (Priority: P3)

Taha wants to share a business win or thought leadership post across all social platforms at once. He drops a prompt into `Needs_Action/`. The AI drafts platform-specific posts for Facebook and Instagram, presents them for approval, and publishes them via browser automation — same pattern as WhatsApp already works in Silver. It also generates a weekly social engagement summary on request.

**Why this priority**: Multi-platform social presence is a direct hackathon Gold requirement. Browser automation (agent-browser) avoids Meta's API review process entirely, making this achievable without a Business account or app approval. It extends the LinkedIn-already-working Silver capability to the two remaining major platforms.

**Independent Test**: Drop a task file requesting a "client win" social post for Facebook and Instagram. Confirm: separate draft approval files created for each platform in `Pending_Approval/`. Approve each. Verify posts appear on the respective platforms within 60 seconds. Trigger a metrics summary; verify engagement data appears in `Plans/`.

**Acceptance Scenarios**:

1. **Given** a social post task exists with `platforms: [facebook, instagram]`, **When** the orchestrator processes it, **Then** separate approval request files are created for each platform in `Pending_Approval/`.
2. **Given** a Facebook approval file is moved to `Approved/`, **When** the executor processes it, **Then** the post is published to Taha's Facebook profile or page within 60 seconds using a persistent, locally stored browser session.
3. **Given** an Instagram approval file is moved to `Approved/`, **When** the executor processes it, **Then** the post with caption and hashtags is published to Taha's Instagram account within 60 seconds.
4. **Given** a social metrics summary is requested, **When** the AI uses browser automation to collect recent post engagement, **Then** a markdown summary appears in `Plans/` with likes, comments, and reach for the last 7 days across both platforms.
5. **Given** the browser session for Facebook or Instagram has expired or been invalidated, **When** an action is attempted, **Then** the system creates a `SYSTEM_social-session-expired.md` alert in `Needs_Action/` and does not attempt to retry until re-authenticated.
6. **Given** a post is rejected by the platform (e.g., rate limit, flagged content), **When** the browser action fails, **Then** the executor logs the error and moves the file to `Rejected/` with the failure reason.

---

### User Story 4 — Monday Morning CEO Briefing (Priority: P4)

Every Sunday night (or on demand), the AI autonomously audits the week's activity: emails handled, tasks completed, invoices sent, revenue logged, social posts published. It writes a structured CEO Briefing report to the vault that Taha reads Monday morning — no manual triggering required after initial setup.

**Why this priority**: The hackathon identifies this as the standout feature — the moment the AI transitions from reactive assistant to proactive business partner. It synthesises all domains into a single business intelligence report that provides immediate value every week.

**Independent Test**: Trigger the briefing manually via a task file. Verify a `CEO_Briefing_<date>.md` appears in `Plans/` within 3 minutes containing: emails handled this week, actions approved/rejected, invoices created and total value, social posts published, outstanding items requiring Taha's attention.

**Acceptance Scenarios**:

1. **Given** a briefing trigger fires (manual or scheduled), **When** the Ralph Loop processes it, **Then** a `CEO_Briefing_<YYYY-MM-DD>.md` report is written to `Plans/` within 3 minutes.
2. **Given** the briefing runs, **When** it reads the week's activity logs, **Then** the report includes: emails handled, WhatsApp replies sent, calendar events created, Odoo invoices sent and total value, social posts published, tasks still pending.
3. **Given** there are overdue approval requests (past 24h expiry) or system alerts, **When** the briefing generates, **Then** they appear in a dedicated "Action Required" section at the top of the report.
4. **Given** the briefing is scheduled (default: Sunday 11 PM PKT), **When** the system reaches the scheduled time, **Then** a briefing task file is automatically created in `Needs_Action/` without manual intervention.
5. **Given** a data source is unavailable (e.g., Odoo down) during briefing generation, **When** the report is written, **Then** it notes the missing data source and proceeds with available data rather than failing entirely.

---

### User Story 5 — Cross-Domain Integration: Payment-to-Outreach Chain (Priority: P5)

A client pays an invoice. The AI detects the payment status change in Odoo, sends a thank-you email, logs the client as active in the vault, and optionally drafts a LinkedIn post celebrating the win — all in a single Ralph Loop chain, with human approval at each outbound step.

**Why this priority**: Cross-domain integration (Personal + Business) is an explicit hackathon Gold requirement. It demonstrates that the AI orchestrates across communication, accounting, and social systems as a unified employee rather than isolated tools.

**Independent Test**: Manually mark an Odoo invoice as paid. Drop a trigger task file. Verify the chain: thank-you email drafted in `Pending_Approval/` → approved → sent → client status updated in vault → LinkedIn win post drafted in `Pending_Approval/`.

**Acceptance Scenarios**:

1. **Given** an Odoo invoice is marked as paid and a trigger task exists, **When** the Ralph Loop processes it, **Then** all downstream actions (thank-you email, client status update, optional social post) are chained in sequence with a separate approval file for each outbound action.
2. **Given** a user rejects one step in the chain (e.g., rejects the LinkedIn post), **When** the rejection is logged, **Then** the remaining steps in the chain continue normally and the task still completes.
3. **Given** a cross-domain task involves more than 3 downstream actions, **When** the orchestrator processes it, **Then** it splits into sequential sub-tasks each with their own loop iteration to keep complexity bounded.

---

### Edge Cases

- What happens when the Ralph Loop's Stop hook fires on a non-task file move (e.g., a temp file or log file)? The hook validates that the moved file matches the current loop's task context before stopping.
- What happens when Odoo contains a duplicate invoice (same client, same amount, same day)? The MCP server returns the existing draft ID and flags it for human review rather than creating a duplicate.
- What happens when Facebook or Instagram changes their UI, breaking browser automation selectors? The executor logs a `browser-automation-failed` error and creates a system alert with instructions to update selectors.
- What happens when the CEO Briefing runs but there are zero entries in the log for the week? The report generates with zeros for all metrics — it never fails silently.
- What happens if multiple Ralph Loops are started simultaneously for different tasks? Each loop runs as a separate process with its own task context and completion condition; they do not interfere.
- What happens when an Instagram post requires an image but none is provided in the task? The approval request is flagged `image_required` and moves to `Pending_Approval/` with instructions for the user to attach an image before re-approving.
- What happens when a social browser session is valid but the account is temporarily restricted by the platform? The executor detects the restriction via page content check, creates a system alert, and does not retry automatically.
- What happens if the scheduled CEO Briefing trigger fires while a previous briefing loop is still running? The new trigger is dropped (deduplicated) and a log entry is written noting the skip.

---

## Clarifications

### Session 2026-03-03

- Q: How should the Ralph Loop handle approval pauses without burning tokens idle-spinning? → A: Use **dual completion strategy**: promise-based (`<promise>AWAITING_APPROVAL</promise>`) whenever a step produces an approval file (loop exits cleanly, no idle spin); file-movement (`task → Done/`) for fully autonomous steps with no approval gates (CEO Briefing, Odoo queries). Executor drops a continuation task into `Needs_Action/` after dispatching each approved action, re-triggering a fresh loop for the next step. This reuses the existing Silver HITL pipeline for approval gates.
- Q: Should agent-browser run as a persistent daemon or launch on-demand per action? → A: **On-demand** — executor launches agent-browser per approved social action, loads saved session cookies from `~/.config/fte/`, posts, then closes. No persistent browser process. Facebook/Instagram are outbound-only (no need to listen), so a daemon adds complexity and resource cost with no benefit.
- Q: How should Odoo be installed locally? → A: **Docker (docker-compose)** — Odoo 19+ and PostgreSQL run in isolated containers, started with `docker-compose up -d`. Avoids conflicts with FTE Python environment, easy to reset/upgrade, and portable to a cloud VM at Platinum tier with the same compose file.
- Q: What mechanism triggers the scheduled CEO Briefing? → A: **Orchestrator-internal scheduler** — the orchestrator tracks last briefing time in a state file in the vault and drops the briefing task into `Needs_Action/` on the next poll cycle after the scheduled time. No new systemd unit or cron job needed. Catches up if the machine was offline at the scheduled time.
- Q: What is the maximum number of downstream actions in a single cross-domain chain? → A: **3 actions** for the initial Gold implementation — covers all primary real-world workflows (e.g. invoice → email → LinkedIn post). Intentionally conservative to keep failure recovery simple and testable. Uncapped mode deferred to a future iteration once the loop pattern is proven stable.

---

## Requirements *(mandatory)*

### Functional Requirements

**Ralph Wiggum Autonomous Loop**

- **FR-001**: The system MUST implement the Ralph Wiggum Stop hook pattern so that multi-step task chains execute to completion without manual re-triggering between steps.
- **FR-002**: The loop MUST use **dual completion strategy**: promise-based exit (`<promise>AWAITING_APPROVAL</promise>`) when a step produces an approval file; file-movement exit (task moves to `Done/`) for fully autonomous steps with no approval gates.
- **FR-003**: The loop MUST enforce a configurable max iteration limit (default: 10) and create a `SYSTEM_ralph-loop-timeout.md` alert in `Needs_Action/` if the limit is reached without task completion.
- **FR-004**: When a step requires HITL approval, the loop MUST exit via promise after writing the approval file. The executor MUST drop a continuation task into `Needs_Action/` after dispatching the approved action, re-triggering the loop for the next step.
- **FR-005**: All AI reasoning capabilities introduced in Gold tier MUST be packaged as independently invokable Agent Skills.

**Odoo Accounting Integration**

- **FR-006**: The system MUST integrate with a locally running Odoo Community 19+ instance via JSON-RPC — Claude uses the local `mcp-odoo-adv` MCP server for reasoning and queries; the executor calls Odoo JSON-RPC directly for mutations (create invoice, confirm invoice). No financial data leaves the local machine.
- **FR-007**: The system MUST support creating draft invoices in Odoo with: client name, line items (description, quantity, unit price), currency, and due date.
- **FR-008**: The system MUST support confirming and emailing Odoo invoices to clients after explicit human approval.
- **FR-009**: The system MUST support querying Odoo for business summary data: total revenue (month-to-date), outstanding invoices count and value, and recent transactions list.
- **FR-010**: All Odoo actions involving financial amounts MUST carry the `requires_human_review` flag in the approval request — no Odoo financial action may be auto-approved.
- **FR-011**: The Odoo MCP server MUST run as a local process; no financial data MAY be transmitted to external cloud services.

**Facebook & Instagram Integration**

- **FR-012**: The system MUST support publishing text posts to Facebook (personal profile or page) via browser automation using a persistent, locally stored session.
- **FR-013**: The system MUST support publishing posts with caption and hashtags to Instagram via browser automation using a persistent, locally stored session.
- **FR-014**: agent-browser MUST be launched on-demand per approved social action (not as a persistent daemon). Session cookies MUST be saved locally in `~/.config/fte/` and loaded at launch so no re-authentication is required across executor restarts, unless the platform invalidates the session.
- **FR-015**: The system MUST support generating a social engagement summary (likes, comments, reach) for the last 7 days by reading post metrics from the Facebook and Instagram web interfaces via browser automation.
- **FR-016**: All Facebook and Instagram posts MUST require human approval before publishing — no auto-approval thresholds apply.
- **FR-017**: Session invalidation MUST create a `SYSTEM_social-session-expired.md` alert in `Needs_Action/` and halt social posting actions until the session is restored.

**CEO Briefing**

- **FR-018**: The system MUST generate a `CEO_Briefing_<YYYY-MM-DD>.md` report in `Plans/` aggregating data from all active domains: email, WhatsApp, calendar, Odoo, LinkedIn, Facebook, and Instagram.
- **FR-019**: The briefing MUST be triggerable both manually (task file in `Needs_Action/`) and on a configurable schedule (default: Sunday 11 PM PKT). The schedule MUST be managed inside the orchestrator, which tracks the last briefing time in a vault state file and self-triggers on the next poll cycle after the scheduled time — no external cron or systemd timer required.
- **FR-020**: The briefing MUST include an "Action Required" section listing: overdue approval requests, unresolved system alerts, and tasks in `In_Progress/` for over 48 hours.

**Cross-Domain Integration**

- **FR-021**: The system MUST support chaining actions across at least two domains (e.g., email + Odoo, Odoo + social) within a single Ralph Loop execution.
- **FR-022**: Each cross-domain outbound action MUST have its own separate approval file — a single approval MUST NOT authorise multiple outbound actions simultaneously.

**Audit Logging**

- **FR-023**: Every Gold tier action (Odoo API call, browser automation step, Ralph Loop iteration) MUST be logged to `Vault/Logs/YYYY-MM-DD.json` using the existing log schema with appropriate `action_type` values.
- **FR-024**: `Dashboard.md` MUST be updated on every orchestrator cycle to include Gold tier metrics: Odoo actions today, social posts published today, Ralph Loop iterations run today.

### Key Entities

- **RalphLoopTask**: A task file in `Needs_Action/` tagged for multi-step autonomous execution. Contains: intended action chain, current step index, max iterations, completion condition.
- **OdooInvoice**: A draft or confirmed invoice in the local Odoo instance, referenced in vault task files by Odoo invoice ID and client contact details.
- **SocialPost**: An approval request for publishing to Facebook or Instagram. Contains: platform, post text, optional image path, hashtags, character count, session reference.
- **SocialSession**: A locally stored browser session file (cookies + auth state) for Facebook or Instagram. Persists between executor restarts.
- **CEOBriefing**: A generated markdown report in `Plans/` aggregating weekly activity across all domains. Referenced from `Dashboard.md`.
- **CrossDomainTask**: A task file in `Needs_Action/` spanning multiple integration domains, processed by the Ralph Loop as a unified chain with per-action approval gates.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A multi-step task (invoice request → Odoo invoice creation → email send) completes end-to-end within 10 minutes of the Ralph Loop being started, including one HITL approval pause, without manual re-triggering.
- **SC-002**: An Odoo invoice is created, confirmed, and emailed to a client within 2 minutes of the approval file being moved to `Approved/`.
- **SC-003**: Facebook and Instagram posts appear on the respective platforms within 60 seconds of the approval file being moved to `Approved/`.
- **SC-004**: The CEO Briefing report is generated within 3 minutes of the trigger (manual or scheduled) and covers all active integration domains.
- **SC-005**: Zero Odoo financial actions occur without a corresponding `Approved/` file carrying the `requires_human_review` flag.
- **SC-006**: Social browser sessions persist across at least 5 consecutive executor restarts without requiring re-authentication (assuming the platform has not invalidated the session).
- **SC-007**: All Gold tier actions are logged to `Vault/Logs/` and reflected in `Dashboard.md` within one orchestrator polling cycle (≤ 30 seconds).
- **SC-008**: All Gold tier AI capabilities are packaged as Agent Skills individually invokable without the full orchestrator pipeline.
- **SC-009**: The Ralph Loop terminates automatically (no manual kill required) in all three exit conditions: task moves to `Done/`, max iterations reached, or unrecoverable error logged.
- **SC-010**: No financial data (Odoo records, invoice PDFs) or browser session tokens are transmitted to any external service beyond the directly targeted platform.

---

## Assumptions

1. Silver tier is fully deployed and all Silver services are running stably before Gold tier development begins.
2. Odoo Community 19+ runs locally via Docker (docker-compose) and is accessible via localhost JSON-RPC before Odoo integration work starts.
3. The Ralph Wiggum loop is implemented in this tier from scratch as `scripts/ralph-loop.sh` (Stop hook) and `src/fte/ralph_loop.py` (state management). No pre-existing plugin is assumed — the reference plugin at `https://github.com/anthropics/claude-code/tree/main/.claude/plugins/ralph-wiggum` is used as a starting point only and requires adaptation for FTE's vault paths and dual-completion logic.
4. Facebook and Instagram automation uses agent-browser (Vercel Labs) for browser control — same pattern as whatsapp-web.js in Silver. The user accepts the ToS grey area for personal accounts posting 1–2 times per day.
5. Instagram is a personal account; if platform restrictions prevent browser automation posting, the user will convert to a Business/Creator account.
6. The Odoo MCP server is the open-source `mcp-odoo-adv` by AlanOgic or equivalent, configured to connect to the local Odoo instance via JSON-RPC.
7. The CEO Briefing scheduled trigger is managed inside the orchestrator process — it tracks last briefing time in `Vault/briefing_state.json` and self-triggers on the next poll cycle after the configured schedule. No external cron or systemd timer is needed.
8. All browser sessions (Facebook, Instagram) are stored locally in `~/.config/fte/` alongside existing OAuth tokens — never synced to any cloud service.
9. Architecture documentation (hackathon requirement #11) is satisfied by existing ADRs in `history/adr/` and a README update — no additional spec artifact required.
10. "Comprehensive audit logging" (hackathon requirement #9) is satisfied by extending the existing `Vault/Logs/YYYY-MM-DD.json` format with Gold tier action types rather than a new logging system.
11. Cross-domain chains are capped at 3 downstream actions in this implementation. The cap is stored as a configuration value so it can be raised or removed in a future iteration without code changes.
