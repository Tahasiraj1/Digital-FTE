# Implementation Plan: Silver Tier — Functional Assistant

**Branch**: `003-silver-functional-assistant` | **Date**: 2026-02-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-silver-functional-assistant/spec.md`

---

## Summary

Silver tier transforms the FTE from a file-processing demonstrator into a functional personal assistant. It adds Gmail and WhatsApp inbound watchers, a HITL approval workflow for all outbound actions (email reply, WhatsApp reply, Google Calendar event creation, LinkedIn post publishing), and packages all AI reasoning as Agent Skills. A new `fte-action-executor` service dispatches approved actions via local MCP servers and the LinkedIn REST API. No personal data leaves the local machine.

---

## Technical Context

**Language/Version**: Python 3.13+ (watchers, executor, LinkedIn action, MCP servers) | Node.js 20+ LTS (WhatsApp watcher via whatsapp-web.js)
**Primary Dependencies**:
- `google-api-python-client` + `google-auth-oauthlib` + `google-auth-httplib2` — Gmail polling + Gmail/Calendar MCP servers
- `mcp[cli]` — FastMCP framework for custom Gmail and Calendar MCP servers
- `whatsapp-web.js` + `qrcode-terminal` — WhatsApp monitoring (Node.js)
- `httpx` — LinkedIn REST API calls + WhatsApp IPC bridge calls
- `python-frontmatter` — approval request file parsing
- `watchdog` (PollingObserver) — Approved/ folder monitoring (existing)

**MCP Servers (custom, owned by this project)**:
- `src/mcp_servers/gmail/` — Python FastMCP server adapted from `D:\Code.Taha\email-app\mcp_server\`; tools: `list_emails`, `read_email`, `send_reply`; single-user local token at `~/.config/fte/gmail_token.json`
- `src/mcp_servers/calendar/` — Python FastMCP server (new, same pattern); tools: `create_event`, `list_events`; same Google OAuth2 token file as Gmail

**Storage**: Local vault files (markdown + YAML frontmatter) | OAuth2 token JSON files at `~/.config/fte/`
**Testing**: `pytest` (Python) | `npx @anthropic-ai/claude-code skills run` (skill testing)
**Target Platform**: WSL2 Ubuntu, systemd, `/mnt/d/` Windows NTFS vault
**Project Type**: Single Python project (existing) + Node.js module (new, whatsapp watcher)
**Performance Goals**: Email task file within 3 min | WhatsApp task file within 60s | Approved action executed within 30s
**Constraints**: All credentials local, chmod 600 | No cloud relay services | DEV_MODE gate on all real sends | Rate limits per constitution (max 10 emails/hour)
**Scale/Scope**: Single user, personal accounts — no multi-tenancy

---

## Constitution Check

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Local-First Privacy | ✅ PASS | MCP servers run locally via npx; tokens at ~/.config/fte/ chmod 600; no Composio/Rube relay |
| II. HITL Safety (NON-NEGOTIABLE) | ✅ PASS | FR-010 + SC-009: zero outbound actions without Approved/ file; executor --allowedTools constrains Claude |
| III. Perception-Reasoning-Action | ✅ PASS | Watchers observe only; orchestrator reasons; executor acts via MCP; no layer bypass |
| IV. Agent Skill Architecture | ✅ PASS | 7 SKILL.md files, all AI reasoning encapsulated; skills auto-discovered by Claude Code |
| V. Security by Default | ✅ PASS | Env vars for secrets; .env gitignored; DEV_MODE gate; 10 email/hour rate limit; --dry-run on executor |
| VI. Observability | ✅ PASS | All actions logged to Logs/YYYY-MM-DD.json; Dashboard.md updated daily by orchestrator |
| VII. Ralph Wiggum Pattern | ✅ PASS | Existing ralph-loop plugin used for multi-step task completion; max-iterations configured |
| VIII. Incremental Delivery | ✅ PASS | Bronze prerequisite in assumptions; Silver adds capabilities without breaking Bronze |

**Justified deviations**:
1. **WhatsApp — Playwright → whatsapp-web.js**: Constitution names "Playwright" for web automation; Silver uses `whatsapp-web.js` (Puppeteer-based). Justified: WhatsApp-specific abstraction with built-in session management, event-driven messaging, and QR terminal rendering — see research.md Decision 7.
2. **LinkedIn — MCP Server → Direct REST API**: Constitution Principle III states "Each MCP server owns a single domain of action." LinkedIn posting uses `httpx` direct REST API (`POST /v2/ugcPosts`) instead of an MCP server. Justified: LinkedIn has no session-persistence requirement (unlike WhatsApp); OAuth token is stateless JSON; wrapping a single REST endpoint in a FastMCP server adds protocol overhead with zero architectural benefit; ADR-0004 documents this explicitly.
3. **WhatsApp Watcher — observe-only → observe + IPC send**: Constitution Principle III states "Watchers MUST NOT reason or act." The WhatsApp `watcher.js` also serves as the send endpoint (HTTP IPC on `localhost:8766`). Justified: `whatsapp-web.js` requires the same Node.js process that holds the session to send messages — a separate sender process cannot access the session; IPC endpoint is localhost-only and guarded by the executor's HITL gate before it is ever called.

---

## Project Structure

### Documentation (this feature)

```
specs/003-silver-functional-assistant/
├── plan.md               ← this file
├── research.md           ← Phase 0 output
├── data-model.md         ← Phase 1 output
├── quickstart.md         ← Phase 1 output
├── contracts/
│   └── action-executor-interface.md
└── tasks.md              ← /sp.tasks output (next command)
```

### Source Code Structure

```
src/fte/
├── watcher.py              # Bronze — unchanged
├── orchestrator.py         # Bronze + Silver: extend for Dashboard.md, skill invocation
├── vault.py                # Bronze — Pending_Approval/Approved/Rejected already in REQUIRED_DIRS
├── cli.py                  # Bronze + Silver: add 'execute' subcommand
├── executor.py             # NEW: fte-action-executor service
├── gmail_watcher.py        # NEW: Gmail polling watcher
├── linkedin_auth.py        # NEW: one-time LinkedIn OAuth2 CLI script
└── actions/
    ├── __init__.py
    ├── gmail.py            # NEW: send email via Gmail MCP subprocess
    ├── calendar.py         # NEW: create event via Calendar MCP subprocess
    ├── whatsapp.py         # NEW: send WhatsApp reply via HTTP IPC (localhost:8766)
    └── linkedin.py         # NEW: publish post via LinkedIn REST API directly

