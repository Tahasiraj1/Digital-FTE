# Contract: Action Executor Interface

**Feature**: 003-silver-functional-assistant
**Date**: 2026-02-27
**Owner**: fte-action-executor service

---

## Overview

The `fte-action-executor` service watches `Vault/Approved/` for approved action files and dispatches them to the correct handler. This contract defines the interface between the HITL approval file format and the executor's dispatch logic.

---

## Trigger Contract: Approved/ File

**Trigger**: A `.md` file appears in `Vault/Approved/` (detected by `PollingObserver`).

**File format** (authoritative — frontmatter fields):

| Field | Type | Required | Values | Description |
|-------|------|----------|--------|-------------|
| `action_type` | string | ✅ | `send_email`, `send_whatsapp`, `create_calendar_event`, `publish_linkedin_post` | Dispatch key |
| `source_task` | string | ✅ | relative path | Original task file path |
| `created_at` | ISO 8601 | ✅ | UTC timestamp | When the approval request was created |
| `expiry_at` | ISO 8601 | ✅ | UTC timestamp | Auto-reject deadline |
| `status` | string | ✅ | `pending` → `executing` → `done` / `failed` | Mutated by executor |

**Dispatch table**:

| `action_type` | Handler | MCP Tools Used | Timeout |
|---------------|---------|---------------|---------|
| `send_email` | `actions/gmail.py` | `mcp__gmail__gmail_send_message` | 30s |
| `send_whatsapp` | `actions/whatsapp.py` | whatsapp-web.js IPC | 30s |
| `create_calendar_event` | `actions/calendar.py` | `mcp__calendar__create_event` | 30s |
| `publish_linkedin_post` | `actions/linkedin.py` | LinkedIn REST API (direct) | 30s |

---

## Execution Contract

**Pre-execution check**:
1. Parse `expiry_at` from frontmatter. If `expiry_at < now` → move to `Rejected/` with `status: expired`, skip.
2. Apply 0.2s sleep + file-size stability check before reading.
3. Set `status: executing` in file frontmatter (in-place edit) to prevent double-processing on restart.

**Executor invocation** (for MCP-based actions):

```
claude -p "<action-specific prompt>" \
  --add-dir <vault_path> \
  --allowedTools <action-specific-tool> \
  --dangerously-skip-permissions
```

The prompt must include the full path to the approved file and instruct Claude to execute only the specified action without further reasoning.

**Completion contract**:
- On **success**: Move file from `Approved/` to `Done/`. Log entry with `result: "success"`.
- On **failure** (exception, timeout, non-zero exit): Move file from `Approved/` to `Rejected/` with `status: failed` and `error` field. Log entry with `result: "error"`.

---

## Expiry Enforcement Contract

**Background thread** in `executor.py` runs every 300 seconds:
1. Scan all files in `Vault/Pending_Approval/`
2. For each file, parse `expiry_at` from frontmatter
3. If `expiry_at < now(UTC)` → move file to `Vault/Rejected/`, update `status: expired`, log

**Expiry field** is always set at approval-request creation time as `created_at + 24h`. Never derived from filesystem mtime.

---

## Service File Naming Convention

| Action Type | Approval File Prefix | Example |
|-------------|---------------------|---------|
| Email reply | `EMAIL_REPLY_` | `EMAIL_REPLY_abc123_20260227-143500.md` |
| WhatsApp reply | `WHATSAPP_REPLY_` | `WHATSAPP_REPLY_xyz789_20260227-143500.md` |
| Calendar event | `CALENDAR_` | `CALENDAR_meeting-alice_20260227-143500.md` |
| LinkedIn post | `LINKEDIN_` | `LINKEDIN_q1-results_20260227-143500.md` |

---

## Rate Limit Contracts

| Action | Client-Side Limit | Platform Limit | On Exceeded |
|--------|------------------|---------------|-------------|
| Email send | 10/hour (per constitution) | Gmail API quotas | Write alert to Needs_Action/, skip |
| WhatsApp reply | No explicit limit | Per-account throttle | Retry once after 10s, then skip |
| Calendar event | No explicit limit | Google Calendar quotas | Move to Rejected/ on 429 |
| LinkedIn post | 10/day | ~10/day per token | Write alert + move to Rejected/ |
