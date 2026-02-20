# CLI Interface Contracts: Bronze Tier

**Date**: 2026-02-20

Bronze tier exposes three CLI entry points. No HTTP APIs — all
interaction is via the command line and filesystem.

## 1. Vault Initialization

```
fte init [--path <vault-path>]
```

**Arguments**:
- `--path`: Target directory for the vault. Default: `~/AI_Employee_Vault/`

**Behavior**:
- Creates vault directory if it doesn't exist
- Creates all 9 required subdirectories (idempotent)
- Creates `Company_Handbook.md` stub if not present
- Creates `Dashboard.md` stub if not present
- Prints created/existing status for each folder

**Exit codes**:
- `0`: Success (all folders exist)
- `1`: Error (permission denied, invalid path)

**stdout** (success):
```
Vault initialized at /home/user/AI_Employee_Vault/
  ✓ Inbox/
  ✓ Needs_Action/
  ✓ Plans/
  ✓ Pending_Approval/
  ✓ Approved/
  ✓ Rejected/
  ✓ Done/
  ✓ In_Progress/
  ✓ Logs/
  ✓ Company_Handbook.md
  ✓ Dashboard.md
```

## 2. Filesystem Watcher

```
fte watch [--path <vault-path>] [--interval <seconds>]
```

**Arguments**:
- `--path`: Vault directory. Default: `~/AI_Employee_Vault/`
- `--interval`: Polling fallback interval in seconds. Default: `5`

**Behavior**:
- Checks lockfile; exits with error if another instance is running
- Creates lockfile with current PID
- Processes any pre-existing files in `Inbox/` (catch-up)
- Watches `Inbox/` for new files using watchdog
- Moves detected files to `Needs_Action/` with timestamp prefix
- Logs every move to `Logs/YYYY-MM-DD.json`
- On SIGINT/SIGTERM: removes lockfile, exits cleanly

**Exit codes**:
- `0`: Clean shutdown (SIGINT/SIGTERM)
- `1`: Error (lockfile conflict, permission error)

**stdout** (running):
```
Watcher started. Monitoring Inbox/ at /home/user/AI_Employee_Vault/
[12:00:05] Moved: test-task.md → Needs_Action/2026-02-20-120005-test-task.md
[12:01:00] Watching... (0 files in Inbox/)
```

## 3. Orchestrator

```
fte orchestrate [--path <vault-path>] [--interval <seconds>] [--dry-run]
```

**Arguments**:
- `--path`: Vault directory. Default: `~/AI_Employee_Vault/`
- `--interval`: Polling interval in seconds. Default: `30`
- `--dry-run`: Log what would happen without invoking Claude

**Behavior**:
- Polls `Needs_Action/` every `--interval` seconds
- When files found: invokes Claude Code via subprocess with prompt
  referencing `Company_Handbook.md`
- Claude writes plan files to `Plans/`
- Orchestrator moves processed files from `Needs_Action/` to
  `In_Progress/`
- Logs every orchestration cycle to `Logs/YYYY-MM-DD.json`
- On SIGINT/SIGTERM: waits for current Claude invocation to finish,
  then exits cleanly

**Exit codes**:
- `0`: Clean shutdown
- `1`: Error (Claude not found, vault not initialized)

**stdout** (running):
```
Orchestrator started. Polling Needs_Action/ every 30s.
[12:01:30] Found 1 file(s) in Needs_Action/. Invoking Claude...
[12:01:45] Claude completed. Plan written: Plans/PLAN-reply-to-client.md
[12:01:45] Moved: 2026-02-20-120005-reply-to-client.md → In_Progress/
[12:02:00] Polling... (0 files in Needs_Action/)
```

**Dry-run stdout**:
```
[DRY RUN] Would invoke Claude for 1 file(s):
  - Needs_Action/2026-02-20-120005-reply-to-client.md
[DRY RUN] No files moved. No Claude invocation.
```
