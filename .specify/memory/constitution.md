<!--
Sync Impact Report
- Version change: 0.0.0 → 1.0.0 (initial ratification)
- Modified principles: N/A (first version)
- Added sections:
  - Core Principles (8 principles)
  - Technology Stack & Constraints
  - Development Workflow
  - Governance
- Removed sections: N/A
- Templates requiring updates:
  - .specify/templates/plan-template.md — ⚠ pending (Constitution Check
    section needs project-specific gates on next /sp.plan run)
  - .specify/templates/spec-template.md — ✅ compatible (no changes needed)
  - .specify/templates/tasks-template.md — ✅ compatible (no changes needed)
- Follow-up TODOs:
  - TODO(TIER_TARGET): User has not declared Bronze/Silver/Gold/Platinum
    target yet. Constitution assumes iterative scope discovery.
  - TODO(ODOO_DECISION): Odoo integration is Gold-tier; defer until scope
    is confirmed.
-->
# Personal AI Employee (FTE) Constitution

## Core Principles

### I. Local-First Privacy

All persistent data — vault files, logs, plans, briefings — MUST reside
on the user's local machine by default. Obsidian (local Markdown) is the
single source of truth for state, memory, and dashboard. Sensitive data
(credentials, banking tokens, WhatsApp sessions) MUST never leave the
local environment unless the user explicitly configures cloud sync for
non-secret files (Platinum tier). Cloud sync, when enabled, MUST exclude
`.env`, credentials, and session files via gitignore or equivalent.

### II. Human-in-the-Loop Safety (NON-NEGOTIABLE)

The AI Employee MUST NOT execute sensitive or irreversible actions without
explicit human approval. Sensitive actions include:
- Payments to any recipient (all amounts for new payees; >$100 for known)
- Emails to new or unknown contacts
- Bulk sends (email, social media DMs)
- File deletion or moves outside the vault
- Any action flagged in `Company_Handbook.md`

Approval workflow: Claude writes an approval-request file to
`/Pending_Approval/`. The action executes ONLY after the user moves the
file to `/Approved/`. Rejected actions are moved to `/Rejected/` and
logged. Auto-approve thresholds MUST be documented in
`Company_Handbook.md` and default to conservative (deny).

### III. Perception-Reasoning-Action Pipeline

The system follows a strict three-layer architecture:
1. **Perception (Watchers):** Lightweight Python scripts poll external
   sources (Gmail, WhatsApp, bank APIs, filesystem) and write `.md`
   files into `/Needs_Action/`. Watchers MUST NOT reason or act — they
   only observe and record.
2. **Reasoning (Claude Code):** Reads `/Needs_Action/`, thinks, and
   writes plans (`/Plans/`) or approval requests
   (`/Pending_Approval/`). Reasoning MUST reference
   `Company_Handbook.md` rules before deciding.
3. **Action (MCP Servers):** External integrations (email, browser,
   payments) execute ONLY after reasoning and (where required) human
   approval. Each MCP server owns a single domain of action.

No layer may bypass another. Watchers never act. Claude never sends
without MCP. MCP never acts without Claude's instruction.

### IV. Agent Skill Architecture

