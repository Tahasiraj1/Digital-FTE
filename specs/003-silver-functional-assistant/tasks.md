# Tasks: Silver Tier — Functional Assistant

**Feature**: `003-silver-functional-assistant`
**Branch**: `003-silver-functional-assistant`
**Generated**: 2026-02-28
**Input**: spec.md, plan.md, data-model.md, contracts/action-executor-interface.md, research.md, quickstart.md + chat session context

**Chat context applied**:
- Gmail MCP: Adapted from user's existing email-app (`D:\Code.Taha\email-app`) — Python FastMCP, strip multi-user OAuth, replace with local token file reader
- Calendar MCP: Custom Python FastMCP server (same pattern as Gmail MCP)
- WhatsApp: `whatsapp-web.js` + `LocalAuth` (Node.js daemon)
- LinkedIn: Direct REST API (`POST /v2/ugcPosts`) — no MCP needed
- 7 Agent Skills required by hackathon (all AI functionality must be in SKILL.md files)
- `skill-creator` skill available for authoring SKILL.md files
- MCP servers must be custom-written (hackathon requirement), not consumed third-party packages

**Tests**: Not requested — no test tasks generated (use quickstart.md for manual verification)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: User story this task belongs to ([US1]–[US5])

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install dependencies, create directory scaffolding, and confirm vault readiness before any feature work begins.

- [X] T001 Confirm `Pending_Approval/`, `Approved/`, `Rejected/`, `Done/` are present in `vault.py`'s `REQUIRED_DIRS` list in `src/fte/vault.py` — add any missing entries
- [X] T002 Add Silver Python dependencies to `pyproject.toml`: `google-api-python-client`, `google-auth-oauthlib`, `google-auth-httplib2`, `python-frontmatter`, `httpx`, `mcp[cli]`
- [X] T003 [P] Create Python package directories: `src/fte/actions/__init__.py`, `src/mcp_servers/__init__.py`, `src/mcp_servers/gmail/__init__.py`, `src/mcp_servers/gmail/services/__init__.py`, `src/mcp_servers/gmail/tools/__init__.py`, `src/mcp_servers/calendar/__init__.py`, `src/mcp_servers/calendar/services/__init__.py`, `src/mcp_servers/calendar/tools/__init__.py`
- [X] T004 [P] Initialise Node.js WhatsApp module — create `src/fte/whatsapp/package.json` with `name: fte-whatsapp-watcher`, `type: module`, dependencies: `whatsapp-web.js@^1.26`, `qrcode-terminal`, `fs-extra`; run `npm install` in `src/fte/whatsapp/`
- [X] T005 [P] Create `deploy/install-silver.sh` scaffold: stub for installing 3 new systemd services (`fte-gmail-watcher`, `fte-whatsapp-watcher`, `fte-action-executor`), copying service files from `deploy/`, running `systemctl daemon-reload`
- [X] T006 [P] Create systemd service unit files: `deploy/fte-gmail-watcher.service`, `deploy/fte-whatsapp-watcher.service`, `deploy/fte-action-executor.service` — follow the same pattern as existing Bronze service files in `deploy/`
- [X] T006a Create `Vault/Company_Handbook.md` — required by Constitution Principle II; Silver-tier content: (1) all outbound actions require manual approval (no auto-approve), (2) rate limits: max 10 emails/hour, max 10 LinkedIn posts/day, (3) email replies to unknown senders must be flagged with `"unknown_sender"` in approval file `flags` field, (4) LinkedIn posts may not contain pricing or financial commitments without explicit review flag

**Checkpoint**: All dependencies installed, directories exist, service stubs created, Company_Handbook.md created. No feature code yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that ALL user stories depend on — executor engine, Gmail MCP server, Calendar MCP server, OAuth setup. Must be complete before any user story work begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Executor Engine (blocks US1–US4)

