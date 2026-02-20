# Tasks: Bronze Tier — Vault & Filesystem Watcher

**Input**: Design documents from `/specs/001-bronze-vault-setup/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/cli-interface.md

**Tests**: Not explicitly requested in the feature specification. Test files are defined in plan.md for future use but test tasks are excluded from this task list.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, package structure, and dependency management

- [x] T001 Initialize uv project with pyproject.toml at repo root — define `[project]` with name="digital-fte", python requires >=3.13, dependencies=[watchdog], and `[project.scripts]` entry `fte = "fte.cli:main"`. Use `[tool.uv]` for dev dependencies (pytest). Set `[tool.setuptools.packages.find]` to `where = ["src"]`
- [x] T002 [P] Create package structure: src/fte/__init__.py (empty) at src/fte/__init__.py
- [x] T003 [P] Update .gitignore at repo root — add Python patterns (__pycache__, *.pyc, .venv, dist/, *.egg-info) and vault runtime patterns (*.lock, Logs/)

**Checkpoint**: `uv sync` succeeds and `uv run fte --help` shows usage (will error on missing cli.py — that's expected)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities that ALL user stories depend on — logger and lockfile

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement structured JSONL logger in src/fte/logger.py — create `log_action(vault_path, action_type, actor, source, destination, parameters, result, error_message, duration_ms)` function. Must: append one JSON object per line to `Logs/YYYY-MM-DD.json`, use ISO 8601 UTC timestamps, create Logs/ dir if missing, handle write errors gracefully (print to stderr, never crash caller). Schema per data-model.md Log Entry
- [x] T005 [P] Implement PID-based lockfile manager in src/fte/lockfile.py — create `acquire_lock(vault_path)` and `release_lock(vault_path)` functions. Lockfile at `<vault>/.watcher.lock`. Must: write current PID on acquire, check if existing PID is still running (stale detection via `os.kill(pid, 0)`), raise error if active lock exists, delete lockfile on release. Handle cross-platform PID check (Windows vs Unix)

**Checkpoint**: Both modules importable, `log_action()` appends valid JSONL, lockfile acquire/release cycle works

---

## Phase 3: User Story 1 — Vault Initialization (Priority: P1) MVP

**Goal**: User runs `fte init` and gets a fully structured Obsidian vault ready for all other components

**Independent Test**: Run `fte init --path /tmp/test-vault`, verify all 9 folders + 2 files exist. Run again, verify idempotent (no errors, existing files preserved)

### Implementation for User Story 1

- [x] T006 [US1] Implement vault initialization logic in src/fte/vault.py — create `init_vault(path)` function that: creates vault root dir, creates 9 subdirectories (Inbox, Needs_Action, Plans, Pending_Approval, Approved, Rejected, Done, In_Progress, Logs) via `Path.mkdir(parents=True, exist_ok=True)`, creates Company_Handbook.md stub (content per data-model.md Section 5) only if not exists, creates Dashboard.md stub only if not exists, returns list of `(item_name, "created"|"exists")` tuples for CLI output, logs vault init action via logger.log_action()
- [x] T007 [US1] Implement `fte init` CLI subcommand in src/fte/cli.py — create `main()` with argparse using subcommands. Add `init` subcommand with `--path` argument (default: `~/AI_Employee_Vault/`). Dispatch to `vault.init_vault()`. Print status output per contracts/cli-interface.md Section 1 (checkmark per folder/file). Exit code 0 on success, 1 on error. Handle `--path` expansion (`~` → home dir)

**Checkpoint**: `uv run fte init --path /tmp/test-vault` creates vault. Re-run is idempotent. Obsidian can open it.

---

## Phase 4: User Story 2 — Filesystem Watcher (Priority: P2)

**Goal**: Background watcher monitors Inbox/ and moves new files to Needs_Action/ with timestamp prefix

**Independent Test**: Start watcher, drop file into Inbox/, verify it appears in Needs_Action/ within 5s as `YYYY-MM-DD-HHMMSS-<name>`

### Implementation for User Story 2

- [x] T008 [US2] Implement filesystem watcher in src/fte/watcher.py — create `InboxHandler(FileSystemEventHandler)` class with `on_created` method that: ignores directories, computes timestamp prefix (`YYYY-MM-DD-HHMMSS-`), moves file via `shutil.move()` to Needs_Action/ with prefixed name, logs via logger.log_action(). Create `run_watcher(vault_path, interval)` function that: acquires lockfile via lockfile.acquire_lock(), scans Inbox/ for pre-existing files on startup (catch-up per FR-004), starts watchdog Observer on Inbox/, enters blocking loop, returns on shutdown
- [x] T009 [US2] Add signal handling and graceful shutdown to src/fte/watcher.py — register SIGINT and SIGTERM handlers in `run_watcher()`. On signal: stop watchdog Observer, release lockfile via lockfile.release_lock(), log shutdown event, exit cleanly with code 0
- [x] T010 [US2] Add `fte watch` subcommand to src/fte/cli.py — add `watch` subcommand with `--path` (default: ~/AI_Employee_Vault/) and `--interval` (default: 5) arguments. Validate vault exists (error if not initialized). Dispatch to `watcher.run_watcher()`. Print startup message per contracts/cli-interface.md Section 2

**Checkpoint**: `uv run fte watch --path /tmp/test-vault` starts. Drop file in Inbox/, appears in Needs_Action/ with timestamp prefix. Ctrl+C shuts down cleanly.

---

## Phase 5: User Story 3 — Claude Reads and Reasons (Priority: P3)

**Goal**: Orchestrator polls Needs_Action/, invokes Claude Code to write plans to Plans/, and moves processed files to In_Progress/

**Independent Test**: Place a task file in Needs_Action/, start orchestrator, verify plan appears in Plans/ and task file moves to In_Progress/

### Implementation for User Story 3

- [x] T011 [US3] Implement orchestrator polling loop in src/fte/orchestrator.py — create `run_orchestrator(vault_path, interval, dry_run)` function that: enters `while True` loop, lists files in Needs_Action/ each cycle, if files found calls `invoke_claude()`, sleeps for `interval` seconds between cycles. Log each poll cycle (files found count) via logger.log_action()
- [x] T012 [US3] Implement Claude Code subprocess invocation in src/fte/orchestrator.py — create `invoke_claude(vault_path, files)` function that: builds prompt string instructing Claude to read each file in Needs_Action/, reference Company_Handbook.md, write plan files to Plans/ using `PLAN-<slug>.md` naming convention with frontmatter per data-model.md Section 3, runs `subprocess.run(["claude", "-p", prompt, "--cwd", str(vault_path)])`, captures stdout/stderr, logs invocation result. After Claude exits: move processed files from Needs_Action/ to In_Progress/ via shutil.move(), log each move. Handle Claude not found (FileNotFoundError), non-zero exit code, and timeout (configurable, default 120s)
- [x] T013 [US3] Implement --dry-run mode in src/fte/orchestrator.py — when `dry_run=True`: list files that would be processed, log "[DRY RUN]" entries, skip Claude invocation and file moves entirely. Output per contracts/cli-interface.md dry-run format
- [x] T014 [US3] Add `fte orchestrate` subcommand to src/fte/cli.py — add `orchestrate` subcommand with `--path` (default: ~/AI_Employee_Vault/), `--interval` (default: 30), `--dry-run` (flag) arguments. Validate vault exists. Dispatch to `orchestrator.run_orchestrator()`. Print startup message per contracts/cli-interface.md Section 3
- [x] T015 [US3] Add signal handling and graceful shutdown to src/fte/orchestrator.py — register SIGINT and SIGTERM handlers in `run_orchestrator()`. On signal: set shutdown flag, wait for in-flight Claude subprocess to complete (do not kill it), log shutdown event, exit cleanly with code 0

**Checkpoint**: `uv run fte orchestrate --path /tmp/test-vault --dry-run` lists files without invoking Claude. Without --dry-run, Claude produces plan files in Plans/ and task files move to In_Progress/.

---

## Phase 6: User Story 4 — Action Logging Hardening (Priority: P4)

**Goal**: Every system action has a corresponding log entry — verify and harden logging across all components

**Independent Test**: Run full pipeline (init → watch → drop file → orchestrate), check Logs/YYYY-MM-DD.json has entries for every action with correct fields per data-model.md Log Entry schema

### Implementation for User Story 4

- [x] T016 [US4] Add error-resilient logging to watcher error paths in src/fte/watcher.py — wrap file move in try/except, log errors (permission denied, disk full, source file vanished) with action_type="error", result="error", and error_message field. Continue processing remaining files after error. Log catch-up count on startup
- [x] T017 [US4] Add error-resilient logging to orchestrator error paths in src/fte/orchestrator.py — log errors for: Claude not found, Claude non-zero exit, Claude timeout, file move failures during In_Progress transition. Each error logged with action_type="error" and descriptive error_message. Continue polling after errors (do not crash)
- [x] T018 [US4] Add system lifecycle log entries — log "system_start" event in watcher.run_watcher() and orchestrator.run_orchestrator() on startup (with config: interval, vault_path). Log "system_shutdown" event on graceful exit. Add to both src/fte/watcher.py and src/fte/orchestrator.py

**Checkpoint**: After running full pipeline, `cat Logs/YYYY-MM-DD.json | python -m json.tool --no-ensure-ascii` validates every line. Each line has all required fields. Error scenarios produce error log entries without crashing.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final integration validation and documentation

- [x] T019 [P] Add descriptive --help text to all CLI subcommands in src/fte/cli.py — add help strings to argparse parser and all subcommands/arguments. Running `fte --help`, `fte init --help`, `fte watch --help`, `fte orchestrate --help` should all produce useful output
- [x] T020 Validate end-to-end flow per specs/001-bronze-vault-setup/quickstart.md — execute all 9 quickstart steps, verify each step produces expected output. Document any deviations and fix

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (T001 for imports). BLOCKS all user stories
- **US1 - Vault Init (Phase 3)**: Depends on Phase 2 (uses logger). No dependency on other stories
- **US2 - Watcher (Phase 4)**: Depends on Phase 2 (uses logger + lockfile) and Phase 3 (vault must exist). Can be tested independently after init
- **US3 - Orchestrator (Phase 5)**: Depends on Phase 2 (uses logger) and Phase 3 (vault must exist). Can be tested independently (manually place files in Needs_Action)
- **US4 - Logging Hardening (Phase 6)**: Depends on Phases 3, 4, 5 (hardens existing logging)
- **Polish (Phase 7)**: Depends on all phases complete

### User Story Dependencies

- **US1 (P1)**: Foundational only — can start first
- **US2 (P2)**: Foundational + US1 (needs vault folder to watch)
- **US3 (P3)**: Foundational + US1 (needs vault). Independent of US2 (can manually place files)
- **US4 (P4)**: All prior stories (hardens their logging)

### Within Each User Story

- Core logic module before CLI subcommand
- Signal handling after core logic
- Integration with logger/lockfile from start (foundational is complete)

### Parallel Opportunities

- T002 and T003 can run in parallel (Phase 1)
- T004 and T005 can run in parallel (Phase 2)
- US2 (Phase 4) and US3 (Phase 5) can run in parallel after US1 completes
- T019 can run in parallel with T020 (Phase 7)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T005)
3. Complete Phase 3: User Story 1 (T006-T007)
4. **STOP and VALIDATE**: Run `fte init`, verify vault in Obsidian
5. This alone proves the project structure and tooling work

### Incremental Delivery

1. Setup + Foundational → tooling works
2. Add US1 (Vault Init) → `fte init` works, vault visible in Obsidian
3. Add US2 (Watcher) → Inbox → Needs_Action pipeline live
4. Add US3 (Orchestrator) → Claude reasoning produces plans
5. Add US4 (Logging Hardening) → bulletproof observability
6. Polish → end-to-end validated against quickstart

### Sequential Execution (Solo Developer)

T001 → T002+T003 → T004+T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012 → T013 → T014 → T015 → T016 → T017 → T018 → T019+T020

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Claude invocation (T012) requires Claude Code CLI installed and authenticated — test with --dry-run first
