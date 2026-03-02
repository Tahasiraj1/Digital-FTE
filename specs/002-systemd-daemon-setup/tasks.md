# Tasks: Systemd Daemon Setup

**Input**: Design documents from `/specs/002-systemd-daemon-setup/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/deploy-interface.md

**Tests**: Not explicitly requested in the feature spec. Manual verification via `systemctl status`, `kill -9`, and `wsl --shutdown` is specified in quickstart.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different functions/no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create the `deploy/` directory structure. No changes to `src/`.

- [x] T001 Create `deploy/` directory at repo root with empty `install.sh` and `uninstall.sh` files; add bash shebang (`#!/usr/bin/env bash`) and `set -euo pipefail` to both

**Checkpoint**: `deploy/install.sh` and `deploy/uninstall.sh` exist with shebangs. `bash -n deploy/install.sh` passes (no syntax errors).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared helper functions used by `install.sh`. MUST be complete before any user story work.

**⚠️ CRITICAL**: US1 depends on both of these functions being implemented and correct.

- [x] T002 Implement `find_uv()` function in `deploy/install.sh` — probe in this order: (1) `command -v uv`, (2) `${UV_INSTALL_DIR:-${XDG_BIN_HOME:-$HOME/.local/bin}}/uv`, (3) `$HOME/.cargo/bin/uv`, (4) `/usr/local/bin/uv`, (5) `/usr/bin/uv`; return absolute path on first match via `echo`; `return 1` if none found
- [x] T003 [P] Implement `check_prerequisites()` function in `deploy/install.sh` — run four checks in sequence: (1) `systemctl --version &>/dev/null` or exit with `ERROR: systemd is not available...`, (2) `find_uv` succeeds or exit with `ERROR: uv not found...`, (3) `test -d "$HOME/AI_Employee_Vault"` or exit with `ERROR: Vault not initialized...`, (4) `test -f pyproject.toml` or exit with `ERROR: Must be run from the FTE project root...`; each error prints to stderr and exits with code 1

**Checkpoint**: Source both functions via `bash -c 'source deploy/install.sh'` — `find_uv` returns the correct absolute uv path; `check_prerequisites` exits 0 when all conditions met, exits 1 with correct message when each condition is unmet.

---

## Phase 3: User Story 1 — One-Command Deploy (Priority: P1) 🎯 MVP

**Goal**: `sudo bash deploy/install.sh` installs, enables, and starts both FTE services in under 30 seconds.

**Independent Test**: Run `sudo bash deploy/install.sh` from project root. Both `systemctl status fte-watcher` and `systemctl status fte-orchestrator` show `Active: active (running)`. Run a second time — exits 0 with no errors (idempotent).

### Implementation for User Story 1

- [x] T004 [US1] Implement `detect_paths()` in `deploy/install.sh` — set `USER_NAME=$(whoami)`, `HOME_DIR=$HOME`, `UV_BIN=$(find_uv)`, `UV_DIR=$(dirname "$UV_BIN")`, `PROJECT_DIR=$(realpath .)`, `VAULT_PATH=$HOME/AI_Employee_Vault`; print each detected value with label per contracts/deploy-interface.md Section 1 output format (e.g., `  USER:        taha`)
- [x] T005 [P] [US1] Implement `install_watcher_unit()` in `deploy/install.sh` — use `sudo tee` with a heredoc to write `/etc/systemd/system/fte-watcher.service`; unit file MUST contain: `[Unit]` with `Description=FTE Filesystem Watcher`, `After=network.target`, `Wants=network.target`; `[Service]` with `Type=simple`, `User=$USER_NAME`, `Group=$USER_NAME`, `WorkingDirectory=$PROJECT_DIR`, `ExecStart=$UV_BIN run fte watch --path $VAULT_PATH`, `Restart=on-failure`, `RestartSec=5s`, `StartLimitBurst=5`, `StartLimitIntervalSec=60s`, `Environment=HOME=$HOME_DIR`, `Environment=PATH=$UV_DIR:/usr/local/bin:/usr/bin:/bin`, `StandardOutput=journal`, `StandardError=journal`; `[Install]` with `WantedBy=multi-user.target`; print `✓ Unit file written to /etc/systemd/system/fte-watcher.service`
- [x] T006 [P] [US1] Implement `install_orchestrator_unit()` in `deploy/install.sh` — identical structure to T005 except: `Description=FTE Orchestrator`, add `fte-watcher.service` to `After=` and `Wants=` in `[Unit]`, `ExecStart=$UV_BIN run fte orchestrate --path $VAULT_PATH --interval 30`; print `✓ Unit file written to /etc/systemd/system/fte-orchestrator.service`
- [x] T007 [US1] Implement `activate_services()` in `deploy/install.sh` — run in sequence: (1) `sudo systemctl daemon-reload` with print `✓ daemon-reload complete`, (2) `sudo systemctl enable fte-watcher.service fte-orchestrator.service` with print per service, (3) `sudo systemctl restart fte-watcher.service fte-orchestrator.service` (restart — not start — handles both first-run and re-install idempotently) with print per service
- [x] T008 [US1] Wire `main()` in `deploy/install.sh` — call functions in order: `check_prerequisites`, `detect_paths`, `install_watcher_unit`, `install_orchestrator_unit`, `activate_services`; print section headers (`[FTE Deploy] Detecting paths...` etc.) per contracts/deploy-interface.md; print final summary footer: `[FTE Deploy] Done. FTE is running 24/7.` followed by the three operational hint lines (status, logs, uninstall)

