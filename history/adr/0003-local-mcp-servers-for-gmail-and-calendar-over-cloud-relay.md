# ADR-0003: Custom Python FastMCP Servers for Gmail and Calendar

- **Status:** Accepted (revised 2026-02-28 — supersedes npm package approach)
- **Date:** 2026-02-27 | **Revised:** 2026-02-28
- **Feature:** 003-silver-functional-assistant
- **Context:** Silver tier requires reading Gmail (inbound monitoring) and creating Google Calendar events (outbound action). The `fte-orchestrator` invokes `claude -p` as a subprocess; that subprocess must have access to Gmail and Calendar APIs. There are four viable approaches: cloud-relay MCP services (Composio, Rube), third-party npm MCP packages, custom Python MCP servers written for this project, or native Python libraries inside the orchestrator process itself.

  Two constraints drive this decision:
  1. **Local-first**: no personal data may leave the local machine to a third-party relay — eliminates cloud relay entirely
  2. **Hackathon requirement**: "All AI functionality should be implemented as Agent Skills" and "MCP Servers (Local Node.js/Python scripts)" — the hackathon explicitly expects custom-written MCP servers, not consumed third-party packages

  Additionally, the user already has a working Gmail MCP server at `D:\Code.Taha\email-app\mcp_server\` — a production-quality Python FastMCP implementation built for the OpenAI Apps Store. Adapting it eliminates the implementation cost of writing a custom MCP server from scratch.

## Decision

Use **custom Python FastMCP servers** owned by this project, registered in `~/.claude/settings.json` (user-level):

- **Gmail MCP**: Adapted from `D:\Code.Taha\email-app\mcp_server\` — Python `FastMCP` (from `mcp[cli]` package), lives at `src/mcp_servers/gmail/`; strip multi-user OAuth decorator (`@require_oauth`, `TokenManager`) and replace with single-user local token file reader (`~/.config/fte/gmail_token.json`); all Gmail API call logic (list_emails, read_email, send_reply) retained as-is
- **Calendar MCP**: New Python `FastMCP` server at `src/mcp_servers/calendar/` following identical pattern; tools: `create_event`, `list_events`; uses same Google OAuth2 token file as Gmail (same Google Cloud project, same consent screen)
- **Transport**: Both servers run as stdio MCP processes launched by `claude -p` via `~/.claude/settings.json`; `ExecStart: python -m mcp_servers.gmail.main` / `python -m mcp_servers.calendar.main`
- **Tool naming**: `mcp__gmail__list_emails`, `mcp__gmail__send_reply`, `mcp__calendar__create_event` (key = JSON key in `mcpServers` settings)
- **OAuth2 scope**: `gmail.readonly` + `gmail.send` + `calendar` — all on one token via `scripts/oauth_setup.py`
- **Token storage**: `~/.config/fte/gmail_token.json`, `chmod 600`

## Consequences

### Positive

- Every line of MCP server code is owned and auditable — zero supply chain risk (no unreviewed npm packages handling inbox content)
- Gmail MCP adaptation is low-effort: the email-app's Gmail API call logic (`list_emails`, `read_email`, `send_reply`) is proven and complete; only the OAuth layer (30–50 lines) needs replacing
- Satisfies the hackathon requirement explicitly: these are custom-written MCP servers using local Python scripts
- Both servers share the same `google-api-python-client` dependency already present in `pyproject.toml` — no additional runtime dependency
- Single OAuth token file covers both Gmail and Calendar — one consent flow, one refresh path
- FastMCP's stdio transport integrates identically with `claude -p` as any npm-based MCP server — no change to the executor invocation pattern
- Adding a third Google service (Drive, Sheets) in Gold tier follows the same Python FastMCP pattern — copy, adapt, register

### Negative

- Requires maintaining the Gmail and Calendar MCP server code going forward (Google API changes, token expiry handling)
- OAuth2 token refresh must be handled in `gmail_service.py` — `google-auth-oauthlib` handles this automatically when using `Credentials` with a refresh token, but we must ensure the refreshed token is written back to disk
- First-run requires `python scripts/oauth_setup.py` to complete browser consent before the MCP servers can authenticate

## Alternatives Considered

**Alternative A: Cloud-Relay MCP (Composio / Rube)**
- Pros: No local install; zero setup; supports many services via single integration
- Cons: Email content and calendar data transmitted to third-party infrastructure — explicit violation of data-locality constraint; requires paid account for production volumes
- Rejected: Data locality constraint is non-negotiable

**Alternative B: Third-Party npm MCP Packages (`@gongrzhe/server-gmail-autoauth-mcp`, `@cocal/google-calendar-mcp`)**
- Pros: Zero implementation effort; npm install and configure
- Cons: Unaudited code from individual maintainers handles inbox content and OAuth tokens — supply chain risk; violates hackathon requirement for custom-written MCP servers; `npx` cold-start per invocation; token refresh reliability depends on package author; low download counts, risk of abandonment
- Rejected: Supply chain risk unacceptable for personal inbox; hackathon requires custom servers

**Alternative C: Native Python Libraries Directly in Orchestrator (no MCP)**
- Pros: No MCP indirection; direct Google API calls in Python
- Cons: Tools not auto-discovered by Claude subprocess; orchestrator becomes tightly coupled to specific API versions; each new Google service requires new Python code AND system prompt updates; breaks the perception-reasoning-action separation (Constitution Principle III)
- Rejected: MCP server pattern provides clean separation and automatic tool discovery at negligible cost given the email-app starting point

## References

- Feature Spec: `specs/003-silver-functional-assistant/spec.md` (US1, FR-001–003, FR-006, FR-018)
- Implementation Plan: `specs/003-silver-functional-assistant/plan.md` — Phase 2 (Gmail MCP, Calendar MCP)
- Tasks: `specs/003-silver-functional-assistant/tasks.md` — T012–T018 (Gmail MCP), T019–T023 (Calendar MCP)
- Source reference: `D:\Code.Taha\email-app\mcp_server\` — Gmail FastMCP server being adapted
- Quickstart: `specs/003-silver-functional-assistant/quickstart.md` — Steps 2–3 (OAuth2 setup)
- Related ADRs: ADR-0001 (service topology — defines subprocess invocation pattern), ADR-0004 (action execution — uses these MCP tools for outbound)
