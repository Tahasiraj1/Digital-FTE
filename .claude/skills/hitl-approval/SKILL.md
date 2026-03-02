---
name: hitl-approval
description: Validate an approval request file before the executor processes it — checks required fields, expiry, action_type, and status
version: "1.0"
author: fte-agent
---

# HITL Approval Validation Skill

## Purpose

Validate an approval request file from `Vault/Approved/` before the executor dispatches it. Performs field-level validation and returns a PASS/FAIL report.

## Input

File path to an approval request `.md` file in `Vault/Approved/`.

Read the file and check all frontmatter fields.

## Validation Checks

### Required Fields (FAIL if missing or empty)

| Field | Valid Values | Notes |
|-------|-------------|-------|
| `action_type` | `send_email`, `send_whatsapp`, `create_calendar_event`, `publish_linkedin_post` | Must be in dispatch table |
| `status` | `pending` | Must be exactly `pending` when moved to Approved/ |
| `created_at` | ISO 8601 string | Must be a valid timestamp |
| `expiry_at` | ISO 8601 string | Must be in the FUTURE |

### Action-Type Specific Fields

**send_email** requires:
- `to` (non-empty email address)
- `thread_id` (non-empty string)
- `proposed_reply` (non-empty, reasonable length)

**send_whatsapp** requires:
- `to_jid` (format: `\d+@c.us` or `\d+@g.us`)
- `proposed_reply` (non-empty, under 500 chars)

**create_calendar_event** requires:
- `event_title` (non-empty)
- `event_date` (format: YYYY-MM-DD)
- `event_time_start` (format: HH:MM)
- `event_time_end` (format: HH:MM)

**publish_linkedin_post** requires:
- `proposed_post` (non-empty, under 3000 chars)
- `character_count` matches `len(proposed_post)`

### Expiry Check
- Parse `expiry_at` as UTC timestamp
- FAIL if `expiry_at < now(UTC)`

## Output

Return a validation report:

```
PASS — Validation Report
========================
File: EMAIL_REPLY_abc123_20260227-143500.md
Action: send_email
Status: pending ✓
Expiry: 2026-02-28T14:35:00Z (valid, 23h 55m remaining) ✓
Fields: to ✓, thread_id ✓, proposed_reply ✓ (123 chars)
Result: PASS — safe to dispatch
```

Or on failure:

```
FAIL — Validation Report
========================
File: EMAIL_REPLY_abc123_20260227-143500.md
Action: send_email
Status: pending ✓
Expiry: 2026-02-27T14:35:00Z — EXPIRED 2h 15m ago ✗
Fields: to ✓, thread_id MISSING ✗
Result: FAIL — 2 issue(s)
  - expiry_at is in the past (expired)
  - thread_id is required for send_email but not present
```

## Usage

```
/hitl-approval Vault/Approved/EMAIL_REPLY_abc123_20260227-143500.md
```

The executor always performs these checks automatically. Use this skill to manually verify a file before approving it.