- [X] T007 Implement `src/fte/executor.py` — `PollingObserver` (PollingObserver, not Observer) watching `Vault/Approved/`, `DEV_MODE` environment gate (if `DEV_MODE=true`, log action but skip actual dispatch), dispatch table stub mapping `action_type` values to handler functions in `src/fte/actions/`
- [X] T008 Add expiry enforcement background thread to `src/fte/executor.py` — runs every 300s, scans all files in `Vault/Pending_Approval/`, parses `expiry_at` frontmatter field, moves expired files to `Vault/Rejected/` with `status: expired`, writes log entry
- [X] T009 Add pre-execution checks to `src/fte/executor.py` per `contracts/action-executor-interface.md`: parse `expiry_at` before dispatch, apply 0.2s stability sleep, set `status: executing` in frontmatter in-place before dispatching, move file to `Done/` on success or `Rejected/` on failure/timeout
- [X] T009a Add `PollingObserver` on `Vault/Rejected/` in `src/fte/executor.py` — on any new `.md` file detected (user-driven rejection or system rejection), read `action_type` and `status` from frontmatter, write a structured log entry to `Vault/Logs/YYYY-MM-DD.json` with `approval_status: "rejected"`, `actor: "user"` (if status was `pending`) or `actor: "fte-action-executor"` (if status is `expired` or `failed`); take no further action (FR-008)
- [X] T010 Add `execute` subcommand to `src/fte/cli.py` — `fte execute` starts the `fte-action-executor` service loop; `fte execute --dry-run` forces `DEV_MODE=true` for that session
- [X] T011 Extend log entry format in `src/fte/executor.py` to include Silver fields: `source_task`, `approved_file`, `approval_status`, `approved_at`, `actor: "fte-action-executor"` — must append to existing `Vault/Logs/YYYY-MM-DD.json` format without breaking Bronze log readers

### Gmail MCP Server (blocks US1, US3)

- [X] T012 Create `src/mcp_servers/gmail/config.py` — reads `GMAIL_TOKEN_PATH` env var (default: `~/.config/fte/gmail_token.json`), `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` from environment; no hardcoded secrets
- [X] T013 Create `src/mcp_servers/gmail/services/gmail_service.py` — `get_gmail_service()` reads OAuth2 token from `~/.config/fte/gmail_token.json`, builds `google-api-python-client` Gmail v1 service; adapted from `D:\Code.Taha\email-app\mcp_server\services\gmail_service.py` — replace `TokenManager`/`OAuthToken` imports with direct `json.loads(Path(token_path).read_text())`, build `google.oauth2.credentials.Credentials` from the JSON fields
- [X] T014 Copy and adapt `list_emails` tool to `src/mcp_servers/gmail/tools/list_emails.py` — source: `D:\Code.Taha\email-app\mcp_server\tools\list_emails.py`; remove `_oauth_token` and `_user_identity` parameters, remove `@require_oauth` import and usage, call `get_gmail_service()` directly with no args; keep all Gmail API call logic and error handling intact
- [X] T015 [P] Copy and adapt `read_email` tool to `src/mcp_servers/gmail/tools/read_email.py` — source: `D:\Code.Taha\email-app\mcp_server\tools\read_email.py`; same stripping as T014
- [X] T016 [P] Copy and adapt `send_reply` tool to `src/mcp_servers/gmail/tools/send_reply.py` — source: `D:\Code.Taha\email-app\mcp_server\tools\send_reply.py`; same stripping as T014; keep `confirm: bool` safety gate as-is (executor always passes `confirm=True` after HITL approval)
- [X] T017 Create `src/mcp_servers/gmail/server.py` — `FastMCP` server (from `mcp.server.fastmcp`) registering `list_emails`, `read_email`, `send_reply` tools; no OAuth middleware; expose as `__main__` entrypoint via `mcp.run()`
- [X] T018 Create `src/mcp_servers/gmail/main.py` — `if __name__ == "__main__": mcp.run()` entrypoint; add `[project.scripts]` entry in `pyproject.toml`: `fte-gmail-mcp = "mcp_servers.gmail.main:main"`

### Calendar MCP Server (blocks US3)

