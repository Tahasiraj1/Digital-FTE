# Odoo Invoice Skill

Draft an Odoo invoice approval request from an `invoice_request` task file.

## Input

A task file in `Needs_Action/` with frontmatter containing:
- `type: invoice_request`
- Client details (name, email) in the body
- Line items (description, quantity, unit_price) in the body
- Optional: `ralph_loop_id`, `ralph_loop: true`

## Output

Write EXACTLY ONE file to `Vault/Pending_Approval/` with filename pattern:
`ODOO_DRAFT_<client_slug>_<YYYYMMDD-HHMMSS>.md`

## Frontmatter Schema

```yaml
---
action_type: create_odoo_invoice
source_task: "<filename of the task file>"
ralph_loop_id: "<loop_id if present in source>"
client_name: "<extracted client name>"
client_email: "<extracted client email>"
line_items:
  - description: "<service description>"
    quantity: <number>
    unit_price: <number>
currency: "USD"
due_date: "<YYYY-MM-DD, 30 days from now>"
amount_total: <calculated total>
requires_human_review: true
created_at: "<ISO8601>"
expiry_at: "<ISO8601, 24h from now>"
status: pending
flags: []
---
```

## Rules

- `requires_human_review` MUST always be `true` for Odoo financial actions
- Calculate `amount_total` from line_items (sum of quantity × unit_price)
- If `ralph_loop_id` is present in the source task, include it in the approval file
- If client details are ambiguous, include `requires_human_review` flag
- After writing the approval file, output `<promise>AWAITING_APPROVAL</promise>` as the LAST line
