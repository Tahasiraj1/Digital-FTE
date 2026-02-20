# Data Model: Bronze Tier — Vault & Filesystem Watcher

**Date**: 2026-02-20
**Branch**: `001-bronze-vault-setup`

## Entities

### 1. Vault (Filesystem Structure)

The vault is a directory tree. Not a database — just folders and files.

```
~/AI_Employee_Vault/
├── Inbox/                  # Drop zone for manual or external input
├── Needs_Action/           # Watcher moves files here with timestamp
├── Plans/                  # Claude writes reasoning/plans here
├── Pending_Approval/       # (Bronze: unused, created for future)
├── Approved/               # (Bronze: unused, created for future)
├── Rejected/               # (Bronze: unused, created for future)
├── In_Progress/            # Files being processed by Claude
├── Done/                   # Completed tasks
├── Logs/                   # Structured JSON log files
├── Company_Handbook.md     # User-editable rules for Claude
└── Dashboard.md            # (Bronze: stub, populated in Silver)
```

**State transitions** (file lifecycle):

```
Inbox/ → Needs_Action/ → In_Progress/ → Done/
                ↘ (if malformed)      ↗
                  Plans/ (plan written regardless)
```

### 2. Task File

**Location**: Moves through vault folders per lifecycle above.

**Naming convention**: `YYYY-MM-DD-HHMMSS-<original-name>.<ext>`
- Timestamp prefix added by watcher on move from Inbox
- Original extension preserved (format-agnostic)

**Content**: Free-form. User or external tool writes whatever they want.
Claude interprets the content during reasoning.

**No schema enforced at Bronze** — files are opaque to the watcher.
Only Claude (reasoning layer) interprets content.

### 3. Plan File

**Location**: `Plans/`

**Naming convention**: `PLAN-<original-task-slug>.md`
- Slug derived from the source task filename (minus timestamp/ext)

**Content structure** (Markdown):

```markdown
---
source_task: Needs_Action/2026-02-20-120000-reply-to-client.md
created: 2026-02-20T12:01:00Z
status: proposed
---

## Summary

[One-line summary of what Claude recommends]

## Reasoning

[Claude's analysis of the task file content]

## Recommended Action

[What should be done — at Bronze, this is advisory only]

## Confidence

[high / medium / low — Claude's self-assessed confidence]
```

### 4. Log Entry

**Location**: `Logs/YYYY-MM-DD.json` (one file per day, JSONL format)

**Schema** (one JSON object per line):

```json
{
  "timestamp": "2026-02-20T12:00:05Z",
  "action_type": "file_move | reasoning | error | system",
  "actor": "watcher | orchestrator | claude | system",
  "source": "/path/or/null",
  "destination": "/path/or/null",
  "parameters": {},
  "result": "success | error | skipped",
  "error_message": "null or string",
  "duration_ms": 150
}
```

**Fields**:
- `timestamp`: ISO 8601 UTC
- `action_type`: One of the enumerated types
- `actor`: Which component produced this log
- `source` / `destination`: File paths (for moves) or null
- `parameters`: Context-dependent metadata (e.g., prompt text for
  reasoning, file count for batch operations)
- `result`: Outcome enum
- `error_message`: Populated only when result is "error"
- `duration_ms`: How long the action took

### 5. Company Handbook

**Location**: `Company_Handbook.md` (vault root)

**Content structure** (Bronze stub):

```markdown
# Company Handbook

## Rules of Engagement

- [Add your rules here, e.g., "Always be polite in responses"]
- [e.g., "Flag any payment over $500 for my approval"]

## Auto-Approve Thresholds

- Payments: $0 (all payments require approval)
- Emails to known contacts: require approval
- Emails to unknown contacts: require approval

## Business Context

- [Describe your business for Claude's reference]
- [e.g., "I run a freelance web development consultancy"]
```

### 6. Lockfile

**Location**: `<vault>/.watcher.lock`

**Content**: PID of the running watcher process (plain text integer).

**Lifecycle**: Created on watcher start, deleted on graceful shutdown.
Stale locks (PID no longer running) are overwritten on startup.
