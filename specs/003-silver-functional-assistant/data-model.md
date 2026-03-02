# Data Model: Silver Tier — Functional Assistant

**Feature**: 003-silver-functional-assistant
**Date**: 2026-02-27

---

## Entity: InboundMessage (Gmail)

File path: `Vault/Inbox/EMAIL_<message-id>.md`
Moved to: `Vault/Needs_Action/<timestamp>-EMAIL_<message-id>.md` by fte-watcher

```yaml
---
type: email
source: gmail
status: unprocessed
message_id: "<gmail-message-id>"
thread_id: "<gmail-thread-id>"
from: "sender@example.com"
from_name: "John Smith"
subject: "Re: Project Timeline"
received: "2026-02-27T14:32:00Z"
priority: high              # high | normal (high = starred or Important label)
has_attachments: false
labels: ["INBOX", "IMPORTANT"]
---

# Email — Requires Action

**From**: John Smith (`sender@example.com`)
**Subject**: Re: Project Timeline
**Received**: 2026-02-27T14:32:00Z

## Message Body

<full email text here>

## Required Action

Review and respond. For outbound reply, the AI will create an approval
file in `Vault/Pending_Approval/`.
```

---

## Entity: InboundMessage (WhatsApp)

File path: `Vault/Inbox/WHATSAPP_<sanitized-id>.md`
Moved to: `Vault/Needs_Action/<timestamp>-WHATSAPP_<sanitized-id>.md` by fte-watcher

```yaml
---
type: whatsapp_message
source: whatsapp
status: unprocessed
message_id: "<whatsapp-message-id-serialized>"
from_jid: "447911123456@c.us"
from_display: "John Smith"
chat_type: private              # private | group
group_name: null                # group name if chat_type=group
timestamp_unix: 1709041920
timestamp_iso: "2026-02-27T14:32:00Z"
body_preview: "Need help with the invoice urgently"
keywords_matched:
  - help
  - invoice
  - urgent
has_media: false
priority: high                  # high if urgent|asap in keywords_matched; else normal
requires_action: true
---

# WhatsApp Message — Requires Action

**From**: John Smith (`447911123456@c.us`)
**Time**: 2026-02-27T14:32:00Z
**Keywords**: help, invoice, urgent

## Message

<full message text here>

## Required Action

Review and respond. For outbound reply, the AI will create an approval
file in `Vault/Pending_Approval/`.
```

---

## Entity: ApprovalRequest (Email Reply)

File path: `Vault/Pending_Approval/EMAIL_REPLY_<message-id>_<timestamp>.md`

```yaml
---
action_type: send_email
source_task: "Needs_Action/2026-02-27-143200-EMAIL_abc123.md"
to: "sender@example.com"
to_name: "John Smith"
subject: "Re: Project Timeline"
thread_id: "<gmail-thread-id>"
proposed_reply: |
  Hi John,

  Thank you for the update on the project timeline...
created_at: "2026-02-27T14:35:00Z"
expiry_at: "2026-02-28T14:35:00Z"
status: pending
flags: []                       # e.g. ["unknown_sender", "requires_human_review"]
---

# Email Reply — Awaiting Approval

**To**: John Smith (`sender@example.com`)
**Subject**: Re: Project Timeline

## Proposed Reply

Hi John,

Thank you for the update on the project timeline...

---

**To Approve**: Move this file to `Vault/Approved/`
**To Reject**: Move this file to `Vault/Rejected/`
**Expires**: 2026-02-28T14:35:00Z (auto-rejected after this time)
```

---

## Entity: ApprovalRequest (WhatsApp Reply)

File path: `Vault/Pending_Approval/WHATSAPP_REPLY_<id>_<timestamp>.md`

```yaml
---
action_type: send_whatsapp
source_task: "Needs_Action/2026-02-27-143200-WHATSAPP_xyz789.md"
to_jid: "447911123456@c.us"
to_display: "John Smith"
proposed_reply: "Hi John, I'll send the invoice over shortly."
created_at: "2026-02-27T14:35:00Z"
expiry_at: "2026-02-28T14:35:00Z"
status: pending
---

# WhatsApp Reply — Awaiting Approval

**To**: John Smith (`447911123456@c.us`)

## Proposed Reply

Hi John, I'll send the invoice over shortly.

---

**To Approve**: Move this file to `Vault/Approved/`
**To Reject**: Move this file to `Vault/Rejected/`
```

---

## Entity: ApprovalRequest (Calendar Event)

File path: `Vault/Pending_Approval/CALENDAR_<slug>_<timestamp>.md`

