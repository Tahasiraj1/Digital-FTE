# Data Model: Gold Tier — Autonomous Employee

**Date**: 2026-03-03 | **Branch**: `004-gold-autonomous-employee`

---

## Entities

### 1. RalphLoopState

Persisted at `Vault/ralph_state.json`. Single active state file — only one loop runs at a time per orchestrator instance.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `loop_id` | string | ✅ | Unique ID: `ralph-<YYYYMMDD>-<random6>` |
| `task_file` | string | ✅ | Filename of the originating task in `Needs_Action/` (e.g., `INVOICE_REQUEST_abc123_20260303.md`) |
| `task_name` | string | ✅ | Same as `task_file` basename (for Done/ check) |
| `iteration` | int | ✅ | Current iteration count (0-indexed) |
| `max_iterations` | int | ✅ | Default: 10 (from env `RALPH_MAX_ITERATIONS`) |
| `continuation_prompt` | string | ✅ | Prompt re-injected on next iteration |
| `started_at` | ISO8601 | ✅ | Loop start timestamp |
| `chain_step` | int | ✅ | Current step within cross-domain chain (0-indexed) |
| `chain_cap` | int | ✅ | Max downstream actions (default: 3) |

**State transitions**:
- Created: when orchestrator detects `ralph_loop: true` task and starts `claude -p`
- Updated: on each iteration (increment `iteration`, update `continuation_prompt`)
- Deleted: when loop exits cleanly (task complete, approval gate, or timeout)

---

### 2. RalphLoopTask (task file in `Needs_Action/`)

A task file tagged for Ralph Loop processing. Extends the standard Silver task file schema.

| Frontmatter Field | Type | Required | Description |
|-------------------|------|----------|-------------|
| `type` | string | ✅ | e.g., `invoice_request`, `social_post_chain`, `ralph_continuation`, `ceo_briefing` |
| `ralph_loop` | bool | ✅ | `true` — signals orchestrator to use Ralph Loop routing |
| `ralph_loop_id` | string | ❌ | Set only for continuation tasks; links back to originating loop |
| `step_completed` | string | ❌ | Continuation only: which action was just dispatched |
| `original_task` | string | ❌ | Continuation only: filename of the chain's originating task |
| `created_at` | ISO8601 | ✅ | |
| `chain_context` | object | ❌ | Arbitrary key-value context passed between chain steps |

---

### 3. OdooApprovalRequest (approval file in `Pending_Approval/`)

Extends standard Silver approval file schema.

**File naming**: `ODOO_<action>_<odoo_id>_<YYYYMMDD-HHMMSS>.md`

| Frontmatter Field | Type | Required | Description |
|-------------------|------|----------|-------------|
| `action_type` | string | ✅ | `create_odoo_invoice` or `confirm_odoo_invoice` |
| `ralph_loop_id` | string | ❌ | Present when part of a Ralph Loop chain — triggers continuation task after dispatch |
| `odoo_invoice_id` | int | ❌ | Odoo record ID (set for `confirm_odoo_invoice`) |
| `client_name` | string | ✅ | |
| `client_email` | string | ✅ | |
| `amount_total` | float | ✅ | Invoice total in local currency |
| `line_items` | list | ✅ | `[{description, quantity, unit_price}]` |
| `requires_human_review` | bool | ✅ | Always `true` for Odoo financial actions |
| `source_task` | string | ✅ | Originating task filename |
| `created_at` | ISO8601 | ✅ | |
| `expiry_at` | ISO8601 | ✅ | 24h from `created_at` |
| `status` | string | ✅ | `pending` → `approved`/`rejected`/`expired` |

---

### 4. SocialPostApprovalRequest (approval file in `Pending_Approval/`)

**File naming**: `SOCIAL_<platform>_<YYYYMMDD-HHMMSS>.md`

| Frontmatter Field | Type | Required | Description |
|-------------------|------|----------|-------------|
| `action_type` | string | ✅ | `publish_facebook_post` or `publish_instagram_post` |
| `ralph_loop_id` | string | ❌ | Present when part of a chain |
| `platform` | string | ✅ | `facebook` or `instagram` |
| `post_text` | string | ✅ | Full post content (max 63,206 chars FB; 2,200 chars IG) |
| `hashtags` | list | ❌ | `["#ai", "#business"]` |
| `image_path` | string | ❌ | Local path to image file; `image_required: true` if mandatory for IG |
| `image_required` | bool | ❌ | If `true` and `image_path` null, approval file flagged before moving to Approved/ |
| `session_name` | string | ✅ | `facebook` or `instagram` (agent-browser session name) |
| `source_task` | string | ✅ | |
| `created_at` | ISO8601 | ✅ | |
| `expiry_at` | ISO8601 | ✅ | 24h from `created_at` |
| `status` | string | ✅ | `pending` → `approved`/`rejected`/`expired` |