- [X] T019 Create `src/mcp_servers/calendar/config.py` — reads `CALENDAR_TOKEN_PATH` (default: `~/.config/fte/gmail_token.json`, same Google project), `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` from environment
- [X] T020 Create `src/mcp_servers/calendar/services/calendar_service.py` — `get_calendar_service()` reads OAuth2 token from `~/.config/fte/gmail_token.json` (same token file as Gmail — both use same Google Cloud project and scopes), builds Google Calendar v3 API service using `google-api-python-client`
- [X] T021 Create `src/mcp_servers/calendar/tools/create_event.py` — `create_event(title, date, start_time, end_time, timezone, attendees, description)` → calls Google Calendar API `events().insert()`, returns `event_id`, `html_link`; validate ISO date format; handle 429/403 errors
- [X] T022 [P] Create `src/mcp_servers/calendar/tools/list_events.py` — `list_events(date_from, date_to, max_results=10)` → calls `events().list()`, returns structured list; useful for orchestrator to check conflicts before creating
- [X] T023 Create `src/mcp_servers/calendar/server.py` — `FastMCP` server registering `create_event` and `list_events` tools; `mcp.run()` entrypoint in `main.py`

### OAuth2 Setup (blocks US1, US3, US4)

- [X] T024 Create `scripts/oauth_setup.py` — one-time interactive OAuth2 flow for Gmail + Calendar scopes (`gmail.readonly`, `gmail.send`, `calendar`) using `google-auth-oauthlib`; launches browser to Google consent page; saves token JSON to `~/.config/fte/gmail_token.json` with `chmod 600`; idempotent (skips if token already exists and is valid)

### MCP Settings (blocks US1, US3)

- [X] T025 Update `specs/003-silver-functional-assistant/quickstart.md` — add Step 2a: "Register Gmail MCP server in `~/.claude/settings.json`" with exact JSON snippet pointing to `python -m mcp_servers.gmail.main`; add Step 2b: Calendar MCP server entry; document MCP tool names (`mcp__gmail__list_emails`, `mcp__gmail__send_reply`, `mcp__calendar__create_event`)

**Checkpoint**: Executor engine, both MCP servers, and OAuth setup are ready. All user stories can now proceed.

---

## Phase 3: User Story 1 — Inbound Email Processing & Reply (Priority: P1) 🎯 MVP

**Goal**: Gmail inbox → `EMAIL_*.md` task file in `Inbox/` → orchestrator drafts reply → `Pending_Approval/` → user approves → email sent.

**Independent Test**: Send a test email → verify `EMAIL_*.md` in `Inbox/` within 3 min → trigger orchestrator → confirm `Pending_Approval/` file → move to `Approved/` → verify email sent (DEV_MODE=true logs only).

### Implementation for User Story 1

- [X] T026 [US1] Implement `src/fte/gmail_watcher.py` — `GmailWatcher` class: polls Gmail API every 120s using `get_gmail_service()`, applies filter (unread + `IMPORTANT` label OR starred OR from known contact), deduplicates via `WatcherState` loaded from `~/.config/fte/gmail_watcher_state.json`, writes `EMAIL_<message-id>.md` to `Vault/Inbox/` using the exact YAML frontmatter schema from `data-model.md`
- [X] T027 [US1] Implement `WatcherState` persistence in `src/fte/gmail_watcher.py` — FIFO `processed_ids` list capped at 10,000 entries, atomic write via temp file + `os.replace()`, schema version field; state file at `~/.config/fte/gmail_watcher_state.json`
- [X] T028 [US1] Add crash recovery and auto-restart logic to `src/fte/gmail_watcher.py` — catch all exceptions in the polling loop, log to `Vault/Logs/`, sleep 15s, retry; the systemd `Restart=always` + `RestartSec=5` handles process-level restart
- [X] T029 [US1] Complete `deploy/fte-gmail-watcher.service` — `ExecStart=fte gmail-watcher`, `Restart=always`, `RestartSec=5`, `MemoryMax=256M`, `Environment=DEV_MODE=false`; add `gmail-watcher` subcommand to `src/fte/cli.py`
- [X] T030 [US1] Implement `src/fte/actions/gmail.py` — `send_email_reply(approved_file_path)`: reads approved file frontmatter (action_type, to, thread_id, subject, proposed_reply), invokes `claude -p` subprocess with `--allowedTools mcp__gmail__send_reply --dangerously-skip-permissions`, 30s timeout; on success moves file to `Done/`, on failure moves to `Rejected/` with `status: failed`
- [X] T031 [US1] Register `send_email` handler in `src/fte/executor.py` dispatch table — `"send_email": actions.gmail.send_email_reply`
- [X] T032 [US1] Extend `src/fte/orchestrator.py` to invoke `gmail-reply` skill when processing `email` type task files in `Needs_Action/` — load skill context, invoke `claude -p` with skill instructions, output must be an `ApprovalRequest` file written to `Pending_Approval/` using the exact YAML schema from `data-model.md` (action_type: send_email, expiry_at = created_at + 24h)

