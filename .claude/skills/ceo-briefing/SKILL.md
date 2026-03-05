# CEO Briefing Skill

Generate a comprehensive weekly business audit report from vault logs and Odoo data.

## Input

A task file in `Needs_Action/` with `type: ceo_briefing` and `ralph_loop: true`.

## Process

1. **Read vault logs**: Scan `Vault/Logs/*.json` for the past 7 days
2. **Aggregate by action_type**:
   - `send_email` → Emails Handled count
   - `send_whatsapp` → WhatsApp Replies count
   - `create_calendar_event` → Calendar Events count
   - `publish_linkedin_post` → LinkedIn Posts count
   - `create_odoo_invoice` / `confirm_odoo_invoice` → Odoo Activity
   - `publish_facebook_post` / `publish_instagram_post` → Social Posts
3. **Query Odoo MCP** (if available):
   - Outstanding invoices: `odoo_call_method(model="account.move", method="search_read", ...)`
   - Monthly revenue: `odoo_call_method(model="account.move", method="read_group", ...)`
4. **Scan Pending_Approval/** for overdue items (past expiry_at)
5. **Count** items in `In_Progress/` and `Needs_Action/`

## Output

Write `CEO_Briefing_<YYYY-MM-DD>.md` to `Vault/Plans/` with these sections:

```markdown
# CEO Briefing — Week Ending YYYY-MM-DD

## Action Required
- [List overdue pending approvals]
- [List SYSTEM_ alerts in Needs_Action/]
- [List items in In_Progress/ > 48h old]

## Emails Handled
- Total: N emails processed
- Approved: N | Rejected: N

## WhatsApp Replies
- Total: N replies sent

## Calendar Events
- Total: N events created

## LinkedIn Posts
- Total: N posts published

## Odoo Activity
- Invoices Created: N
- Invoices Confirmed: N
- Outstanding: $X (N invoices)
- Monthly Revenue: $X

## Social Posts
- Facebook: N posts
- Instagram: N posts

## Pending Tasks
- In Progress: N
- Needs Action: N
```

## Completion

1. Write the briefing report to `Vault/Plans/`
2. Move the task file from `Needs_Action/` to `Done/`
3. Output `<promise>TASK_COMPLETE</promise>` as the LAST line

This is a fully autonomous task — NO approval gate needed.
