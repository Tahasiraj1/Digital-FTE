---
name: linkedin-post
description: Draft a professional LinkedIn post for business visibility and sales generation (max 3000 chars, 3-5 hashtags, call-to-action), writing an approval request to Pending_Approval/
version: "1.0"
author: fte-agent
---

# LinkedIn Post Skill

## Purpose

Read a task file with a LinkedIn post topic/context and draft a professional, engaging post for business visibility and sales generation. Write the result as a `LINKEDIN_*.md` approval request to `Vault/Pending_Approval/`.

## Input

Task files in `Vault/Needs_Action/` with `type: linkedin` or `type: linkedin_post` in frontmatter, or any task file containing LinkedIn post instructions.

Read the task file and also reference `Vault/Company_Handbook.md` for business context.

## Output

Write one file to `Vault/Pending_Approval/`:

**Filename**: `LINKEDIN_<slug>_<YYYYMMDD-HHMMSS>.md`
(slug = 3-5 words from post topic, lowercase, hyphenated)

```yaml
---
action_type: publish_linkedin_post
source_task: "Needs_Action/<filename>"
proposed_post: |
  🚀 [Opening hook — bold statement or question]

  [2-3 paragraphs of substance — insights, results, or value]

  Key points:
  • [Point 1]
  • [Point 2]
  • [Point 3]

  [Call-to-action — question or invitation to connect]

  #Hashtag1 #Hashtag2 #Hashtag3 #Hashtag4 #Hashtag5
character_count: <integer>
max_character_count: 3000
created_at: "<ISO8601 now>"
expiry_at: "<ISO8601 24h from now>"
status: pending
flags: []
---

# LinkedIn Post — Awaiting Approval

**Characters**: <count> / 3000

## Proposed Post

[post content]

---

**To Approve**: Move this file to `Vault/Approved/`
**To Reject**: Move this file to `Vault/Rejected/`
```

## Writing Rules

1. **Hook**: Start with a bold statement, surprising fact, or rhetorical question
2. **Structure**: Hook → Context/Story → Key insights (bullet points) → Call-to-action
3. **Length**: 150-400 words is optimal. MUST be under 3,000 characters
4. **Hashtags**: 3-5 relevant hashtags at the end (industry-specific + general)
5. **Call-to-action**: End with a question or invitation ("What's your experience?", "Let's connect")
6. **Tone**: Professional but conversational — like a thoughtful peer, not a corporate press release
7. **No financial commitments**: If post mentions pricing or revenue figures, add `"requires_human_review"` to `flags`
8. **Character count**: Count ALL characters including spaces, newlines, emojis (emoji = 2 chars)
9. **Over-limit**: If draft exceeds 3,000 chars, add `"requires_human_review"` to `flags` and truncate with a note

## Example

**Input task**: "Write a LinkedIn post about our Q1 2026 AI automation results"

**Output post**:
```
🤖 AI automation saved our clients 15+ hours/week in Q1 2026.

Here's what we learned building AI employees for small businesses:

The biggest blocker isn't technology — it's trust. Business owners need to stay in control.

Our approach: every AI action goes through human approval before execution. Results:
• 12 clients onboarded
• 3 manual workflows automated
• 0 unauthorized actions (human-in-the-loop works)

What's your biggest concern about AI automation in your business?

#AIAutomation #SmallBusiness #Productivity #AI #BusinessGrowth
```