---

### 5. SocialSession (local file at `~/.agent-browser/sessions/`)

Managed by agent-browser natively. Not a vault file. Backed up to `~/.config/fte/`.

| Attribute | Description |
|-----------|-------------|
| Session name | `facebook` or `instagram` (passed via `--session-name`) |
| Storage path | `~/.agent-browser/sessions/<name>/` (auto-managed) |
| Backup path | `~/.config/fte/<platform>-session.json` |
| Validity | Until platform invalidates session (no fixed expiry) |
| Recovery | `SYSTEM_social-session-expired.md` alert → manual re-auth |

---

### 6. CEOBriefingState

Persisted at `Vault/briefing_state.json`.

| Field | Type | Description |
|-------|------|-------------|
| `last_run` | ISO8601 | Last successful briefing generation timestamp (UTC) |
| `schedule_utc_weekday` | int | Day of week (0=Mon, 6=Sun). Default: 6 |
| `schedule_utc_hour` | int | Hour in UTC. Default: 18 (= Sunday 11 PM PKT) |
| `schedule_utc_minute` | int | Minute. Default: 0 |

---

### 7. CEOBriefing (report file in `Vault/Plans/`)

**File naming**: `CEO_Briefing_<YYYY-MM-DD>.md`

Sections (all auto-generated):

| Section | Data Source |
|---------|-------------|
| Action Required | `Pending_Approval/` (overdue), `Needs_Action/` (SYSTEM_ files), `In_Progress/` (>48h) |
| Emails Handled | `Vault/Logs/` — `action_type: send_email` |
| WhatsApp Replies | `Vault/Logs/` — `action_type: send_whatsapp` |
| Calendar Events | `Vault/Logs/` — `action_type: create_calendar_event` |
| LinkedIn Posts | `Vault/Logs/` — `action_type: publish_linkedin_post` |
| Odoo Activity | `Vault/Logs/` — `action_type: create_odoo_invoice`, `confirm_odoo_invoice` |
| Social Posts | `Vault/Logs/` — `action_type: publish_facebook_post`, `publish_instagram_post` |
| Pending Tasks | `Vault/In_Progress/` count + `Vault/Needs_Action/` count |

---

## State Transitions

### Ralph Loop Task Lifecycle

```
Needs_Action/  →  In_Progress/  →  (Done/ or stays in loop)
     ↑                                      |
CONTINUATION_*.md ← executor drops ← Approved/
```

### Odoo Invoice Chain

```
Needs_Action/            Odoo               Vault
  invoice_request
       ↓ [Claude + MCP]
  [draft created in Odoo] ─────────────────────────→ Pending_Approval/ODOO_CONFIRM_*.md
                                                              ↓ [user approves]
                                                       Approved/ODOO_CONFIRM_*.md
                                                              ↓ [executor: action_post]
                                                       Needs_Action/CONTINUATION_*.md
                                                              ↓ [Claude: email chain step]
                                                       Pending_Approval/EMAIL_REPLY_*.md
                                                              ↓ [user approves]
                                                       Done/ ← task moved by Claude
```

### Social Post Lifecycle

```
Needs_Action/social_post_chain
  ↓ [Claude: drafts per platform]
Pending_Approval/SOCIAL_facebook_*.md
Pending_Approval/SOCIAL_instagram_*.md
  ↓ [user approves each]
Approved/SOCIAL_*.md
  ↓ [executor: agent-browser subprocess]
Published on platform → Logs/ entry
  ↓ [executor: drops continuation if ralph_loop_id set]
Needs_Action/CONTINUATION_*.md (if chain continues)
```

---

## New Log Action Types (extends Silver)

| `action_type` | Description |
|---------------|-------------|
| `create_odoo_invoice` | Draft invoice created in Odoo via MCP |
| `confirm_odoo_invoice` | Invoice confirmed + emailed via JSON-RPC |
| `publish_facebook_post` | Post published via agent-browser |
| `publish_instagram_post` | Post published via agent-browser |
| `ralph_loop_iteration` | Each Ralph Loop iteration logged |
| `ralph_loop_timeout` | Loop hit max iterations |
| `ralph_loop_complete` | Loop exited cleanly (task done) |
| `ceo_briefing_generated` | CEO Briefing report written to Plans/ |
| `briefing_schedule_trigger` | Orchestrator triggered scheduled briefing |
| `social_metrics_collected` | Social engagement metrics collected |
