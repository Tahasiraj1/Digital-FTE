# Social Post Skill

Draft Facebook and Instagram post approval requests from a `social_post_chain` task file.

## Input

A task file in `Needs_Action/` with:
- `type: social_post_chain`
- `ralph_loop: true` (optional)
- Post content in the body
- Optional: `platforms: [facebook, instagram]` (defaults to both)

## Output

Write TWO files to `Vault/Pending_Approval/` (unless platforms specifies only one):

1. `SOCIAL_facebook_<YYYYMMDD-HHMMSS>.md`
2. `SOCIAL_instagram_<YYYYMMDD-HHMMSS>.md`

## Platform-Specific Content

### Facebook
- Up to 63,206 characters
- Richer, more detailed content
- Can include links and longer narratives
- Include hashtags at the end

### Instagram
- Max 2,200 characters
- Hashtag-heavy (3-5 hashtags)
- More visual/emotional tone
- If image_required is true for the task, set `image_required: true` and `image_path: null`

## Frontmatter Schema (per platform)

```yaml
---
action_type: publish_facebook_post  # or publish_instagram_post
source_task: "<filename of the task file>"
ralph_loop_id: "<loop_id if present in source>"
platform: facebook  # or instagram
session_name: facebook  # or instagram
post_text: |
  <platform-specific post content>
hashtags: ["#tag1", "#tag2"]
image_path: null  # or local path if provided
image_required: false  # true for IG if image needed
created_at: "<ISO8601>"
expiry_at: "<ISO8601, 24h from now>"
status: pending
flags: []
---
```

## Rules

- Draft BOTH platform versions from the same source content
- Adapt tone and length per platform
- After writing both approval files, output `<promise>AWAITING_APPROVAL</promise>` as the LAST line
- If `ralph_loop_id` is present in the source task, include it in both approval files
