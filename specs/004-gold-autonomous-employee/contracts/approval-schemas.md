# Approval File Schemas — Gold Tier

All approval files live in `Vault/Pending_Approval/`. These schemas define the frontmatter fields that Claude writes and the executor reads.

---

## create_odoo_invoice

**Filename**: `ODOO_DRAFT_<client_slug>_<YYYYMMDD-HHMMSS>.md`

```yaml
---
action_type: create_odoo_invoice
source_task: "INVOICE_REQUEST_abc123_20260303.md"
ralph_loop_id: "ralph-20260303-abc123"   # omit if not in a chain
client_name: "Acme Corp"
client_email: "billing@acme.com"
line_items:
  - description: "AI Consulting — March 2026"
    quantity: 5
    unit_price: 100.00
currency: "USD"
due_date: "2026-03-31"
amount_total: 500.00
requires_human_review: true
created_at: "2026-03-03T10:00:00Z"
expiry_at: "2026-03-04T10:00:00Z"
status: pending
flags: []
---
```

**Executor action**: Calls Odoo JSON-RPC `account.move.create` and stores returned `invoice_id` in log. Does NOT confirm — user must approve a separate `confirm_odoo_invoice` request.

---

## confirm_odoo_invoice

**Filename**: `ODOO_CONFIRM_<odoo_id>_<YYYYMMDD-HHMMSS>.md`

```yaml
---
action_type: confirm_odoo_invoice
source_task: "INVOICE_REQUEST_abc123_20260303.md"
ralph_loop_id: "ralph-20260303-abc123"
odoo_invoice_id: 42
client_name: "Acme Corp"
client_email: "billing@acme.com"
amount_total: 500.00
invoice_number: "INV/2026/00042"   # filled after draft creation
requires_human_review: true
created_at: "2026-03-03T10:01:00Z"
expiry_at: "2026-03-04T10:01:00Z"
status: pending
flags: []
---
```

**Executor action**: Calls `action_post` on `account.move`, then triggers Odoo's built-in invoice email send. Drops continuation task if `ralph_loop_id` is set.

---

## publish_facebook_post

**Filename**: `SOCIAL_facebook_<YYYYMMDD-HHMMSS>.md`

```yaml
---
action_type: publish_facebook_post
source_task: "SOCIAL_POST_CHAIN_20260303.md"
ralph_loop_id: "ralph-20260303-xyz789"   # omit if standalone
platform: facebook
session_name: facebook
post_text: |
  Excited to announce we just closed a new AI consulting deal! 🚀

  If you're looking to integrate AI into your business workflows, let's talk.
hashtags: ["#AI", "#Consulting", "#BusinessGrowth"]
image_path: null
image_required: false
created_at: "2026-03-03T11:00:00Z"
expiry_at: "2026-03-04T11:00:00Z"
status: pending
flags: []
---
```

**Executor action**: Invokes `agent-browser --session-name facebook` subprocess to navigate to Facebook and publish the post. Creates system alert if session expired.

---

## publish_instagram_post

**Filename**: `SOCIAL_instagram_<YYYYMMDD-HHMMSS>.md`

```yaml
---
action_type: publish_instagram_post
source_task: "SOCIAL_POST_CHAIN_20260303.md"
ralph_loop_id: "ralph-20260303-xyz789"
platform: instagram
session_name: instagram
post_text: "Closed a new AI deal! DM me if you want to automate your business. 🤖"
hashtags: ["#AI", "#Automation", "#Pakistan"]
image_path: "/mnt/d/AI_Employee_Vault/Assets/deal-win.jpg"
image_required: true
created_at: "2026-03-03T11:00:00Z"
expiry_at: "2026-03-04T11:00:00Z"
status: pending
flags: ["image_required"]
---
```

**Executor action**: Invokes `agent-browser --session-name instagram` subprocess. If `image_required: true` and `image_path: null`, executor moves file to `Pending_Approval/` with `flags: ["image_required"]` and does NOT dispatch.

---

## Ralph Loop Continuation Task

**Filename**: `CONTINUATION_<original_task>_<YYYYMMDD-HHMMSS>.md`

```yaml
---
type: ralph_continuation
ralph_loop: true
ralph_loop_id: "ralph-20260303-abc123"
original_task: "INVOICE_REQUEST_abc123_20260303.md"
step_completed: "confirm_odoo_invoice"
next_hint: "Invoice confirmed. Next: draft thank-you email to client."
created_at: "2026-03-03T10:05:00Z"
---

# Task Continuation

Step `confirm_odoo_invoice` completed for invoice INV/2026/00042.

Next action in the chain: draft and send a thank-you email to billing@acme.com.

Check `Vault/Logs/` for confirmation of the invoice send, then proceed with the email step.
```

---

## System Alert Files

**Filename**: `SYSTEM_<alert-type>.md`

### SYSTEM_ralph-loop-timeout.md
```yaml
---
type: system_alert
alert_type: ralph_loop_timeout
loop_id: "ralph-20260303-abc123"
task_file: "INVOICE_REQUEST_abc123_20260303.md"
iterations_reached: 10
created_at: "2026-03-03T10:30:00Z"
---

# Ralph Loop Timeout

The autonomous loop for task `INVOICE_REQUEST_abc123_20260303.md` reached the maximum iteration limit (10) without completing.

**Action required**: Review the task and restart the loop manually, or resolve the blocking step.
```

### SYSTEM_social-session-expired.md
```yaml
---
type: system_alert
alert_type: social_session_expired
platform: facebook
created_at: "2026-03-03T11:05:00Z"
---

# Social Session Expired

The Facebook browser session has been invalidated by the platform. Social posting is paused until re-authentication.

**Action required**: Run `agent-browser --session-name facebook open facebook.com` and log in manually to restore the session.
```

### SYSTEM_odoo-unreachable.md
```yaml
---
type: system_alert
alert_type: odoo_unreachable
attempted_action: confirm_odoo_invoice
created_at: "2026-03-03T10:02:00Z"
---

# Odoo Unreachable

Could not connect to Odoo at `http://localhost:8069`. The action `confirm_odoo_invoice` was not dispatched.

**Action required**: Start Odoo with `docker compose -f deploy/docker-compose.odoo.yml up -d` and retry.
```