All AI functionality MUST be implemented as Claude Code Agent Skills.
Skills are reusable, composable units that encapsulate a specific
capability (e.g., "draft invoice," "triage email," "generate CEO
briefing"). This ensures:
- Capabilities are discoverable and documented
- Skills can be tested independently
- New functionality is added by creating new skills, not modifying
  core orchestration

### V. Security by Default

- Credentials MUST use environment variables or OS-native secret stores
  (macOS Keychain, Windows Credential Manager, 1Password CLI). Never
  plain text, never in the vault.
- `.env` files MUST be gitignored immediately upon creation.
- All action scripts MUST support a `--dry-run` flag during development.
- A `DEV_MODE` environment variable MUST gate all real external actions.
- Rate limits MUST be enforced: max 10 emails/hour, max 3 payments/hour
  (configurable in `Company_Handbook.md`).
- Credentials MUST be rotated monthly or after any suspected breach.

### VI. Observability & Auditability

Every action the AI Employee takes MUST be logged in structured JSON
format to `/Logs/YYYY-MM-DD.json` with fields: timestamp, action_type,
actor, target, parameters, approval_status, approved_by, result.
Logs MUST be retained for a minimum of 90 days. The system MUST support
three oversight cadences:
- Daily: 2-minute dashboard check (`Dashboard.md`)
- Weekly: 15-minute action log review
- Monthly: 1-hour comprehensive audit

### VII. Autonomous Persistence (Ralph Wiggum Pattern)

For multi-step tasks, the system MUST use the Ralph Wiggum loop (a Stop
hook pattern) to keep Claude iterating until the task is complete or a
max-iteration limit is reached. Completion is detected by either:
1. Promise-based: Claude outputs `<promise>TASK_COMPLETE</promise>`
2. File-movement: Task file moves from `/In_Progress/` to `/Done/`

Max iterations MUST be configurable (default: 10) and logged. If max
iterations are reached without completion, the system MUST alert the
user and pause rather than retry indefinitely.

### VIII. Incremental Delivery & Iterative Scope

The project follows a tiered delivery model (Bronze → Silver → Gold →
Platinum). Each tier builds on the previous. Development MUST:
- Start with the smallest viable working system (Bronze: 1 watcher +
  vault + basic folder structure)
- Add capabilities incrementally, validating each tier before advancing
- Never block Bronze functionality on Silver/Gold/Platinum requirements
- Keep specifications and constitutions living documents — updated as
  scope and tools become clear through iteration

## Technology Stack & Constraints

**Core Stack (all tiers):**
- **Knowledge Base / GUI:** Obsidian (local Markdown vault)
- **Reasoning Engine:** Claude Code (claude-4-5-opus or via router)
- **Watcher Scripts:** Python 3.13+ with `uv` project management
- **MCP Servers:** Node.js v24+ LTS or Python
- **Web Automation:** Playwright (for WhatsApp, payment portals)
- **Process Management:** PM2 (recommended) or supervisord
- **Version Control:** Git + GitHub

**Constraints:**
- Minimum hardware: 8GB RAM, 4-core CPU, 20GB free disk, stable internet
- Recommended: 16GB RAM, 8-core CPU, SSD
- All watcher scripts MUST be managed by a process manager for crash
  recovery and boot persistence
- MCP server paths in configuration MUST be absolute
- The vault folder structure MUST include at minimum:
  `/Inbox`, `/Needs_Action`, `/Plans`, `/Pending_Approval`, `/Approved`,
  `/Rejected`, `/Done`, `/Logs`, `/In_Progress`

**Gold/Platinum additions (deferred until tier confirmed):**
- Odoo Community (self-hosted) for accounting/ERP
- Cloud VM deployment (Oracle Free Tier / AWS)
- Git-based vault sync between local and cloud agents

## Development Workflow

1. **Spec-Driven Development:** Every feature begins with a specification
   (`/sp.specify`) before implementation. Plans (`/sp.plan`) and tasks
   (`/sp.tasks`) follow. No code without a spec.

2. **Iterative Clarification:** Because the full scope is not yet known,
   specs and plans are living documents. Use `/sp.clarify` liberally.
   Constitution amendments follow governance rules below.

3. **Watcher-First Development:** When adding a new integration domain
   (e.g., Gmail, WhatsApp), implement the Watcher first, verify it
   produces correct `/Needs_Action/` files, then build reasoning and
   action layers.

4. **Dry-Run Gate:** All new action scripts MUST be tested in `DEV_MODE`
   / `--dry-run` before connecting to real accounts. The first real
   execution of any action MUST be manually approved regardless of
   auto-approve thresholds.

5. **Checkpoint Validation:** After completing each tier (Bronze, Silver,
   Gold), perform a full integration test: trigger a watcher event, verify
   reasoning, verify action (or approval request), verify logging.

## Governance

This constitution is the authoritative source of project principles.
All development decisions, code reviews, and architectural choices MUST
comply with these principles. Conflicts are resolved by this document.

**Amendment procedure:**
1. Propose the change with rationale (via `/sp.constitution` or PR).
2. Review against existing principles for conflicts.
3. Update version per semantic versioning (MAJOR: principle removal or
   redefinition; MINOR: new principle or material expansion; PATCH:
   clarification or wording fix).
4. Propagate changes to dependent templates and documents.
5. Record the amendment in a PHR.

**Compliance review:** Every spec and plan MUST include a Constitution
Check section verifying alignment with these principles.

**Living document notice:** This constitution will evolve as the project
scope becomes clearer through iteration. Principles marked as
NON-NEGOTIABLE require MAJOR version bump to modify.

**Version**: 1.0.0 | **Ratified**: 2026-02-20 | **Last Amended**: 2026-02-20
