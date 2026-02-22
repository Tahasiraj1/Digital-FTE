# Feature Specification: Bronze Tier — Vault & Filesystem Watcher

**Feature Branch**: `001-bronze-vault-setup`
**Created**: 2026-02-20
**Status**: Draft
**Input**: User description: "Start from bronze tier, implement simplest version first, understand it, refine constitution, then move on after testing thoroughly."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Vault Initialization (Priority: P1)

As a user, I want to run a single setup command that creates my
Obsidian vault with the correct folder structure so that the AI Employee
has a working filesystem to operate on from day one.

**Why this priority**: Without the vault folder structure, no other
component (watchers, reasoning, actions) has a place to read from or
write to. This is the foundation everything depends on.

**Independent Test**: Can be fully tested by running the setup command
and verifying all required folders exist, are empty, and Obsidian can
open the vault.

**Acceptance Scenarios**:

1. **Given** a fresh machine with no vault, **When** the user runs the
   vault initialization script with a target path (e.g.,
   `~/AI_Employee_Vault/`), **Then** the vault directory is created at
   that path with all required folders: `Inbox`, `Needs_Action`, `Plans`,
   `Pending_Approval`, `Approved`, `Rejected`, `Done`, `In_Progress`,
   `Logs`.
2. **Given** the vault has been initialized, **When** the user opens it
   in Obsidian, **Then** the folder structure is visible and navigable.
3. **Given** the vault already exists, **When** the user runs the setup
   script again, **Then** existing files are preserved (idempotent) and
   missing folders are created.

---

### User Story 2 — Filesystem Watcher Detects New Files (Priority: P2)

As a user, I want a background watcher that monitors my `Inbox` folder
so that when I (or another tool) drops a file there, the system
automatically moves it to `Needs_Action` for processing.

**Why this priority**: This is the simplest possible "Perception" layer
— no external APIs, no credentials, just filesystem events. It proves
the watcher pattern works before adding Gmail/WhatsApp.

**Independent Test**: Drop a `.md` file into `Inbox/`, verify it
appears in `Needs_Action/` within 5 seconds with a timestamp prefix
added to the filename.

**Acceptance Scenarios**:

1. **Given** the watcher is running and `Inbox/` is empty, **When** I
   create a file `test-task.md` in `Inbox/`, **Then** within 5 seconds
   the file appears in `Needs_Action/` as
   `YYYY-MM-DD-HHMMSS-test-task.md` and `Inbox/` is empty.
2. **Given** the watcher is running, **When** I drop 3 files into
   `Inbox/` simultaneously, **Then** all 3 appear in `Needs_Action/`
   with correct timestamps and none are lost.
3. **Given** the watcher is running, **When** I drop a non-markdown file
   (e.g., `.txt`, `.pdf`) into `Inbox/`, **Then** the file is still
   moved to `Needs_Action/` (watcher is format-agnostic at Bronze tier).
4. **Given** the watcher is NOT running, **When** I drop files into
   `Inbox/` and then start the watcher, **Then** pre-existing files in
   `Inbox/` are processed on startup.

---

### User Story 3 — Claude Reads and Reasons (Priority: P3)

As a user, I want Claude Code to read files from `Needs_Action/`,
decide what to do, and write a plan to `Plans/` so that I can see what
the AI Employee recommends before any action is taken.

**Why this priority**: This completes the Bronze "Perception →
Reasoning" loop. No actions are executed — Claude only writes
recommendations. This lets the user build trust before enabling actions.

**Independent Test**: Place a task file in `Needs_Action/`, invoke the
reasoning loop, verify a corresponding plan file appears in `Plans/`
that references the original task.

**Acceptance Scenarios**:

1. **Given** a file `2026-02-20-120000-reply-to-client.md` exists in
   `Needs_Action/` with content "Client asked about project timeline,"
   **When** the reasoning loop runs, **Then** a plan file
   `reply-to-client-plan.md` appears in `Plans/` containing a
   recommended response and reasoning.
2. **Given** `Needs_Action/` contains multiple files, **When** the
   reasoning loop runs, **Then** each file gets its own plan in
   `Plans/` and processed files move to `In_Progress/`.
3. **Given** `Needs_Action/` is empty, **When** the reasoning loop runs,
   **Then** no plan files are created and the system logs "No items
   requiring action."
4. **Given** a file in `Needs_Action/` is malformed or empty, **When**
   the reasoning loop runs, **Then** the system writes a plan noting it
   could not interpret the file and suggests the user review it manually.

---

### User Story 4 — Action Logging (Priority: P4)

As a user, I want every system action (file moves, reasoning runs,
errors) logged to `Logs/` so that I can audit what the AI Employee did.

**Why this priority**: Observability from day one builds trust and
enables debugging. Without logs, failures are invisible.

**Independent Test**: Trigger any of the above stories, verify a log
entry exists in `Logs/YYYY-MM-DD.json` with the correct fields.

**Acceptance Scenarios**:

1. **Given** the watcher moves a file from `Inbox/` to `Needs_Action/`,
   **Then** a log entry is written with fields: timestamp, action_type
   ("file_move"), source, destination, result ("success").
