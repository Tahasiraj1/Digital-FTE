# Research: Silver Tier — Functional Assistant

**Feature**: 003-silver-functional-assistant
**Date**: 2026-02-27
**Agents dispatched**: 4 (parallel)

---

## Decision 1: MCP Server Configuration for Claude Code Subprocess

**Decision**: Add Gmail and Calendar MCP servers to `~/.claude/settings.json` (user-level).

**Rationale**: Claude Code uses a three-tier lookup when invoked via `claude -p`:
1. `--mcp-config <path>` flag (explicit)
2. `.claude/settings.json` (project-level)
3. `~/.claude/settings.json` (user-level)

User-level is correct for this project: credentials stay out of the git repo, and the systemd unit already sets `Environment=HOME=/home/taha` so the subprocess resolves `~` correctly.

**Exact config format** (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "gmail": {
      "type": "stdio",
      "command": "/usr/bin/npx",
      "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
      "env": {
        "GMAIL_CREDENTIALS_PATH": "/home/taha/.config/fte/gmail_credentials.json",
        "GMAIL_TOKEN_PATH": "/home/taha/.config/fte/gmail_token.json"
      }
    },
    "calendar": {
      "type": "stdio",
      "command": "/usr/bin/npx",
      "args": ["-y", "@cocal/google-calendar-mcp"],
      "env": {
        "GOOGLE_CREDENTIALS_PATH": "/home/taha/.config/fte/gmail_credentials.json",
        "GOOGLE_TOKEN_PATH": "/home/taha/.config/fte/calendar_token.json"
      }
    }
  }
}
```

**MCP tool naming convention**: `mcp__<server-key>__<tool-name>` (double underscore).
- Gmail: `mcp__gmail__gmail_send_message`, `mcp__gmail__gmail_create_draft`, `mcp__gmail__gmail_list_messages`
- Calendar: `mcp__calendar__create_event`, `mcp__calendar__list_events`

**MCP loads in subprocess mode**: Confirmed — `claude -p` loads MCP servers at startup, not just in interactive mode.

**One-time setup**: `@gongrzhe/server-gmail-autoauth-mcp` requires a browser OAuth consent on first run. Complete once, then `token.json` handles all subsequent headless calls.

**Alternatives considered**:
- Project-level `.claude/settings.json`: Rejected — would require committing MCP config with credential paths to the repo.
- `--mcp-config` flag per invocation: Rejected — adds complexity to every orchestrator subprocess call.

---

## Decision 2: Service Topology — Three New systemd Services

**Decision**: Silver tier adds three new services alongside the existing two (fte-watcher, fte-orchestrator):

| Service | Responsibility | Technology |
|---------|---------------|------------|
| `fte-gmail-watcher` | Poll Gmail every 2 min → write EMAIL_*.md to Inbox/ | Python + Gmail API |
| `fte-whatsapp-watcher` | Monitor WhatsApp messages → write WHATSAPP_*.md to Inbox/ | Node.js + whatsapp-web.js |
| `fte-action-executor` | Watch Approved/ → execute actions via Claude + MCP | Python |

**Rationale for separate action executor**: The existing orchestrator's 120s Claude timeout and `in_flight` boolean guard mean it cannot handle concurrent work. The executor needs a 30s action SLA (FR-007). Merging both into one process would cause 120s blocking delays on approval execution. Separation mirrors the established pattern: each service owns exactly one pipeline stage transition.

**Alternatives considered**:
- Extend orchestrator to also watch Approved/: Rejected — timeout contention, violates single-responsibility.
- Node.js executor (unify with whatsapp-web.js): Rejected — Constitution Principle III separates layers; Python is the established action executor language.

---

## Decision 3: WhatsApp Watcher Implementation (whatsapp-web.js)

**Decision**: Use `whatsapp-web.js` with `LocalAuth` for WhatsApp monitoring.

**Session persistence**: `LocalAuth(dataPath: '/var/lib/fte/whatsapp-session')` — survives restarts; QR scan only required once.

**WatcherState**: JSON file at `/var/lib/fte/whatsapp-session/watcher-state.json`. Format: `{"processed_ids": ["id1", "id2", ...]}` (FIFO sliding window of 2,000 entries). Always write via atomic `rename()` to prevent corruption on OOM-kill.

**Disconnection handling**:
- `UNPAIRED` / `UNPAIRED_IDLE` / `LOGOUT` → delete session dir, write SYSTEM alert to Inbox/, `process.exit(1)`, systemd restarts and displays QR in journal
- `CONFLICT` (another WA Web tab opened) → do NOT delete session; reinitialize after 15s

**Keyword filtering**: Pre-compiled `RegExp` at module load time (not per-message):
```javascript
const KEYWORD_REGEX = new RegExp(
  ['urgent','asap','invoice','payment','help','contract'].map(k => `\\b${k}\\b`).join('|'), 'i'
);
```

**Crash recovery**: In-process heartbeat (`client.getState()` every 30s); on throw → `process.exit(1)`. systemd `MemoryMax=512M` + `Restart=on-failure` provides outer recovery layer.

**Memory management**: `RuntimeMaxSec=86400` (daily clean restart). `LocalAuth` preserves session; no QR re-scan. Extract only primitives from message objects — never retain raw Message objects.

**Outbound messaging (JID format)**: `client.sendMessage('447911123456@c.us', text)` — JID must be `<E164-digits>@c.us`. Store `from_jid` in task file frontmatter for reply targeting.

**Alternatives considered**:
- Raw Playwright: Rejected — requires manual DOM polling against `window.Store` (fragile internal), no built-in QR terminal rendering.
- Baileys: Rejected — explicit WhatsApp ToS violation; protocol-break risk for a personal daemon that needs reliability.

---

## Decision 4: HITL Approval Workflow Architecture

**Decision**: Frontmatter `action_type` is authoritative for dispatch; filename prefix (`EMAIL_`, `LINKEDIN_`, etc.) is for human readability only.

**Vault folders**: `Pending_Approval/`, `Approved/`, `Rejected/` are **already in `REQUIRED_DIRS` in `vault.py`**. No vault migration needed for Silver.

**Action dispatch in executor**: Claude Code subprocess with `--allowedTools` constrained to the specific action's MCP tools:
```python
subprocess.run([
    "claude", "-p", prompt,
    "--add-dir", str(vault_path),
    "--allowedTools", f"mcp__gmail__gmail_send_message",
    "--dangerously-skip-permissions",
], timeout=30, ...)
```
The `--allowedTools` constraint is the safety gate — Claude cannot take any action outside the approved scope.

**Expiry enforcement**: Background thread in `executor.py` scans `Pending_Approval/` every 5 minutes, parses `expiry_at` from frontmatter (UTC ISO 8601), moves expired files to `Rejected/` with `status: expired`. Uses creation-time `expiry_at`, not mtime (mtime is unreliable across moves).

**Race condition**: Apply 0.2s sleep + file-size stability check on Approved/ file detection (consistent with existing `InboxHandler` pattern in `watcher.py`).

**Dashboard.md**: Scheduled Python update inside existing `fte-orchestrator` (daily, log aggregation — not an AI reasoning task). No new service needed.

---

## Decision 5: Agent Skills Architecture

**Decision**: One `SKILL.md` file per skill in `.claude/skills/<skill-name>/SKILL.md` (directory-per-skill).

**Required frontmatter fields**: `name`, `description`
**Optional fields**: `version`, `tools`, `author`

**Auto-discovery**: Claude Code scans `.claude/skills/` at startup — no registration needed.

**Invocation pattern**: Natural language in prompt: `"Use the gmail-reply skill to process the task file at <path>"`. No `--skill` flag exists.

**MCP tools in skills**: Declared in `tools:` frontmatter list using `mcp__<server>__<tool>` convention. Constrains which tools the skill can access.

**Seven skills for Silver**:
| Skill | Purpose |
|-------|---------|
| `gmail-watcher` | Read EMAIL_*.md, extract structured context |
| `whatsapp-watcher` | Read WHATSAPP_*.md, extract structured context |
| `gmail-reply` | Draft email reply → write to Pending_Approval/ |
| `whatsapp-reply` | Draft WhatsApp reply → write to Pending_Approval/ |
| `calendar-event` | Draft calendar event → write to Pending_Approval/ |
| `linkedin-post` | Draft LinkedIn post → write to Pending_Approval/ |
| `hitl-approval` | Format and validate Pending_Approval/ request files |

**Testing**: `npx @anthropic-ai/claude-code skills run <name> --input <file>` for isolated skill testing.

---

## Decision 6: LinkedIn OAuth2 Token Management

**Decision**: Proactive token refresh 7 days before expiry. Store tokens at `~/.config/fte/linkedin_token.json` (chmod 600).

**Token lifetimes**: Access token: 60 days. Refresh token: 365 days (rotation — every refresh call returns a new refresh token; must save it).

**Refresh API**: `POST https://www.linkedin.com/oauth/v2/accessToken` with `grant_type=refresh_token`.