src/fte/whatsapp/           # NEW: Node.js module (separate from Python package)
├── package.json
├── watcher.js              # whatsapp-web.js daemon + HTTP IPC server on localhost:8766
└── watcher-state.json      # WatcherState (runtime, not committed)

src/mcp_servers/            # NEW: Custom Python FastMCP servers (owned by this project)
├── __init__.py
├── gmail/                  # Adapted from D:\Code.Taha\email-app\mcp_server\
│   ├── __init__.py
│   ├── config.py           # Token path + Google credentials from env
│   ├── main.py             # FastMCP entrypoint
│   ├── server.py           # Tool registration (list_emails, read_email, send_reply)
│   ├── services/
│   │   └── gmail_service.py  # get_gmail_service() — reads local token file
│   └── tools/
│       ├── list_emails.py
│       ├── read_email.py
│       └── send_reply.py
└── calendar/               # New Python FastMCP server (same pattern as Gmail)
    ├── __init__.py
    ├── config.py
    ├── main.py
    ├── server.py           # Tool registration (create_event, list_events)
    ├── services/
    │   └── calendar_service.py
    └── tools/
        ├── create_event.py
        └── list_events.py

.claude/skills/
├── gmail-watcher/
│   └── SKILL.md
├── whatsapp-watcher/
│   └── SKILL.md
├── gmail-reply/
│   └── SKILL.md
├── whatsapp-reply/
│   └── SKILL.md
├── calendar-event/
│   └── SKILL.md
├── linkedin-post/
│   └── SKILL.md
└── hitl-approval/
    └── SKILL.md