2. **Given** the reasoning loop processes a file, **Then** a log entry
   is written with: timestamp, action_type ("reasoning"), input_file,
   output_file, result.
3. **Given** an error occurs (e.g., permission denied on file move),
   **Then** a log entry is written with action_type, error message, and
   result ("error").

---

### Edge Cases

- What happens when the vault folder is on a network drive with high
  latency? **Assumption**: Bronze tier assumes local filesystem only.
  Network drives are out of scope.
- What happens when two watcher instances run simultaneously?
  **Assumption**: Only one watcher instance runs at a time. The watcher
  MUST use a lockfile to prevent duplicate instances.
- What happens when disk space is full? The watcher MUST log an error
  and pause rather than silently failing.
- What happens when a file is dropped into `Inbox/` while another file
  with the same name is already in `Needs_Action/`? The timestamp prefix
  ensures uniqueness — no collision possible.

## Clarifications

### Session 2026-02-20

- Q: Should the Obsidian vault be separate from the project repo or inside it? → A: Separate directory (e.g., `~/AI_Employee_Vault/`). The code repo (`Digital-FTE`) holds source code for watchers/scripts; the vault is where the AI Employee operates. Claude Code is pointed at the vault via `--cwd` or by running from within it.
- Q: How should the reasoning loop be triggered at Bronze tier? → A: Continuous Python orchestrator (`orchestrator.py`) that polls `Needs_Action/` on a configurable interval (default 30-60s) and invokes Claude Code when files appear. Runs as a persistent background process. This matches the hackathon's Orchestrator pattern and scales naturally into Silver/Gold tiers.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a vault initialization script that
  accepts a target path (defaulting to `~/AI_Employee_Vault/`) and
  creates all required folders idempotently. The vault is a standalone
  Obsidian vault, separate from the code repository.
- **FR-002**: System MUST run a filesystem watcher as a background
  process that monitors `Inbox/` for new files.
- **FR-003**: Watcher MUST move files from `Inbox/` to `Needs_Action/`
  with a `YYYY-MM-DD-HHMMSS-` timestamp prefix.
- **FR-004**: Watcher MUST process pre-existing `Inbox/` files on
  startup (catch-up).
- **FR-005**: Watcher MUST use a lockfile to prevent duplicate instances.
- **FR-006**: System MUST provide a persistent orchestrator that polls
  `Needs_Action/` on a configurable interval (default 30-60s) and
  invokes Claude Code to reason over found files, generating plans in
  `Plans/` and moving processed files to `In_Progress/`.
- **FR-007**: System MUST log every action (file move, reasoning run,
  error) to `Logs/YYYY-MM-DD.json` in structured JSON format.
- **FR-008**: System MUST handle errors gracefully — log them, skip the
  problematic item, and continue processing remaining items.
- **FR-009**: Vault initialization MUST create a `Company_Handbook.md`
  stub in the vault root with placeholder sections for rules and
  auto-approve thresholds.
- **FR-010**: Watcher MUST be startable and stoppable via simple CLI
  commands.

### Key Entities

- **Task File**: A markdown file representing something the AI Employee
  should reason about. Key attributes: original filename, content,
  timestamp of arrival, source folder, current status (inbox → needs
  action → in progress → done).
- **Plan File**: A markdown file containing Claude's reasoning and
  recommended action for a given task. Key attributes: reference to
  source task file, reasoning text, recommended action, confidence level.
- **Log Entry**: A structured record of a system action. Key attributes:
  timestamp, action_type, actor (watcher/reasoning/system), source,
  destination, parameters, result.
- **Company Handbook**: A user-editable configuration file defining
  rules, thresholds, and preferences that Claude references during
  reasoning.

### Assumptions

- Bronze tier targets local development only (single machine, local
  filesystem). The vault lives in a standalone directory (e.g.,
  `~/AI_Employee_Vault/`), separate from the `Digital-FTE` code repo.
- The user has Python 3.13+ and `uv` installed.
- The user has Claude Code CLI installed and authenticated.
- Obsidian is installed but vault creation is handled by our script, not
  by Obsidian itself.
- No external API integrations at Bronze tier (no Gmail, WhatsApp, bank,
  or MCP servers).
- The reasoning loop is invoked by a persistent Python orchestrator that
  polls `Needs_Action/` on a configurable interval (default 30-60s) and
  invokes Claude Code as a subprocess when files are found.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Vault setup completes in under 5 seconds and all 9
  required folders exist afterward.
- **SC-002**: Files dropped into `Inbox/` appear in `Needs_Action/`
  within 5 seconds of the watcher detecting them.
- **SC-003**: The watcher runs continuously for 1 hour without crashing
  or missing files.
- **SC-004**: Every file in `Needs_Action/` produces a corresponding
  plan in `Plans/` after the reasoning loop runs.
- **SC-005**: 100% of system actions (moves, reasoning, errors) have
  a corresponding log entry in `Logs/`.
- **SC-006**: The system recovers gracefully from at least 3 error
  scenarios (malformed file, permission error, empty file) without
  crashing.
- **SC-007**: A new user can go from zero to a working Bronze system
  (vault + watcher + first reasoning run) in under 15 minutes following
  documentation.
