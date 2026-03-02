---
name: calendar-event
description: Extract scheduling intent from a task file and draft a calendar event creation request in Pending_Approval/
version: "1.0"
author: fte-agent
---

# Calendar Event Skill

## Purpose

Read a task file from `Vault/Needs_Action/` that contains scheduling intent (mentions a meeting, call, appointment with date/time and attendees) and extract the scheduling details into a `CALENDAR_*.md` approval request in `Vault/Pending_Approval/`.

## Input

Any task file in `Vault/Needs_Action/` that mentions:
- A meeting, call, or appointment
- A date or day of the week
- At least one time reference (HH:MM or "3pm" etc.)
- At least one attendee (email address or name)

## Output

Write one file to `Vault/Pending_Approval/`:

**Filename**: `CALENDAR_<slug>_<YYYYMMDD-HHMMSS>.md`
(slug = 3-5 words from event title, lowercase, hyphenated)

```yaml
---
action_type: create_calendar_event
source_task: "Needs_Action/<filename>"
event_title: "Meeting with John Smith"
event_date: "2026-03-03"        # ISO 8601 YYYY-MM-DD
event_time_start: "15:00"       # HH:MM 24-hour
event_time_end: "16:00"         # HH:MM 24-hour (default: start + 1 hour)
event_timezone: "Asia/Karachi"  # always default to Asia/Karachi unless specified
attendees:
  - "john@example.com"
event_description: "Discussion of project timeline as requested."
created_at: "<ISO8601 now>"
expiry_at: "<ISO8601 24h from now>"
status: pending
---

# Calendar Event — Awaiting Approval

**Event**: Meeting with John Smith
**When**: 2026-03-03, 15:00–16:00 Asia/Karachi
**Attendees**: john@example.com

## Description

Discussion of project timeline as requested.

---

**To Approve**: Move this file to `Vault/Approved/`
**To Reject**: Move this file to `Vault/Rejected/`
**Expires**: <expiry_at>
```

## Extraction Rules

1. **Date**: Convert relative dates to absolute ISO 8601:
   - "Tuesday" → next Tuesday from today
   - "tomorrow" → today + 1 day
   - "next week" → Monday of next week
2. **Time**: Convert 12-hour to 24-hour: "3pm" → "15:00", "10am" → "10:00"
3. **Duration**: Default 1 hour unless specified ("30 minutes", "2 hours")
4. **Timezone**: Default to `Asia/Karachi` unless the task specifies otherwise
5. **Title**: Generate a descriptive 4-6 word title from context
6. **Attendees**: Extract email addresses. If only a name is given, include it in description
7. **Expiry**: Set `expiry_at` to 24 hours from `created_at`

## Example

**Input**: "Can we schedule a call with John (john@example.com) on Tuesday at 3pm for 30 minutes?"

**Output**:
- event_title: "Call with John"
- event_date: "2026-03-04" (next Tuesday)
- event_time_start: "15:00"
- event_time_end: "15:30"
- attendees: ["john@example.com"]