**Checkpoint**: `sudo bash deploy/install.sh` runs to completion. Both services active. Running again exits 0 with no duplicate errors.

---

## Phase 4: User Story 2 — Auto-Recovery from Crash (Priority: P2)

**Goal**: Both services restart within 5 seconds of a crash. Stop retrying after 5 failures in 60 seconds.

**Independent Test**: Get PID via `systemctl status fte-watcher | grep "Main PID"`, run `sudo kill -9 <pid>`, wait 6 seconds, confirm `systemctl status fte-watcher` shows `Active: active (running)` again.

### Implementation for User Story 2

- [x] T009 [US2] Audit and lock down restart policy in `deploy/install.sh` — verify that `StartLimitBurst=5` and `StartLimitIntervalSec=60s` appear in the `[Service]` section (NOT `[Unit]`) in BOTH `install_watcher_unit()` and `install_orchestrator_unit()`; add inline comment `# systemd v229+: StartLimit* must be in [Service], silently ignored in [Unit]`; verify `RestartSec=5s` is present (satisfies FR-004: restart within 5 seconds)

**Checkpoint**: Inspect installed unit file with `systemctl cat fte-watcher` — `StartLimitBurst` and `StartLimitIntervalSec` appear under `[Service]`. Kill the process and confirm restart in < 6 seconds.

---

## Phase 5: User Story 3 — Status and Log Inspection (Priority: P3)

**Goal**: `systemctl status` and `journalctl` produce useful, identifiable output for both services.

**Independent Test**: After install, run `journalctl -u fte-watcher --since "1 minute ago"` — output shows at least one line from the watcher (startup log or poll entry). Run `systemctl status fte-orchestrator` — shows `Active: active (running)` with uptime.

### Implementation for User Story 3

- [x] T010 [US3] Verify journal routing and description quality in `deploy/install.sh` — confirm `StandardOutput=journal` and `StandardError=journal` are present in both unit generators; ensure `Description=` strings are distinct and informative (`FTE Filesystem Watcher` vs `FTE Orchestrator`) so `journalctl` and `systemctl status` output clearly identifies which service is which

**Checkpoint**: `journalctl -u fte-watcher -n 5` shows FTE watcher log lines (not empty). `journalctl -u fte-orchestrator -n 5` shows orchestrator log lines. Both `systemctl status` outputs show correct Description fields.

---

## Phase 6: User Story 4 — Clean Uninstall (Priority: P4)

**Goal**: `sudo bash deploy/uninstall.sh` removes both services cleanly. Idempotent.

**Independent Test**: Run `sudo bash deploy/uninstall.sh`. Then `systemctl status fte-watcher` returns `Unit fte-watcher.service not found`. Run uninstall again — exits 0 with no errors.

### Implementation for User Story 4