**Checkpoint**: Full US1 pipeline functional. Send test email → task file → approval draft → (DEV_MODE) logged send.

---

## Phase 4: User Story 2 — WhatsApp Message Detection & Reply (Priority: P2)

**Goal**: Keyword WhatsApp message → `WHATSAPP_*.md` task file in `Inbox/` → orchestrator drafts reply → `Pending_Approval/` → user approves → WhatsApp reply sent.

**Independent Test**: Send WhatsApp message with keyword "invoice" → verify `WHATSAPP_*.md` in `Inbox/` within 60s → approve draft → verify reply logged (DEV_MODE).

### Implementation for User Story 2

- [X] T033 [US2] Implement `src/fte/whatsapp/watcher.js` — initialise `whatsapp-web.js` `Client` with `LocalAuth({ dataPath: '/var/lib/fte/whatsapp-session' })` and `puppeteer: { headless: true, args: ['--no-sandbox'] }`; print QR to terminal via `qrcode-terminal` on first run; handle `client.on('qr')`, `client.on('ready')`, `client.on('message')`
- [X] T034 [US2] Add keyword filter to `src/fte/whatsapp/watcher.js` — configurable keyword list via `WHATSAPP_KEYWORDS` env var (default: `urgent,asap,invoice,payment,help,contract`); pre-compile single RegExp from keywords; only process messages matching the pattern; ignore group messages unless `WHATSAPP_ALLOW_GROUPS=true`
- [X] T035 [US2] Implement `WHATSAPP_*.md` task file writer in `src/fte/whatsapp/watcher.js` — on keyword match, write file to `Vault/Inbox/WHATSAPP_<sanitized-id>.md` with exact YAML frontmatter from `data-model.md`; sanitize message ID for filename (replace non-alphanumeric with `_`); dedup via `watcher-state.json` at `/var/lib/fte/whatsapp-session/watcher-state.json`
- [X] T036 [US2] Implement `WatcherState` in `src/fte/whatsapp/watcher.js` — FIFO `processed_ids` array capped at 2,000 entries, atomic write via `fs-extra.outputJson` to temp path then rename; load on startup
- [X] T037 [US2] Add disconnection handling to `src/fte/whatsapp/watcher.js` — `client.on('disconnected', reason)`: if reason is `UNPAIRED` write `SYSTEM_whatsapp-session-expired.md` to `Vault/Needs_Action/`; if `CONFLICT` call `client.initialize()` to reinitialise; log all events to stdout (captured by systemd journal)
- [X] T038 [US2] Complete `deploy/fte-whatsapp-watcher.service` — `ExecStart=node /path/to/src/fte/whatsapp/watcher.js`, `Restart=always`, `RestartSec=10`, `MemoryMax=512M`, `RuntimeMaxSec=86400` (daily restart for session health); add `VAULT_PATH` env var
- [X] T039 [US2] Implement WhatsApp IPC bridge in `src/fte/whatsapp/watcher.js` — add minimal HTTP server (Node.js built-in `http`) on port 8766 (localhost only); `POST /send` with JSON body `{to_jid, message}` → calls `client.sendMessage(to_jid, message)` → returns `{status: "sent"}` or `{error: "..."}` — this is the IPC endpoint for the Python action
- [X] T040 [US2] Implement `src/fte/actions/whatsapp.py` — `send_whatsapp_reply(approved_file_path)`: reads approved file frontmatter (action_type, to_jid, to_display, proposed_reply), sends `POST http://localhost:8766/send` via `httpx`, 30s timeout; on success moves file to `Done/`, on failure to `Rejected/`
- [X] T041 [US2] Register `send_whatsapp` handler in `src/fte/executor.py` dispatch table — `"send_whatsapp": actions.whatsapp.send_whatsapp_reply`
- [X] T042 [US2] Extend `src/fte/orchestrator.py` to invoke `whatsapp-reply` skill when processing `whatsapp_message` type task files — output must be `WHATSAPP_REPLY_*.md` approval request file in `Pending_Approval/` using YAML schema from `data-model.md`