```yaml
---
action_type: create_calendar_event
source_task: "Needs_Action/2026-02-27-143200-EMAIL_abc123.md"
event_title: "Project Timeline Review"
event_date: "2026-03-03"
event_time_start: "15:00"
event_time_end: "16:00"
event_timezone: "Asia/Karachi"
attendees:
  - "sender@example.com"
event_description: "Discussion of revised project timeline following client request."
created_at: "2026-02-27T14:35:00Z"
expiry_at: "2026-02-28T14:35:00Z"
status: pending
---

# Calendar Event — Awaiting Approval

**Event**: Project Timeline Review
**When**: 2026-03-03, 15:00–16:00 Asia/Karachi
**Attendees**: sender@example.com

## Description

Discussion of revised project timeline following client request.

---

**To Approve**: Move this file to `Vault/Approved/`
**To Reject**: Move this file to `Vault/Rejected/`
```

---

## Entity: ApprovalRequest (LinkedIn Post)

File path: `Vault/Pending_Approval/LINKEDIN_<slug>_<timestamp>.md`

```yaml
---
action_type: publish_linkedin_post
source_task: "Needs_Action/2026-02-27-143200-TASK_linkedin-q1.md"
proposed_post: |
  🚀 Q1 2026 in review: We helped 12 clients streamline their operations...

  Key wins this quarter:
  • Automated 3 manual workflows, saving 15+ hours/week
  • Delivered 2 projects ahead of schedule

  What's your biggest operational challenge in 2026? Let's connect.

  #BusinessAutomation #AI #Productivity
character_count: 347
max_character_count: 3000
created_at: "2026-02-27T14:35:00Z"
expiry_at: "2026-02-28T14:35:00Z"
status: pending
---

# LinkedIn Post — Awaiting Approval

**Characters**: 347 / 3000

## Proposed Post

🚀 Q1 2026 in review: We helped 12 clients streamline their operations...

---

**To Approve**: Move this file to `Vault/Approved/`
**To Reject**: Move this file to `Vault/Rejected/`
```

---

## Entity: WatcherState (Gmail)

File path: `~/.config/fte/gmail_watcher_state.json`

```json
{
  "last_poll": "2026-02-27T14:32:00Z",
  "processed_ids": [
    "18d5a1b2c3d4e5f6",
    "18d5a1b2c3d4e5f7"
  ],
  "processed_ids_max": 10000,
  "schema_version": "1"
}
```

`processed_ids` is a FIFO window capped at `processed_ids_max`. Written atomically via temp file + rename.

---

## Entity: WatcherState (WhatsApp)

File path: `/var/lib/fte/whatsapp-session/watcher-state.json`

```json
{
  "processed_ids": [
    "3EB0A1B2C3D4E5F6_447911123456@c.us",
    "3EB0A1B2C3D4E5F7_447911123456@c.us"
  ],
  "processed_ids_max": 2000,
  "schema_version": "1"
}
```

---

## Entity: LinkedInToken

File path: `~/.config/fte/linkedin_token.json` (chmod 600)

```json
{
  "access_token": "AQV...",
  "refresh_token": "AQV...",
  "expires_at": "2026-04-28T10:30:00Z",
  "refresh_token_expires_at": "2027-02-27T10:30:00Z",
  "scope": "r_liteprofile w_member_social openid profile email",
  "token_type": "Bearer",
  "linkedin_user_id": "urn:li:person:abc123",
  "created_at": "2026-02-27T10:30:00Z",
  "updated_at": "2026-02-27T10:30:00Z"
}
```

Refresh token rotation: every refresh call returns a new `refresh_token` — always overwrite both tokens.

---

## Vault Folder Structure (Silver Extension)

```
Vault/
├── Inbox/              # Raw inbound files from watchers (Bronze)
├── Needs_Action/       # Timestamped task files (Bronze)
├── Plans/              # Claude's reasoning plans (Bronze)
├── In_Progress/        # Tasks being worked on (Bronze)
├── Done/               # Completed tasks (Bronze)
├── Logs/               # Structured JSON action logs (Bronze)
├── Pending_Approval/   # Proposed actions awaiting human review (Silver — already in REQUIRED_DIRS)
├── Approved/           # Human-approved actions ready for execution (Silver — already in REQUIRED_DIRS)
└── Rejected/           # Rejected or expired actions (Silver — already in REQUIRED_DIRS)
```

Note: `Pending_Approval/`, `Approved/`, `Rejected/` are already present in `vault.py`'s `REQUIRED_DIRS`. Any Bronze-initialized vault already has them. **No migration needed.**

---

## Log Entry Schema (extended for Silver)

Extends the existing Bronze JSON log format in `Vault/Logs/YYYY-MM-DD.json`:

```json
{
  "timestamp": "2026-02-27T14:35:00Z",
  "action_type": "send_email",
  "actor": "fte-action-executor",
  "source_task": "Needs_Action/2026-02-27-143200-EMAIL_abc123.md",
  "approved_file": "Approved/EMAIL_REPLY_abc123_20260227-143500.md",
  "approval_status": "approved",
  "approved_at": "2026-02-27T14:37:00Z",
  "target": "sender@example.com",
  "result": "success",
  "duration_ms": 1240
}
```

Additional fields for Silver: `source_task`, `approved_file`, `approval_status`, `approved_at`.
