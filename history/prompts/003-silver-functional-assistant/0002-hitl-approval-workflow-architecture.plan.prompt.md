---
id: "0002"
title: HITL Approval Workflow Architecture Research
stage: plan
date: 2026-02-27
surface: agent
model: claude-sonnet-4-6
feature: 003-silver-functional-assistant
branch: 002-systemd-daemon-setup
user: taha
command: research query (7 architecture questions)
labels: ["hitl","silver-tier","orchestrator","action-executor","mcp","expiry","vault-structure","race-conditions","dashboard"]
links:
  spec: specs/003-silver-functional-assistant/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - history/prompts/003-silver-functional-assistant/0002-hitl-approval-workflow-architecture.plan.prompt.md
tests:
  - none
---

## Prompt

Research the architecture for extending the FTE (Full-Time Employee) project's orchestrator to handle the HITL (Human-in-the-Loop) approval workflow for Silver tier.

Context:
- Bronze tier has: `fte-watcher` (watches Inbox/, moves to Needs_Action/) and `fte-orchestrator` (watches Needs_Action/, runs Claude Code, Claude writes Plans/)
- Silver tier adds: Claude writes approval requests to `Pending_Approval/`; user moves files to `Approved/` or `Rejected/`; the system must detect approved files and execute the corresponding action
- Actions: send Gmail reply, send WhatsApp reply, create Google Calendar event, publish LinkedIn post
- All watchers use `watchdog.observers.polling.PollingObserver` (already established for Windows NTFS mounts)
- The project is Python 3.13+ with uv, systemd on WSL2

Answer these specific questions:

1. **Approved folder watcher architecture**: Should the Approved/ folder be watched by:
   a. A new separate Python service (`fte-action-executor`)
   b. An extension of the existing `fte-orchestrator` Python process (watch both Needs_Action/ AND Approved/ in the same process)
   c. A Node.js process (to unify with whatsapp-web.js)
   Which is cleanest architecturally and why?

2. **Action dispatch pattern**: When a file lands in Approved/, how does the executor know which action to take? Options:
   a. Parse the YAML frontmatter `action_type` field from the approved file (e.g., `action_type: send_email`)
   b. File naming convention (e.g., `EMAIL_*.md` → send email, `LINKEDIN_*.md` → post)
   c. Both (frontmatter is authoritative, filename is for human readability)
   Recommend the best pattern.

3. **MCP invocation from executor**: When action_type is `send_email`, the executor needs to call the Gmail MCP. Options:
   a. Invoke Claude Code with the approved file as context (`claude --print "Send this email" --allowedTools mcp__gmail__*`)
   b. Call the MCP server directly via its JSON-RPC interface (bypassing Claude)
   c. A thin Python wrapper that calls the MCP via subprocess
   Which approach is most reliable for a daemon?

4. **Expiry enforcement**: The spec requires approval requests to expire after 24 hours and be auto-moved to Rejected/. Options:
   a. Check file mtime on every Approved/ poll and skip/move expired files
   b. A scheduled job (cron or apscheduler in Python) that scans Pending_Approval/ hourly
   c. Parse the expiry timestamp from the frontmatter on every poll
   Best approach for a PollingObserver-based system?

5. **Vault folder structure for Silver**: The `fte init` CLI command currently creates: `Inbox/`, `Needs_Action/`, `Plans/`, `Logs/`, `In_Progress/`, `Done/`. Silver needs to add: `Pending_Approval/`, `Approved/`, `Rejected/`. What's the cleanest way to extend the init command — add to the existing folder list in the Python source, or a migration/upgrade command?

6. **Race condition prevention**: If the user moves an Approved/ file at the same time the watcher polls, is there a risk of processing a partially-written file? How does the existing Bronze tier handle this (the 0.2s sleep in InboxHandler)? Should the same pattern apply?

7. **Dashboard.md generation**: The constitution requires a daily Dashboard.md in the vault. At what point in Silver tier should this be implemented? Should it be a scheduled task in the orchestrator or a separate skill?

Return architectural recommendations with rationale for each question.

## Response snapshot

Delivered 7 architectural recommendations grounded in codebase inspection of:
- src/fte/watcher.py (InboxHandler, PollingObserver, 0.2s sleep pattern)
- src/fte/orchestrator.py (subprocess Claude invocation, polling loop, in_flight guard)
- src/fte/vault.py (REQUIRED_DIRS — already includes Pending_Approval, Approved, Rejected)
- src/fte/cli.py (subcommand structure, entry points)
- src/fte/lockfile.py (PID-based single-instance guard)
- specs/003-silver-functional-assistant/spec.md (FR-005 through FR-010, SC-009)
- .specify/memory/constitution.md (Principle II HITL, Principle III layers, Principle VI logging)

Key decisions: separate fte-action-executor service; frontmatter-authoritative + filename-readable dispatch; Claude Code subprocess invocation; frontmatter expiry_at + background thread for expiry; existing REQUIRED_DIRS already covers Silver folders; 0.2s sleep pattern applies; Dashboard deferred to post-action Silver milestone.

## Outcome

- Impact: Architecture research complete — 7 decisions documented with rationale and tradeoffs, ready for /sp.plan to consume and produce the Silver implementation plan
- Tests: none — research/plan stage
- Files: history/prompts/003-silver-functional-assistant/0002-hitl-approval-workflow-architecture.plan.prompt.md
- Next prompts: /sp.plan for 003-silver-functional-assistant
- Reflection: vault.py already has Pending_Approval, Approved, Rejected in REQUIRED_DIRS — no migration needed. The key architectural insight is that fte-action-executor must be a separate process (not Node.js, not an extension of orchestrator) because MCP tool invocation via Claude subprocess has a very different timeout and failure profile from polling. Separation of concerns > process count efficiency at Silver scale.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): codebase cross-referenced — all recommendations grounded in real source
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): /sp.plan to convert this research into a concrete implementation plan with tasks
