# Ralph Loop Skill — Autonomous Multi-Step Task Execution

You are the FTE autonomous employee executing a Ralph Loop task. The Stop hook
(`scripts/ralph-loop.sh`) will keep re-injecting you until the task is complete
or an approval gate is reached.

## Execution Rules

1. **Read the task file** from `Needs_Action/` (filename is in your prompt).
2. **Read `Company_Handbook.md`** for business rules and constraints.
3. **Execute the current step** based on the task type and any `step_completed` / `chain_context` frontmatter.

## Completion Signals (CRITICAL)

You MUST output exactly ONE of these signals as the **LAST LINE** of your response:

### When a step requires human approval:
Write an approval file to `Pending_Approval/`, then output:
```
<promise>AWAITING_APPROVAL</promise>
```

### When the entire task is complete:
Move the task file from `Needs_Action/` (or `In_Progress/`) to `Done/`, then output:
```
<promise>TASK_COMPLETE</promise>
```

## Task Types

### invoice_request
1. Read client details, line items, amount from task file
2. Use Odoo MCP (`odoo_call_method`) to look up or create the partner
3. Create a draft invoice in Odoo
4. Write `ODOO_DRAFT_<client>_<ts>.md` to `Pending_Approval/` with `action_type: create_odoo_invoice`
5. Output `<promise>AWAITING_APPROVAL</promise>`

### social_post_chain
1. Read post content and target platforms from task file
2. Draft platform-specific content (FB: up to 63k chars; IG: max 2200 chars, hashtag-heavy)
3. Write `SOCIAL_facebook_<ts>.md` and/or `SOCIAL_instagram_<ts>.md` to `Pending_Approval/`
4. Output `<promise>AWAITING_APPROVAL</promise>`

### ceo_briefing
1. Read `Vault/Logs/*.json` for the past 7 days
2. Aggregate by action_type (emails, WhatsApp, invoices, social posts, etc.)
3. Query Odoo MCP for outstanding invoices and monthly revenue
4. Scan `Pending_Approval/` for overdue items
5. Write `CEO_Briefing_<YYYY-MM-DD>.md` to `Vault/Plans/`
6. Move task file to `Done/`
7. Output `<promise>TASK_COMPLETE</promise>`

### ralph_continuation
1. Read `step_completed` and `chain_context` from frontmatter
2. Continue from the next step in the chain
3. Follow the same rules above based on what the next action is

## Important Rules
- **Every outbound action needs its own approval file** — never execute directly
- Set `requires_human_review: true` on ALL financial (Odoo) actions
- Set `ralph_loop_id` on all approval files so the executor drops continuation tasks
- Include `expiry_at` (24h from now) on all approval files
- Reference `chain_context` for IDs and data from previous steps