**Initial auth**: One-time local HTTP server at `localhost:8765/callback` captures OAuth2 code. Script: `uv run python src/fte/linkedin_auth.py`.

**Rate limits**: ~10 posts/day per member token. `429 Too Many Requests` with `Retry-After` header. Max post length: 3,000 characters.

**Token expiry alerts**: Write `SYSTEM_linkedin-token-expiring-soon.md` to `Needs_Action/` when refresh token is within 30 days of expiry. Write `SYSTEM_linkedin-token-expired.md` when expired.

**Google Cloud setup** (shared by Gmail + Calendar):
1. Create project at `console.cloud.google.com`
2. Enable Gmail API + Google Calendar API
3. OAuth consent screen: External, add Gmail as test user
4. Create Desktop app OAuth2 credential → download `credentials.json`

**LinkedIn Developer App setup**:
1. Create app at `developer.linkedin.com`
2. Request "Share on LinkedIn" product (instant approval for personal apps)
3. Add `http://localhost:8765/callback` as Authorized Redirect URL
4. Note Client ID + Client Secret → `.env`

---

## Decision 7: Constitution Compliance — Justified Deviation

**Deviation**: Constitution names "Playwright" for web automation; Silver uses `whatsapp-web.js` (Puppeteer-based).

**Justification**: `whatsapp-web.js` is the maintained WhatsApp-specific Puppeteer wrapper. It provides:
- Built-in `LocalAuth` session management (Playwright equivalent requires custom code)
- Event-driven `message` event vs manual DOM polling
- QR code terminal rendering without X11/WSLg
- Community patches for WhatsApp Web protocol updates

The spirit of the constitution (use established tooling for web automation) is satisfied. The letter ("Playwright") refers to the browser automation layer — `whatsapp-web.js` uses the same Chromium runtime, just with a WhatsApp-specific abstraction layer above Puppeteer.

📋 Architectural decision detected: Silver tier service topology (separate fte-action-executor), MCP invocation strategy (Claude subprocess vs direct JSON-RPC), and WhatsApp library choice (whatsapp-web.js vs Playwright) — Document reasoning and tradeoffs? Run `/sp.adr silver-tier-architecture`
