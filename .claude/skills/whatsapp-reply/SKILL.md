---
name: whatsapp-reply
description: Read a WhatsApp task file and draft a short conversational reply (max 500 chars) appropriate for WhatsApp, writing an approval request to Pending_Approval/
version: "1.0"
author: fte-agent
---

# WhatsApp Reply Skill

## Purpose

Read a WhatsApp task file from `Vault/Needs_Action/` and draft a short, conversational reply appropriate for WhatsApp messaging. Write the result as a `WHATSAPP_REPLY_*.md` approval request to `Vault/Pending_Approval/`.

## Input

WhatsApp task files in `Vault/Needs_Action/` with `type: whatsapp_message` in frontmatter.

Read each file fully. Key fields:
- `from_jid`: Sender JID (needed for reply routing)
- `from_display`: Sender display name
- `body_preview`: Message preview
- Full message body after `## Message` heading
- `keywords_matched`: Keywords that triggered the watcher

Also read `Vault/Company_Handbook.md` for business context.

## Output

For each WhatsApp task file, write one file to `Vault/Pending_Approval/`:

**Filename**: `WHATSAPP_REPLY_<sanitized_id>_<YYYYMMDD-HHMMSS>.md`

```yaml
---
action_type: send_whatsapp
source_task: "Needs_Action/<filename>"
to_jid: "447911123456@c.us"
to_display: "John Smith"
proposed_reply: "Hi John! I'll get that invoice sorted for you right away."
created_at: "<ISO8601 now>"
expiry_at: "<ISO8601 24h from now>"
status: pending
---

# WhatsApp Reply — Awaiting Approval

**To**: John Smith (`447911123456@c.us`)

## Proposed Reply

Hi John! I'll get that invoice sorted for you right away.

---

**To Approve**: Move this file to `Vault/Approved/`
**To Reject**: Move this file to `Vault/Rejected/`
```

## Rules

1. **Length**: MUST be under 500 characters — WhatsApp norm is brief and conversational
2. **Tone**: Friendly but professional — like a quick text message, not a formal email
3. **No signatures**: WhatsApp replies don't need "Best regards" signatures
4. **Expiry**: Set `expiry_at` to 24 hours from `created_at`
5. **JID**: Copy `from_jid` exactly from the source task — it's the routing address
6. **Single line preferred**: Keep `proposed_reply` to 1-2 short sentences

## Example

**Input** (`Needs_Action/20260227-143200-WHATSAPP_3EB0A1.md`):
- from_jid: "447911123456@c.us", from_display: "John"
- body: "Invoice payment is urgent, can you help?"

**Output** (`Pending_Approval/WHATSAPP_REPLY_3EB0A1_20260227-143500.md`):
- proposed_reply: "Hi John! I'll sort out the invoice payment urgently and get back to you within the hour."
- (84 chars — well under 500 limit)
