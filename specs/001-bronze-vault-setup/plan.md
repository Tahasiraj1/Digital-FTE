# Implementation Plan: Bronze Tier — Vault & Filesystem Watcher

**Branch**: `001-bronze-vault-setup` | **Date**: 2026-02-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-bronze-vault-setup/spec.md`

## Summary

Build the simplest working Personal AI Employee: an Obsidian vault with
structured folders, a filesystem watcher that moves files from Inbox to
Needs_Action with timestamps, a Python orchestrator that polls
Needs_Action and invokes Claude Code to write reasoning plans, and
structured JSON logging for all actions. No external APIs, no MCP
servers, no approval workflow — just the Perception → Reasoning pipeline
running locally.

## Technical Context

**Language/Version**: Python 3.13+
**Primary Dependencies**: watchdog (filesystem events), subprocess (Claude invocation), pathlib (file operations), argparse (CLI)
**Storage**: Local filesystem (Obsidian Markdown vault at user-chosen path)
**Testing**: pytest + tmp_path fixtures for filesystem isolation
**Target Platform**: Cross-platform (Linux/macOS/Windows via WSL)
**Project Type**: Single project
**Performance Goals**: File detection within 5s, reasoning cycle within 60s
**Constraints**: No external network calls, no database, <50MB memory
**Scale/Scope**: Single user, single machine, ~10 files/day throughput

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Local-First Privacy | ✅ PASS | Vault is local Markdown. No cloud, no network. |
| II. Human-in-the-Loop | ✅ PASS | Bronze writes plans only — no actions executed. Approval folders created but unused. |
| III. Perception-Reasoning-Action | ✅ PASS | Watcher (perception) → Orchestrator+Claude (reasoning). Action layer deferred to Silver. Layers don't bypass each other. |
| IV. Agent Skill Architecture | ⚠ DEFERRED | No Agent Skills at Bronze. Reasoning is a single Claude prompt. Skills introduced at Silver. Justified: Bronze is about proving the pipeline, not composability. |
| V. Security by Default | ✅ PASS | No credentials needed at Bronze. `--dry-run` flag on orchestrator. No `.env` file needed yet. |
| VI. Observability & Auditability | ✅ PASS | JSONL logging to `Logs/YYYY-MM-DD.json` for every action. |
| VII. Autonomous Persistence | ⚠ DEFERRED | No Ralph Wiggum loop at Bronze. Orchestrator polls but Claude runs one-shot per invocation. Justified: multi-step persistence is Gold tier. |
| VIII. Incremental Delivery | ✅ PASS | This IS the Bronze tier — smallest viable system. |

**Gate result**: PASS (2 deferred items justified, 0 violations)

## Project Structure

### Documentation (this feature)

```text
specs/001-bronze-vault-setup/
├── plan.md              # This file
├── research.md          # Phase 0: technology decisions
├── data-model.md        # Phase 1: entities and schemas
├── quickstart.md        # Phase 1: user-facing getting started
├── contracts/
│   └── cli-interface.md # Phase 1: CLI command contracts
└── tasks.md             # Phase 2: (/sp.tasks - not yet created)
```

### Source Code (repository root)

```text
src/
├── fte/
│   ├── __init__.py
│   ├── cli.py               # argparse entry point (fte init/watch/orchestrate)
│   ├── vault.py             # Vault initialization logic
│   ├── watcher.py           # Filesystem watcher (Inbox → Needs_Action)
│   ├── orchestrator.py      # Polls Needs_Action, invokes Claude
│   ├── logger.py            # Structured JSONL logging to Logs/
│   └── lockfile.py          # PID-based lockfile management
├── pyproject.toml            # uv project config, dependencies, entry points
└── README.md                 # (already exists)

