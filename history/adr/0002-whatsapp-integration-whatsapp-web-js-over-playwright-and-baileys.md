# ADR-0002: WhatsApp Integration — whatsapp-web.js over Playwright and Baileys

- **Status:** Accepted
- **Date:** 2026-02-27
- **Feature:** 003-silver-functional-assistant
- **Context:** Silver tier requires monitoring a personal WhatsApp account for inbound messages and sending replies. There are three viable approaches: raw Playwright automation of WhatsApp Web, the `whatsapp-web.js` Node.js library (Puppeteer-based), or the `@whiskeysockets/baileys` Node.js library (direct WebSocket protocol). The choice determines the runtime language, session management strategy, and operational reliability of the watcher daemon in WSL2.

  The user previously attempted Playwright-based LinkedIn automation and had their account banned. WhatsApp's detection sensitivity is a real constraint.

## Decision

Use **whatsapp-web.js** with **LocalAuth** session persistence for the WhatsApp watcher daemon:

- **Library**: `whatsapp-web.js` (npm, Puppeteer-based, WhatsApp Web automation)
- **Session strategy**: `LocalAuth(dataPath: '/var/lib/fte/whatsapp-session')` — persists Chromium profile to disk; survives restarts without QR re-scan
- **Runtime**: Node.js 20+ LTS (separate from the Python stack)
- **First-time QR**: Printed as ASCII art to the WSL2 terminal via `qrcode-terminal` — no display/WSLg required
- **Message detection**: Event-driven `client.on('message', cb)` — no polling
- **WatcherState**: FIFO JSON file (2,000-entry window) for cross-restart deduplication
- **Crash recovery**: In-process heartbeat (`client.getState()` every 30s) + systemd `MemoryMax=512M` + `RuntimeMaxSec=86400` (daily clean restart)
- **Outbound**: `client.sendMessage(jid, text)` where JID = `<E164-phone>@c.us`

## Consequences

### Positive

- QR scan required only once — `LocalAuth` persists session to disk; daemon restarts are seamless
- Event-driven message detection with zero polling overhead
- Library actively maintained for WhatsApp Web compatibility; patches ship when WhatsApp updates its web client
- QR code prints to terminal as ASCII art — works in headless WSL2 without a display or WSLg
- Ban risk equivalent to using the official WhatsApp Web in a browser (same Chromium user-agent and session token)
- `LocalAuth` handles stale `SingletonLock` cleanup automatically

### Negative

- Introduces Node.js as a second runtime in a Python-primary project
- Adds Chromium (~400MB RAM) as a runtime dependency for the watcher daemon
- `MemoryMax=512M` systemd limit required to prevent WSL2 memory pressure
- `RuntimeMaxSec=86400` forces a daily daemon restart (no QR needed; session preserved by `LocalAuth`)
- When WhatsApp updates its web client, the library may lag 1–3 days before a compatibility patch

## Alternatives Considered

**Alternative A: Raw Playwright (Python)**
- Pros: Python-native (no runtime boundary), large community
- Cons: No built-in WhatsApp session management; detecting new messages requires polling `window.Store.Msg` (internal WhatsApp Web JS object — undocumented, changes without notice); QR rendering requires `headless=False` + display (problematic in WSL2 without WSLg); significantly more implementation effort with worse reliability
- Rejected: Maintenance burden of fragile DOM queries outweighs the Python-native benefit

**Alternative B: @whiskeysockets/baileys (Node.js, no browser)**
- Pros: No Chromium (~80MB RAM vs ~400MB); fully event-driven; lower resource footprint
- Cons: Implements WhatsApp's private binary WebSocket protocol — explicit Terms of Service violation per Meta; has been subject to cease-and-desist actions; protocol breaks occur without notice when WhatsApp updates its handshake/protobuf schema; user previously had account banned from Playwright-based automation (heightened sensitivity to violations)
- Rejected: ToS violation risk + protocol fragility unacceptable for a personal account the user depends on

## References

- Feature Spec: `specs/003-silver-functional-assistant/spec.md` (US2, FR-001–004)
- Implementation Plan: `specs/003-silver-functional-assistant/plan.md` — Phase 4
- Research: `specs/003-silver-functional-assistant/research.md` — Decision 3
- Related ADRs: ADR-0001 (service topology — this decision creates the Node.js service boundary)
