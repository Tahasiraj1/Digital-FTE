---
name: gmail-watcher
description: Extract structured metadata from a raw email message and write a correctly formatted EMAIL_*.md task file to Vault/Inbox/
version: "1.0"
author: fte-agent
---

# Gmail Watcher Skill

## Purpose

Parse a raw Gmail email message (headers + body) and write a correctly formatted `EMAIL_<message-id>.md` task file to `Vault/Inbox/`.

## Input Format

Provide the following fields:
- `message_id`: Gmail message ID
- `thread_id`: Gmail thread ID
- `from`: Sender email address (full "Name <email>" format)
- `subject`: Email subject line
- `received`: ISO 8601 timestamp of receipt
- `labels`: List of Gmail label strings (e.g., ["INBOX", "IMPORTANT"])
- `body_text`: Plain text email body

## Output

Write one file to `Vault/Inbox/EMAIL_<message-id>.md` with this exact frontmatter:

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
priority: high              # high = IMPORTANT label OR STARRED; else normal
has_attachments: false
labels: ["INBOX", "IMPORTANT"]
flags: []                   # add "unknown_sender" if sender has no display name
---

# Email — Requires Action

**From**: John Smith (`sender@example.com`)
**Subject**: Re: Project Timeline
**Received**: 2026-02-27T14:32:00Z

## Message Body

<full email text>

## Required Action

Review and respond. For outbound reply, the AI will create an approval
file in `Vault/Pending_Approval/`.
```

## Rules

- Set `priority: high` if labels include `IMPORTANT` or `STARRED`
- Add `"unknown_sender"` to flags if sender has no display name
- Do NOT write the file if it already exists (check before writing)
- Filename: `EMAIL_<message-id>.md` — use the message_id exactly

## Example

**Input**:
```
message_id: 18d5a1b2c3d4e5f6
from: "John Smith <john@example.com>"
subject: Invoice Request
received: 2026-02-27T14:32:00Z
labels: ["INBOX", "IMPORTANT"]
body_text: Hi, can you send me the February invoice?
```

**Output**: Write `Vault/Inbox/EMAIL_18d5a1b2c3d4e5f6.md` with the schema above filled in.
