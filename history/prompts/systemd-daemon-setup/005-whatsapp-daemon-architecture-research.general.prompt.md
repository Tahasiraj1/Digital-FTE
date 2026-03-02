---
id: "005"
title: WhatsApp Daemon Architecture Research
stage: general
date: 2026-02-27
surface: agent
model: claude-sonnet-4-6
feature: systemd-daemon-setup
branch: 002-systemd-daemon-setup
user: Tahasiraj1
command: research
labels: ["whatsapp-web.js","daemon","WatcherState","puppeteer","keyword-filter","session","memory","outbound","systemd","WSL2"]
links:
  spec: specs/002-systemd-daemon-setup/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - null
tests:
  - null
---

## Prompt

Research production architecture patterns for a `whatsapp-web.js` daemon that monitors incoming WhatsApp messages and writes structured `.md` files to a vault folder.

Context:
- Running as a systemd service on WSL2 Ubuntu
- Personal WhatsApp account (not Business API)
- Session stored via `LocalAuth` at `/var/lib/fte/whatsapp-session`
- New messages should create `WHATSAPP_<id>.md` files in `/mnt/d/AI_Employee_Vault/Inbox/`
- Only keyword-matched messages should trigger file creation (keywords: urgent, asap, invoice, payment, help, contract)
- We need a `WatcherState` mechanism to track processed message IDs across restarts

Answer these specific questions:

1. **WatcherState file format**: What is the best format and location for tracking processed WhatsApp message IDs across restarts? JSON file at a fixed path? How do you handle the file growing indefinitely (sliding window)?

2. **Reconnection on session loss**: If WhatsApp invalidates the linked device session (e.g., user opened WhatsApp on another device, or 14-day inactivity), what event does whatsapp-web.js emit? How should the daemon handle this — alert file in vault, stop the service, attempt re-auth?

3. **Keyword filtering**: Where in the event flow is the best place to apply keyword filtering? In the `message` event handler directly, or in a separate filter function? How do you handle keyword matching (case-insensitive substring? regex?)?

4. **Task file format**: What should a `WHATSAPP_<id>.md` file look like? Based on the Bronze tier pattern (EMAIL_*.md format), design the YAML frontmatter and body for a WhatsApp task file that the orchestrator can process.

5. **Puppeteer crash recovery**: If the headless Chromium process crashes (OOM, WSL2 issue), does whatsapp-web.js detect this and emit an event? Or does the Node.js process just die? What's the recommended pattern for auto-recovery?

6. **Memory management**: WhatsApp Web accumulates messages in memory over time. What are best practices for preventing memory leaks in a long-running whatsapp-web.js daemon? (message store limits, periodic restarts, etc.)

7. **Outbound messaging**: To send a WhatsApp reply (after HITL approval), what is the exact whatsapp-web.js API call? Does it need the JID (e.g., `447911123456@c.us`) or can it use a phone number directly?

Return concrete code examples and best practices for each question.

## Response snapshot

Produced concrete answers and code examples for all 7 questions:

1. **WatcherState**: JSON at `/var/lib/fte/whatsapp-session/watcher-state.json` with a sliding window of 2,000 entries. Uses atomic `fs.renameSync(tmp, dest)` writes to prevent corruption. FIFO eviction from the front of the array when over window_size. State is loaded once at startup and checked per message in the `'message'` event handler.

2. **Reconnection**: `'disconnected'` event fires with `reason` string (`UNPAIRED`, `UNPAIRED_IDLE`, `CONFLICT`, `LOGOUT`). UNPAIRED/UNPAIRED_IDLE → delete session directory + exit(1) (systemd restarts, next run forces QR). CONFLICT → setTimeout(reinitialize, 15000). Transient → setTimeout(reinitialize, 5000). Alert files written to Inbox/ in all cases.

3. **Keyword filtering**: Applied inside the `'message'` event handler as a fast-path predicate. Pre-compiled regex with `\b` word boundaries and `'i'` flag at module load time. Separate `matchesKeyword(body)` and `extractMatchedKeywords(body)` functions for testability. `message.fromMe` guard first.

4. **Task file format**: YAML frontmatter with type, source, status, message_id, from_jid, from_display, chat_type, timestamp_unix, timestamp_iso, body_preview, keywords_matched array, has_media, group_name, requires_action, priority. Markdown body with human-readable From/Time/Chat/Keywords/Message sections. Filename: `WHATSAPP_<sanitized_message_id>.md`.

5. **Puppeteer crash recovery**: Cannot reliably catch OOM-kill from within same process. Use heartbeat via `client.getState()` every 30s — throws if Chromium dead, triggers `process.exit(1)`. Combined with systemd `MemoryMax=512M` (SIGTERM at limit before OOM-kill) and `Restart=on-failure`. `TimeoutStopSec=10s` in unit file.

6. **Memory management**: Primary strategy is `RuntimeMaxSec=86400` in unit file (clean 24h restart, LocalAuth preserves session). Secondary: never accumulate Message objects (extract primitives immediately), write media to disk immediately on download, do not call `getChats()`/`getMessages()` in polling loops. Use `webVersionCache: { type: 'local' }` to avoid repeated web version fetches.

7. **Outbound messaging**: `client.sendMessage('447911123456@c.us', text)` — JID format required (E.164 digits + `@c.us`). `message.reply(text)` for quoted replies. `client.isRegisteredUser(jid)` to verify registration. Watch `Approved/` folder every 10s; on finding `WHATSAPP_REPLY_*.md`, send and move to `Done/` or `Rejected/`.

## Outcome

- Impact: Comprehensive production architecture established for whatsapp-web.js daemon; ready to scaffold Silver-tier WhatsApp watcher feature
- Tests: null
- Files: null (research only — no code files produced)
- Next prompts: /sp.specify for whatsapp-watcher feature; then /sp.plan to scaffold Node.js daemon structure; then /sp.tasks for implementation
- Reflection: The most critical non-obvious decisions are (1) atomic state writes via rename to survive Chromium OOM crashes mid-write, (2) treating CONFLICT differently from UNPAIRED on disconnect (don't delete session on CONFLICT), and (3) RuntimeMaxSec=86400 as the practical memory management solution rather than complex in-process cleanup.

## Evaluation notes (flywheel)

- Failure modes observed: WebSearch and WebFetch tools were unavailable in this session; research conducted from library knowledge of whatsapp-web.js API, Puppeteer, and systemd
- Graders run and results (PASS/FAIL): null
- Prompt variant (if applicable): null
- Next experiment: Validate `'disconnected'` reason strings against live whatsapp-web.js v1.x source when implementing
