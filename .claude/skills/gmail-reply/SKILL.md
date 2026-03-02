---
name: gmail-reply
description: Read an email task file from Needs_Action/ and draft a contextually appropriate professional reply, writing an approval request to Pending_Approval/
version: "1.0"
author: fte-agent
---

# Gmail Reply Skill

## Purpose

Read one or more email task files from `Vault/Needs_Action/` and draft a professional, concise reply for each. Write the result as an `EMAIL_REPLY_*.md` approval request file to `Vault/Pending_Approval/`.

## Input

Email task files in `Vault/Needs_Action/` with `type: email` in frontmatter.

Read each file fully. Key fields:
- `message_id`: For referencing in reply
- `thread_id`: For Gmail threading
- `from`: Sender address
- `from_name`: Sender display name
- `subject`: Email subject
- Body text after the `## Message Body` heading

Also read `Vault/Company_Handbook.md` for business context and rules.

## Output

For each email task file, write one file to `Vault/Pending_Approval/`:

**Filename**: `EMAIL_REPLY_<message_id>_<YYYYMMDD-HHMMSS>.md`

```yaml
---
action_type: send_email
source_task: "Needs_Action/<filename>"
to: "sender@example.com"
to_name: "John Smith"
subject: "Re: Project Timeline"
thread_id: "<thread_id>"
proposed_reply: |
  Hi John,

  Thank you for reaching out. [Your reply here]

  Best regards,
  [Business Name]
created_at: "<ISO8601 now>"
expiry_at: "<ISO8601 24h from now>"
status: pending
flags: []
---

# Email Reply — Awaiting Approval

**To**: John Smith (`sender@example.com`)
**Subject**: Re: Project Timeline

## Proposed Reply

Hi John,

[reply text]

---

**To Approve**: Move this file to `Vault/Approved/`
**To Reject**: Move this file to `Vault/Rejected/`
**Expires**: <expiry_at>
```

## Rules

1. **Tone**: Professional, concise, no filler phrases ("I hope this email finds you well")
2. **Length**: Keep replies to 3-5 sentences unless the email requires a detailed response
3. **Unknown sender**: Add `"unknown_sender"` to `flags` if `from_name` == `from` (no display name)
4. **Financial commitments**: Add `"requires_human_review"` to `flags` if reply mentions pricing or payment terms
5. **Expiry**: Always set `expiry_at` to exactly 24 hours from `created_at`
6. **Thread**: Always include `thread_id` so Gmail API threads the reply correctly
7. **Subject**: Prefix with "Re: " unless it already starts with "Re:"

## Example

**Input file** (`Needs_Action/20260227-143200-EMAIL_abc123.md`):
- from: "john@example.com", from_name: "John Smith"
- subject: "Invoice Request"
- body: "Hi, can you send me the February invoice?"

**Output** (`Pending_Approval/EMAIL_REPLY_abc123_20260227-143500.md`):
- proposed_reply: "Hi John,\n\nThank you for your message. I'll prepare the February invoice and send it over within 24 hours.\n\nBest regards,\n[Business Name]"
- flags: [] (known sender, no financial commitment)