- [x] T011 [US4] Implement `deploy/uninstall.sh` — add `check_systemd()` guard (same systemd check as T003); then in sequence: (1) print `[FTE Uninstall] Stopping services...`, stop each service with `sudo systemctl stop <name> 2>/dev/null || true`, print `✓ stopped (or was not running)`; (2) print `[FTE Uninstall] Disabling services...`, disable each with `|| true`, print confirmation; (3) print `[FTE Uninstall] Removing unit files...`, `sudo rm -f /etc/systemd/system/fte-watcher.service /etc/systemd/system/fte-orchestrator.service`, print confirmation per file; (4) `sudo systemctl daemon-reload`, print confirmation; (5) print `[FTE Uninstall] Done. FTE services removed.`
- [x] T012 [P] [US4] Verify idempotency of `deploy/uninstall.sh` — confirm every systemctl call uses `|| true` or `2>/dev/null` so the script exits 0 when services are not installed; confirm `rm -f` (not `rm`) is used so missing files don't cause errors; confirm script exits 0 in both "services existed" and "services never installed" cases

**Checkpoint**: Run uninstall when services are running → both removed. Run uninstall again immediately → exits 0, prints "or was not running" / "or did not exist" messages.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening and end-to-end validation.

- [x] T013 [P] Make both scripts executable — run `chmod +x deploy/install.sh deploy/uninstall.sh`; verify `set -euo pipefail` is present at the top of both files (ensures the script exits on any unhandled error, unbound variable, or pipe failure); verify both scripts pass `bash -n` (syntax check)
- [ ] T014 Run quickstart.md validation — execute all 7 steps from `specs/002-systemd-daemon-setup/quickstart.md` in order: (1) confirm systemd --version, (2) confirm uv on PATH, (3) run install.sh, (4) verify both services active, (5) drop a task file without a terminal and verify it is processed, (6) kill -9 crash recovery test, (7) wsl --shutdown reboot persistence test; document any deviations from expected output and fix

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (deploy/ dir must exist). BLOCKS Phase 3+
- **US1 (Phase 3)**: Depends on Phase 2 (uses find_uv + check_prerequisites)
- **US2 (Phase 4)**: Depends on Phase 3 (audits unit file content written in T005/T006)
- **US3 (Phase 5)**: Depends on Phase 3 (verifies journal routing set in T005/T006)
- **US4 (Phase 6)**: Depends on Phase 1 only (uninstall.sh is independent of install.sh)
- **Polish (Phase 7)**: Depends on all phases complete

### User Story Dependencies

- **US1 (P1)**: Foundational only — can start after Phase 2
- **US2 (P2)**: Depends on US1 (verifies restart policy placed correctly in US1's unit files)
- **US3 (P3)**: Depends on US1 (verifies journal routing in US1's unit files)
- **US4 (P4)**: Depends on Phase 1 only — can be developed in parallel with US1

### Within Each Phase

- T002 and T003 can run in parallel (different functions in same file — no conflict)
- T005 and T006 can run in parallel (different functions — watcher vs orchestrator unit)
- T011 and T012 can be written together (T012 is a hardening pass on T011)
- T013 can run in parallel with T014 after all phases complete

### Parallel Opportunities

```
Phase 2: T002 ║ T003
Phase 3: T004 → (T005 ║ T006) → T007 → T008
Phase 6: T011 → T012   (can start in parallel with Phase 3)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002, T003)
3. Complete Phase 3: US1 (T004–T008)
4. **STOP and VALIDATE**: `sudo bash deploy/install.sh` — both services running

This alone delivers the core value: zero-terminal 24/7 operation.

### Incremental Delivery

1. Phase 1–3: `install.sh` works → FTE runs 24/7 (MVP)
2. Phase 4: Crash recovery confirmed and locked in
3. Phase 5: Journal output verified and readable
4. Phase 6: `uninstall.sh` completes the lifecycle
5. Phase 7: Fully validated against quickstart

### Sequential Execution (Solo Developer)

T001 → T002 + T003 → T004 → T005 + T006 → T007 → T008 → T009 → T010 → T011 → T012 → T013 → T014

---

## Notes

- [P] tasks = no dependencies on each other; safe to develop in any order
- [Story] label maps each task to a specific user story for traceability
- No changes to `src/` — this is purely infrastructure on top of Bronze tier
- `sudo` is required for `install.sh` and `uninstall.sh` (writes to `/etc/systemd/system/`)
- Verify `bash -n <script>` passes after every task before running live
- The only code file for US1–US3 is `deploy/install.sh`; US4 is `deploy/uninstall.sh`