deploy/
├── install.sh              # Bronze — unchanged
├── uninstall.sh            # Bronze — unchanged
├── install-silver.sh       # NEW: adds 3 Silver systemd services
└── uninstall-silver.sh     # NEW: removes Silver services

tests/
├── unit/
│   ├── test_gmail_watcher.py   # NEW
│   ├── test_executor.py        # NEW
│   ├── test_actions_gmail.py   # NEW
│   ├── test_actions_linkedin.py # NEW
│   └── test_skills.py          # NEW
└── integration/
    └── test_silver_pipeline.py  # NEW: full pipeline smoke test with DEV_MODE
```

---

## Service Topology

```
systemd (5 services after Silver deploy)
├── fte-watcher          [Bronze] Inbox/ → Needs_Action/
├── fte-orchestrator     [Bronze+] Needs_Action/ → Plans/ + Pending_Approval/
│                                  + daily Dashboard.md update
├── fte-gmail-watcher    [Silver] Gmail inbox → Inbox/  (Python, 2-min poll)
├── fte-whatsapp-watcher [Silver] WhatsApp messages → Inbox/ (Node.js, event-driven)
└── fte-action-executor  [Silver] Approved/ → action dispatch → Done/
```

**MCP servers** (custom Python FastMCP, loaded by `claude -p` subprocess on demand):
- `gmail` → `python -m mcp_servers.gmail.main` (loaded by orchestrator + executor); tools: `mcp__gmail__list_emails`, `mcp__gmail__read_email`, `mcp__gmail__send_reply`
- `calendar` → `python -m mcp_servers.calendar.main` (loaded by executor); tools: `mcp__calendar__create_event`, `mcp__calendar__list_events`

**Agent Skills** (auto-discovered from `.claude/skills/`):
- `gmail-watcher`, `whatsapp-watcher` — context extraction skills (invoked by orchestrator)
- `gmail-reply`, `whatsapp-reply`, `calendar-event`, `linkedin-post` — action drafting skills
- `hitl-approval` — approval request formatting and validation

---

## Implementation Phases

### Phase 1: Vault + Skill Foundation (no external calls)

- Verify `Pending_Approval/`, `Approved/`, `Rejected/` are created by `fte init` (already in REQUIRED_DIRS — confirm only)
- Create all 7 `SKILL.md` files under `.claude/skills/`
- Add `execute` CLI subcommand scaffolding to `cli.py`
- Create `executor.py` with `PollingObserver` on `Approved/`, expiry thread, and dry-run mode
- Unit tests for executor (file parsing, expiry logic, dry-run)

### Phase 2: Gmail Watcher + Custom Gmail MCP Server (inbound + MCP foundation)

- Adapt `src/mcp_servers/gmail/` from `D:\Code.Taha\email-app\mcp_server\` — strip `@require_oauth` decorator and `TokenManager`, replace with `get_gmail_service()` reading `~/.config/fte/gmail_token.json` directly; retain all Gmail API call logic in `list_emails.py`, `read_email.py`, `send_reply.py`
- Create `src/mcp_servers/calendar/` — new Python FastMCP server (same pattern); `create_event.py`, `list_events.py` using `google-api-python-client` Calendar v3
- Create `scripts/oauth_setup.py` — one-time browser OAuth2 flow for Gmail + Calendar scopes; saves token to `~/.config/fte/gmail_token.json` with `chmod 600`
- Register both MCP servers in `~/.claude/settings.json` with `python -m mcp_servers.gmail.main` / `python -m mcp_servers.calendar.main`
- Implement `gmail_watcher.py` — Gmail API polling, deduplication, `EMAIL_*.md` task file writer
- WatcherState at `~/.config/fte/gmail_watcher_state.json` (atomic writes)
- Add `fte-gmail-watcher` to `deploy/install-silver.sh`
- Verify: send test email → task file appears in Inbox/ within 3 min

### Phase 3: Gmail Action (outbound via Gmail MCP)

- Implement `actions/gmail.py` — calls `claude -p` with `--allowedTools mcp__gmail__send_reply --dangerously-skip-permissions`
- Integration test: approved EMAIL_REPLY file → executor → gmail sent (DEV_MODE=true dry-run)
- Activate `gmail-reply` skill invocation from orchestrator

### Phase 4: WhatsApp Watcher (inbound only)

- Implement `src/fte/whatsapp/watcher.js` using `whatsapp-web.js` + `LocalAuth`
- WatcherState at `/var/lib/fte/whatsapp-session/watcher-state.json`
- Keyword filtering with pre-compiled RegExp
- `WHATSAPP_*.md` task file writer
- Disconnection handling (UNPAIRED → alert file; CONFLICT → reinitialize)
- In-process heartbeat + systemd `MemoryMax=512M`, `RuntimeMaxSec=86400`
- Add `fte-whatsapp-watcher` to `deploy/install-silver.sh`
- First-time QR setup: run interactively, scan, session persisted
- Verify: trigger keyword message → task file in Inbox/ within 60s

### Phase 5: WhatsApp Action (outbound)

- Implement `actions/whatsapp.py` — IPC or CLI bridge to `client.sendMessage()` in the Node.js watcher
- Implement `whatsapp-reply` skill
- Integration test: approved WHATSAPP_REPLY file → executor → message sent in conversation (DEV_MODE)

### Phase 6: Google Calendar Action

- Implement `actions/calendar.py` — calls `claude -p` with `--allowedTools mcp__calendar__create_event`
- Calendar MCP config in `~/.claude/settings.json`
- Implement `calendar-event` skill
- Integration test: approved CALENDAR file → executor → event in Google Calendar (DEV_MODE)

### Phase 7: LinkedIn Action + Auth

- Implement `linkedin_auth.py` one-time OAuth2 flow (localhost:8765 callback server)
- Implement `actions/linkedin.py` — `POST /v2/ugcPosts`, proactive token refresh (7-day buffer), rate limit handling, vault alerts on 429/401
- Client-side rate limiting: max 10 posts/day (log-counted)
- Implement `linkedin-post` skill
- Integration test: approved LINKEDIN file → executor → post visible on profile (DEV_MODE)

### Phase 8: Dashboard.md + Polish

- Add daily `Dashboard.md` update to orchestrator (Python log aggregation, no Claude invocation)
- Implement `hitl-approval` skill for approval request formatting validation
- `deploy/uninstall-silver.sh`
- Full end-to-end integration test with all 5 services running (DEV_MODE=true)
- Constitution compliance final review

---

## Complexity Tracking

| Item | Why Needed | Simpler Alternative Rejected Because |
|------|-----------|-------------------------------------|
| Node.js WhatsApp watcher alongside Python | `whatsapp-web.js` is Node.js native; no equivalent Python library with the same reliability | Raw Playwright (Python) requires fragile DOM polling against `window.Store` internal; `whatsapp-web.js` provides event-driven messaging out of the box |
| 3 new systemd services | Each pipeline stage (inbound Gmail, inbound WhatsApp, outbound action) has independent timeout and restart requirements | Merging into orchestrator would cause 120s Claude timeout to block 30s action SLA; single-process mixing violates Constitution Principle III |
| Custom Python FastMCP servers for Gmail + Calendar | Local MCP keeps data off cloud relay (Principle I); hackathon requires custom-written MCP servers; Gmail MCP adapted from user's existing email-app (low cost) | Cloud-based Composio/Rube rejected: data locality violation; npm packages rejected: supply chain risk + hackathon requirement |