**Checkpoint**: Full US2 pipeline functional. Keyword WhatsApp message → task file → approval draft → (DEV_MODE) logged send.

---

## Phase 5: User Story 3 — Google Calendar Event Creation (Priority: P3)

**Goal**: Task with scheduling intent → calendar event approval request in `Pending_Approval/` → user approves → event created in Google Calendar.

**Independent Test**: Drop a task file referencing "Can we meet Tuesday at 3pm?" into `Inbox/` → confirm `CALENDAR_*.md` in `Pending_Approval/` → approve → verify event created (or logged in DEV_MODE).

### Implementation for User Story 3

- [X] T043 [US3] Implement `src/fte/actions/calendar.py` — `create_calendar_event(approved_file_path)`: reads approved file frontmatter (action_type, event_title, event_date, event_time_start, event_time_end, event_timezone, attendees, event_description), invokes `claude -p` subprocess with `--allowedTools mcp__calendar__create_event --dangerously-skip-permissions`, 30s timeout; on success moves file to `Done/`, on failure to `Rejected/`
- [X] T044 [US3] Register `create_calendar_event` handler in `src/fte/executor.py` dispatch table — `"create_calendar_event": actions.calendar.create_calendar_event`
- [X] T045 [US3] Extend `src/fte/orchestrator.py` to invoke `calendar-event` skill when processing task files containing scheduling intent (date + time + participants keywords) — output must be `CALENDAR_<slug>_<timestamp>.md` approval request file in `Pending_Approval/` using YAML schema from `data-model.md` (including `event_date`, `event_time_start`, `event_time_end`, `event_timezone`, `attendees` list)
- [X] T046 [US3] Add scheduling intent detection logic to `src/fte/orchestrator.py` — heuristic check: if task contains date/time keywords ("meet", "call", "schedule", "tuesday", "pm", ISO date patterns) AND has at least one email address or contact name, route to `calendar-event` skill; otherwise route to standard reply skill

**Checkpoint**: Full US3 pipeline functional. Scheduling task → calendar event approval → (DEV_MODE) event creation logged.

---

## Phase 6: User Story 4 — LinkedIn Business Post Publishing (Priority: P4)

**Goal**: LinkedIn post task → AI drafts post → `Pending_Approval/` → user approves → post published to LinkedIn profile.

**Independent Test**: Drop prompt file "Write a LinkedIn post about our AI automation services" into `Inbox/` → confirm `LINKEDIN_*.md` in `Pending_Approval/` → approve → verify post published (DEV_MODE logs only).

### Implementation for User Story 4

