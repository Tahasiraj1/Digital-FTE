# Social Metrics Skill

Collect social engagement summary from Facebook and Instagram for the past 7 days.

## Input

A task file in `Needs_Action/` with `type: social_metrics_request`.

## Process

1. Use `agent-browser --session-name facebook` to navigate to published posts' insights pages
2. Collect: likes, comments, reach for each post in the past 7 days
3. Repeat for Instagram with `agent-browser --session-name instagram`
4. Aggregate totals per platform

## Output

Write `SOCIAL_METRICS_<YYYY-MM-DD>.md` to `Vault/Plans/` with:

```markdown
# Social Engagement Report — YYYY-MM-DD

## Facebook (Past 7 Days)
| Post | Likes | Comments | Reach |
|------|-------|----------|-------|
| ...  | ...   | ...      | ...   |
**Totals**: X likes, Y comments, Z reach

## Instagram (Past 7 Days)
| Post | Likes | Comments | Reach |
|------|-------|----------|-------|
| ...  | ...   | ...      | ...   |
**Totals**: X likes, Y comments, Z reach
```

## Completion

This is a **read-only** operation — NO approval gate needed.
1. Write the metrics report to `Vault/Plans/`
2. Move task file to `Done/`
3. Output `<promise>TASK_COMPLETE</promise>` as the LAST line
