---
name: whatsapp-watcher
description: Parse a WhatsApp message object and write a correctly formatted WHATSAPP_*.md task file to Vault/Inbox/
version: "1.0"
author: fte-agent
---

# WhatsApp Watcher Skill

## Purpose

Parse a WhatsApp message object and write a `WHATSAPP_<sanitized-id>.md` task file to `Vault/Inbox/`.

## Input Format

Provide the following fields:
- `message_id`: WhatsApp message ID (serialized)
- `from_jid`: Sender JID (e.g., `447911123456@c.us`)
- `from_display`: Sender display name
- `body`: Message text
- `timestamp_unix`: Unix timestamp
- `keywords_matched`: List of matched keywords

## Output

Write one file to `Vault/Inbox/WHATSAPP_<sanitized-id>.md` with this exact frontmatter:

```yaml
---
type: whatsapp_message
source: whatsapp
status: unprocessed
message_id: "<sanitized-message-id>"
from_jid: "447911123456@c.us"
from_display: "John Smith"
chat_type: private              # private | group
group_name: null
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

<full message text>

## Required Action

Review and respond. For outbound reply, the AI will create an approval
file in `Vault/Pending_Approval/`.
```

## Rules

- Sanitize message_id for filename: replace non-alphanumeric with `_`, cap at 64 chars
- Set `priority: high` if `urgent` or `asap` in keywords_matched
- `body_preview` is the first 100 chars of the message body (newlines replaced with space)
- Do NOT write the file if it already exists

## Example

**Input**:
```json
{
  "message_id": "3EB0A1B2C3D4E5F6_447911123456@c.us",
  "from_jid": "447911123456@c.us",
  "from_display": "John Smith",
  "body": "Invoice payment is urgent, need help",
  "timestamp_unix": 1709041920,
  "keywords_matched": ["invoice", "urgent", "help"]
}
```

**Output**: Write `Vault/Inbox/WHATSAPP_3EB0A1B2C3D4E5F6_447911123456_c_us.md`