- [X] T047 [US4] Implement `src/fte/linkedin_auth.py` — one-time OAuth2 authorisation code flow: open browser to `https://www.linkedin.com/oauth/v2/authorization` with `scope=r_liteprofile w_member_social openid profile email`, run `http.server` on `localhost:8765` to capture redirect, exchange code for tokens via `POST /oauth/v2/accessToken`, save to `~/.config/fte/linkedin_token.json` with `chmod 600`; `fte linkedin-auth` CLI subcommand
- [X] T048 [US4] Implement `src/fte/actions/linkedin.py` — `publish_linkedin_post(approved_file_path)`: reads approved file frontmatter (proposed_post, character_count); loads token from `~/.config/fte/linkedin_token.json`; proactively refreshes token if `expires_at < now + 7 days`; sends `POST https://api.linkedin.com/v2/ugcPosts` with correct UGC post schema; client-side rate limit (max 10 posts/day, counted from today's `Vault/Logs/` entries); on success moves file to `Done/`, on failure to `Rejected/`
- [X] T049 [US4] Implement proactive token refresh in `src/fte/actions/linkedin.py` — if access token expires within 7 days, call `POST /oauth/v2/accessToken` with `grant_type=refresh_token`; always overwrite both `access_token` and `refresh_token` in the token file (LinkedIn rotates refresh tokens); if refresh fails write `SYSTEM_linkedin-token-expired.md` alert to `Vault/Needs_Action/`
- [X] T050 [US4] Implement LinkedIn rate limit enforcement in `src/fte/actions/linkedin.py` — count today's `publish_linkedin_post` entries in `Vault/Logs/YYYY-MM-DD.json`; if count >= 10, write alert file to `Vault/Needs_Action/` and move approved file to `Rejected/` without API call
- [X] T051 [US4] Register `publish_linkedin_post` handler in `src/fte/executor.py` dispatch table — `"publish_linkedin_post": actions.linkedin.publish_linkedin_post`
- [X] T052 [US4] Extend `src/fte/orchestrator.py` to invoke `linkedin-post` skill when processing `linkedin` type task files — output must be `LINKEDIN_<slug>_<timestamp>.md` approval request in `Pending_Approval/` with `proposed_post` (max 3,000 chars), `character_count`, `hashtags` fields per `data-model.md`; if draft exceeds 3,000 chars, flag with `"requires_human_review"` in `flags` field

**Checkpoint**: Full US4 pipeline functional. LinkedIn post task → draft → approval → (DEV_MODE) post logged.

---

## Phase 7: User Story 5 — Agent Skills for All AI Capabilities (Priority: P5)

**Goal**: All 7 AI capabilities packaged as Agent Skills, independently invokable, auto-discovered by Claude Code.

**Independent Test**: Invoke each skill individually via Claude Code interface (`/skill-name`) and verify it produces the correct output artifact for a sample input without additional prompt engineering.

**Note**: Use the installed `skill-creator` skill (`/skill-creator`) to author and test each SKILL.md file.

### Implementation for User Story 5

- [X] T053 [US5] Create `.claude/skills/gmail-watcher/SKILL.md` using `/skill-creator` — skill purpose: extract structured metadata from a raw email message and write a correctly formatted `EMAIL_*.md` task file to `Vault/Inbox/`; input: raw email headers + body; output format: exact YAML frontmatter schema from `data-model.md` Entity InboundMessage (Gmail); include example input/output pair
- [X] T054 [P] [US5] Create `.claude/skills/whatsapp-watcher/SKILL.md` using `/skill-creator` — skill purpose: parse a WhatsApp message object and write a correctly formatted `WHATSAPP_*.md` task file to `Vault/Inbox/`; input: message JSON (from_jid, from_display, body, timestamp, keywords_matched); output format: exact YAML frontmatter schema from `data-model.md` Entity InboundMessage (WhatsApp)
- [X] T055 [P] [US5] Create `.claude/skills/gmail-reply/SKILL.md` using `/skill-creator` — skill purpose: read an email task file from `Needs_Action/` and draft a contextually appropriate reply; input: full email task file content; output: `EMAIL_REPLY_*.md` approval request file in `Pending_Approval/` with YAML frontmatter from `data-model.md` Entity ApprovalRequest (Email Reply); include tone guidance (professional, concise, no filler)
- [X] T056 [P] [US5] Create `.claude/skills/whatsapp-reply/SKILL.md` using `/skill-creator` — skill purpose: read a WhatsApp task file and draft a short, conversational reply appropriate for WhatsApp; input: WhatsApp task file content; output: `WHATSAPP_REPLY_*.md` approval request file; YAML schema from `data-model.md` Entity ApprovalRequest (WhatsApp Reply); reply must be under 500 chars for WhatsApp norms
- [X] T057 [P] [US5] Create `.claude/skills/calendar-event/SKILL.md` using `/skill-creator` — skill purpose: extract scheduling intent from a task file and draft a calendar event creation request; input: task file with scheduling context; output: `CALENDAR_*.md` approval request file; YAML schema from `data-model.md` Entity ApprovalRequest (Calendar Event); must extract: event_title, event_date (ISO 8601), event_time_start, event_time_end, event_timezone (default Asia/Karachi), attendees list
- [X] T058 [P] [US5] Create `.claude/skills/linkedin-post/SKILL.md` using `/skill-creator` — skill purpose: draft a professional LinkedIn post for business visibility and sales generation; input: task file with post topic/context + vault business context; output: `LINKEDIN_*.md` approval request file; YAML schema from `data-model.md`; post must be under 3,000 chars, include 3–5 relevant hashtags, end with a call-to-action; flag if over limit
- [X] T059 [P] [US5] Create `.claude/skills/hitl-approval/SKILL.md` using `/skill-creator` — skill purpose: validate an approval request file before the executor processes it; input: file path to an `Approved/` file; checks: all required frontmatter fields present, `expiry_at` is future, `action_type` is in the dispatch table, `status` is `pending`; output: validation report (PASS/FAIL with field-level details)
- [X] T060 [US5] Verify all 7 skills are auto-discovered — check `.claude/skills/` directory structure; each skill must have `name` and `description` fields in SKILL.md frontmatter; invoke each skill individually and confirm it produces a correctly formatted output for a sample input

**Checkpoint**: All 7 skills installed and independently verified. SC-008 satisfied.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Dashboard reporting, deploy scripts, integration wiring, and constitution compliance review.

- [X] T061 Add daily `Dashboard.md` auto-update to `src/fte/orchestrator.py` — Python log aggregation (no Claude invocation): count tasks processed today from `Vault/Logs/YYYY-MM-DD.json`, count approvals pending/approved/rejected, last watcher heartbeat timestamps; overwrite `Vault/Dashboard.md` with summary each time orchestrator runs
- [X] T062 [P] Complete `deploy/install-silver.sh` — install all 3 Silver systemd services (`fte-gmail-watcher`, `fte-whatsapp-watcher`, `fte-action-executor`), create `/var/lib/fte/whatsapp-session/` directory with correct permissions, create `~/.config/fte/` with `chmod 700`, print post-install checklist (OAuth setup step, MCP settings.json step, QR scan step)
- [X] T063 [P] Create `deploy/uninstall-silver.sh` — stop and disable all 3 Silver services, remove service files, leave data directories and token files intact (data preservation)
- [X] T064 Complete `deploy/fte-action-executor.service` — `ExecStart=fte execute`, `Restart=always`, `RestartSec=5`, `MemoryMax=256M`, `Environment=DEV_MODE=false`, `Environment=VAULT_PATH=/mnt/d/AI_Employee_Vault`
- [X] T065 Add `fte-action-executor` entry to `deploy/install-silver.sh` and wire up the `execute` CLI subcommand to the executor service loop
- [X] T066 [P] Update `specs/003-silver-functional-assistant/quickstart.md` — complete all 8 setup steps including: Node.js install, npm install for whatsapp watcher, OAuth setup (`python scripts/oauth_setup.py`), MCP settings.json registration, WhatsApp QR scan procedure, DEV_MODE smoke test for each of the 4 action types, `fte execute --dry-run` verification
- [ ] T067 Run full end-to-end smoke test with all 5 services running and `DEV_MODE=true` — verify: email → task file → approval draft → executor logs send; WhatsApp keyword → task file → approval draft; LinkedIn post task → approval draft → executor logs post; confirm zero real outbound calls in DEV_MODE (SC-009 verification)
- [ ] T068 Constitution compliance final review — verify all 8 principles pass: local-first (no cloud relay), HITL (Approved/ gate), perception-reasoning-action separation, 7 skills installed, DEV_MODE gate on executor, all actions logged, ralph-loop available, Bronze still operational

**Checkpoint**: Full Silver tier operational with DEV_MODE verified. Ready for production with `DEV_MODE=false`.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    └── Phase 2 (Foundational)  ← BLOCKS all user stories
            ├── Phase 3 (US1 Gmail) ← MVP
            ├── Phase 4 (US2 WhatsApp)
            ├── Phase 5 (US3 Calendar) ← requires Gmail MCP
            ├── Phase 6 (US4 LinkedIn)
            └── Phase 7 (US5 Agent Skills) ← can start after Phase 2
                    └── Phase 8 (Polish) ← requires all US phases
```

### User Story Dependencies

| Story | Depends On | Independently Testable? |
|-------|-----------|------------------------|
| US1 Gmail Reply | Phase 2 complete (Gmail MCP, executor) | ✅ Yes |
| US2 WhatsApp | Phase 2 complete (executor, IPC bridge) | ✅ Yes |
| US3 Calendar | Phase 2 complete (Calendar MCP, executor) + US1 orchestrator extension | ✅ Yes |
| US4 LinkedIn | Phase 2 complete (executor) | ✅ Yes |
| US5 Skills | Phase 2 complete (skill-creator installed) | ✅ Each skill individually |

### Critical Dependencies Within Phases

- T008, T009 (expiry thread) depend on T007 (executor base)
- T013 (gmail_service.py) depends on T012 (config.py)
- T014, T015, T016 (tools) depend on T013 (gmail_service)
- T017 (server.py) depends on T014–T016 (tools)
- T026 (gmail_watcher polling) depends on T024 (OAuth setup) being complete (one-time)
- T030 (actions/gmail.py) depends on T017 (Gmail MCP server running)
- T033–T040 (WhatsApp watcher) depend on T004 (npm install complete)
- T039 (actions/whatsapp.py) depends on T038 (IPC bridge running in watcher.js)
- T043 (actions/calendar.py) depends on T023 (Calendar MCP server running)
- T047–T050 (LinkedIn) depend on T024 (OAuth setup, different token)
- T053–T059 (Skills) depend on skill-creator being available (already installed)

### Parallel Opportunities

**Phase 2** — these can run in parallel after Phase 1:
```
T007-T011 (executor)  ‖  T012-T018 (Gmail MCP)  ‖  T019-T023 (Calendar MCP)  ‖  T024 (OAuth)
```

**Phase 3–6** — all 4 user stories can start in parallel after Phase 2:
```
US1 (T026-T032)  ‖  US2 (T033-T042)  ‖  US3 (T043-T046)  ‖  US4 (T047-T052)
```

**Phase 7** — all 7 SKILL.md files can be written in parallel:
```
T053 ‖ T054 ‖ T055 ‖ T056 ‖ T057 ‖ T058 ‖ T059
```

---

## Implementation Strategy

### MVP First (User Story 1 — Gmail Reply Only)

1. Complete Phase 1: Setup (T001–T006a)
2. Complete Phase 2: Foundational — focus on T007–T018 (executor + Gmail MCP) + T024 (OAuth)
3. Complete Phase 3: US1 Gmail (T026–T032)
4. **STOP AND VALIDATE**: Send test email → verify full pipeline end-to-end in DEV_MODE
5. Add `gmail-reply` skill (T055) and `hitl-approval` skill (T059)
6. Demo: Bronze still running + US1 Gmail pipeline working

### Full Silver Delivery

1. MVP (above) → validate
2. US2 WhatsApp (T033–T042) → validate with keyword message test
3. US3 Calendar (T043–T046) → validate with scheduling task test
4. US4 LinkedIn (T047–T052) → validate with post prompt test
5. US5 Remaining Skills (T053, T054, T056, T057, T058) → verify each independently
6. Phase 8 Polish (T061–T068) → full end-to-end DEV_MODE test
7. Flip `DEV_MODE=false` → production

---

## Task Summary

| Phase | Tasks | Count |
|-------|-------|-------|
| Phase 1: Setup | T001–T006a | 7 |
| Phase 2: Foundational | T007–T025 | 21 |
| Phase 3: US1 Gmail | T026–T032 | 7 |
| Phase 4: US2 WhatsApp | T033–T042 | 10 |
| Phase 5: US3 Calendar | T043–T046 | 4 |
| Phase 6: US4 LinkedIn | T047–T052 | 6 |
| Phase 7: US5 Skills | T053–T060 | 8 |
| Phase 8: Polish | T061–T068 | 8 |
| **Total** | | **70** |

**Parallel opportunities**: 4 major parallel windows (Phase 2, Phase 3–6, Phase 7 skills, Phase 8 polish tasks)
**MVP scope**: T001–T006 + T007–T018 + T024 + T026–T032 + T055 + T059 (32 tasks for working Gmail pipeline)
**Suggested first commit**: Phase 1 complete (T001–T006) — structure and deps only, no feature code