tests/
├── conftest.py              # Shared fixtures (tmp vault, mock Claude)
├── test_vault.py            # Vault initialization tests
├── test_watcher.py          # Watcher behavior tests
├── test_orchestrator.py     # Orchestrator polling + Claude invocation tests
├── test_logger.py           # Log format and append tests
└── test_lockfile.py         # Lockfile create/check/cleanup tests
```

**Structure Decision**: Single project layout. The `fte` package under
`src/` contains all components. CLI entry point registered via
`pyproject.toml` `[project.scripts]` so `uv run fte` works. Tests
mirror source structure. No frontend, no backend split — this is a
CLI tool + background processes.

### Vault Structure (created by `fte init`)

```text
~/AI_Employee_Vault/          # User-chosen path
├── Inbox/                    # User drops files here
├── Needs_Action/             # Watcher moves files here
├── Plans/                    # Claude writes plans here
├── Pending_Approval/         # (Bronze: empty, future use)
├── Approved/                 # (Bronze: empty, future use)
├── Rejected/                 # (Bronze: empty, future use)
├── In_Progress/              # Files being processed
├── Done/                     # Completed tasks
├── Logs/                     # JSONL log files
├── Company_Handbook.md       # User-editable rules
└── Dashboard.md              # (Bronze: stub)
```

## Component Design

### 1. vault.py — Vault Initialization

**Responsibility**: Create vault folder structure idempotently.

**Key decisions**:
- Uses `pathlib.Path.mkdir(parents=True, exist_ok=True)` for idempotency
- Creates `Company_Handbook.md` and `Dashboard.md` only if they don't
  exist (preserves user edits)
- Returns a list of created/existing items for CLI output

### 2. watcher.py — Filesystem Watcher

**Responsibility**: Monitor `Inbox/`, move files to `Needs_Action/`
with timestamp prefix.

**Key decisions**:
- Uses `watchdog.Observer` for real-time filesystem events
- On startup, scans `Inbox/` for pre-existing files (catch-up)
- Timestamp format: `YYYY-MM-DD-HHMMSS-` prefix
- Moves files atomically via `shutil.move()`
- Logs every move via `logger.py`
- Graceful shutdown on SIGINT/SIGTERM: stops observer, removes lockfile

### 3. orchestrator.py — Reasoning Orchestrator

**Responsibility**: Poll `Needs_Action/`, invoke Claude Code, manage
file transitions.

**Key decisions**:
- Polls via `time.sleep(interval)` loop (not watchdog — different
  lifecycle than the watcher)
- Invokes Claude Code via `subprocess.run()`:
  ```
  claude -p "<prompt>" --cwd <vault_path>
  ```
- Prompt template instructs Claude to:
  1. Read files in `Needs_Action/`
  2. Reference `Company_Handbook.md`
  3. Write plan files to `Plans/`
  4. Output filenames of processed files
- After Claude exits, orchestrator moves processed files to
  `In_Progress/`
- `--dry-run` flag: logs what would happen, skips Claude invocation
- Graceful shutdown: waits for in-flight Claude process, then exits

### 4. logger.py — Structured Logging

**Responsibility**: Append JSONL log entries to daily log files.

**Key decisions**:
- One file per day: `Logs/YYYY-MM-DD.json`
- Each line is a self-contained JSON object (JSONL)
- Append-only (no read-modify-write)
- Thread-safe via file-level locking
- All components import and call `log_action()` function

### 5. lockfile.py — Single Instance Guard

**Responsibility**: Prevent duplicate watcher instances.

**Key decisions**:
- Lockfile at `<vault>/.watcher.lock` containing PID
- On startup: check if PID in lockfile is still running
- If running: exit with error
- If stale (process dead): overwrite with new PID
- On shutdown: delete lockfile

### 6. cli.py — Command Line Interface

**Responsibility**: Parse arguments and dispatch to components.

**Key decisions**:
- Uses `argparse` with subcommands: `init`, `watch`, `orchestrate`
- Registered as `fte` entry point in `pyproject.toml`
- Each subcommand validates vault path exists (except `init` which
  creates it)

## Complexity Tracking

No constitution violations requiring justification. Two principles
deferred (Agent Skills, Ralph Wiggum) with rationale documented in
Constitution Check above.
