# Implementation Plan: Systemd Daemon Setup

**Branch**: `002-systemd-daemon-setup` | **Date**: 2026-02-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-systemd-daemon-setup/spec.md`

---

## Summary

Install two systemd system services (`fte-watcher` and `fte-orchestrator`) that run the Bronze tier pipeline 24/7 without manual terminal sessions. A `deploy/install.sh` script detects all machine-specific paths at install time (uv binary, vault path, project root, username), generates unit files with those absolute paths baked in, and registers them with systemd. Both services auto-restart on crash and auto-start on WSL2 boot. A companion `deploy/uninstall.sh` cleanly removes both services.

---

## Technical Context

**Language/Version**: Bash (deploy scripts)
**Primary Dependencies**: systemd 255 (confirmed available), uv (resolved at install time)
**Storage**: `/etc/systemd/system/` (two unit files written at deploy time)
**Testing**: Manual verification via `systemctl status`; crash-recovery test via `kill -9`; reboot test via `wsl --shutdown`
**Target Platform**: Linux WSL2, Ubuntu, systemd 255
**Project Type**: Infrastructure/deployment — no changes to `src/`
**Performance Goals**: Services start within 10 seconds of WSL2 boot; restart within 5 seconds of crash
**Constraints**: No new runtime dependencies; no changes to existing Python source; scripts require `sudo` (writes to `/etc/systemd/system/`)
**Scale/Scope**: 2 scripts, 2 generated unit files, 1 new `deploy/` directory

---

## Constitution Check

*GATE: Evaluated before Phase 0. Re-evaluated after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Local-First Privacy | ✅ PASS | No data leaves local machine. Service files manage local processes only. |
| II. HITL Safety (NON-NEGOTIABLE) | ✅ PASS | Approval workflow in vault is unchanged. Daemons run the same orchestrator code — HITL is enforced at the application layer, not here. |
| III. Perception-Reasoning-Action | ✅ PASS | This feature makes the existing watcher and orchestrator always-on. It does not change their behaviour or bypass any layer. |
| IV. Agent Skill Architecture | ✅ N/A | Infrastructure feature; no AI skills involved. |
| V. Security by Default | ✅ PASS | Services run as non-root user (`User=` directive). No secrets in unit files. No credentials touched. |
| VI. Observability & Auditability | ✅ PASS | `StandardOutput=journal` + `StandardError=journal` captures all output. Existing JSONL vault logging continues unchanged. |
| VII. Ralph Wiggum Loop | ✅ N/A | Deferred to Gold tier. Not relevant here. |
| VIII. Incremental Delivery | ✅ PASS | Minimal Bronze-tier infrastructure improvement. Zero changes to src/. Smallest viable diff. |

**Constitution tech stack note**: Constitution recommends "PM2 (recommended) or supervisord" for process management. We are using systemd instead. This is a **justified deviation**:
- User confirmed systemd 255 is running on their machine
- Systemd is the native Linux process supervisor — no additional tool (Node.js, npm, supervisord package) required
- Systemd provides superior WSL2 boot-time reliability (no linger requirement)
- The constitution lists PM2 as "recommended" not "required"

**Gate result: PASS** — No violations. Justified deviation documented above.

---

## Project Structure

### Documentation (this feature)

```text
specs/002-systemd-daemon-setup/
├── plan.md                          # This file
├── research.md                      # 7 technology decisions
├── data-model.md                    # Service entity definitions
├── quickstart.md                    # 7-step deploy guide
├── contracts/
│   └── deploy-interface.md          # Script CLI contracts
├── checklists/
│   └── requirements.md              # Spec quality checklist
└── tasks.md                         # (created by /sp.tasks)
```

### Source Code (repository root)

```text
deploy/
├── install.sh     # Detects paths, generates + installs unit files, enables + starts services
└── uninstall.sh   # Stops, disables, removes unit files, reloads daemon

# No changes to:
src/               # Unchanged — existing fte package
tests/             # Unchanged — existing test suite
pyproject.toml     # Unchanged
```

**Structure Decision**: Pure infrastructure — a new top-level `deploy/` directory containing two shell scripts. No Python source changes. The unit files are generated inline by `install.sh` using heredoc substitution; they are not stored as static templates.

---

## Component Design

### install.sh — Execution Flow

```
1. check_prerequisites()
   ├── systemctl --version         → exit 1 if not found
   ├── find_uv()                   → exit 1 if not found
   ├── test -d $VAULT_PATH         → exit 1 if not found
   └── test -f pyproject.toml      → exit 1 if not found (must run from project root)

2. detect_paths()
   ├── USER_NAME = $(whoami)
   ├── HOME_DIR  = $HOME
   ├── UV_BIN    = $(find_uv)          → /home/taha/.local/bin/uv
   ├── UV_DIR    = $(dirname $UV_BIN)
   ├── PROJECT_DIR = $(realpath .)
   └── VAULT_PATH  = $HOME/AI_Employee_Vault

3. print_detected_paths()

4. install_service("fte-watcher")
   ├── generate unit file via heredoc with all paths substituted
   ├── sudo tee /etc/systemd/system/fte-watcher.service
   └── print confirmation

5. install_service("fte-orchestrator")
   ├── generate unit file via heredoc with all paths substituted
   └── sudo tee /etc/systemd/system/fte-orchestrator.service

6. sudo systemctl daemon-reload

7. sudo systemctl enable fte-watcher fte-orchestrator

8. sudo systemctl restart fte-watcher fte-orchestrator   # restart handles both first-run and re-install

9. print_summary_and_commands()
```

### find_uv() — Fallback Probe

```bash
find_uv() {
    command -v uv && return 0
    for candidate in \
        "${UV_INSTALL_DIR:-${XDG_BIN_HOME:-$HOME/.local/bin}}/uv" \
        "$HOME/.cargo/bin/uv" \
        "/usr/local/bin/uv" \
        "/usr/bin/uv"; do
        [[ -x "$candidate" ]] && echo "$candidate" && return 0
    done
    return 1
}
```

### Generated Unit File Structure

**fte-watcher.service**:
```ini
[Unit]
Description=FTE Filesystem Watcher
After=network.target
Wants=network.target

[Service]
Type=simple
User=<USER_NAME>
Group=<USER_NAME>
WorkingDirectory=<PROJECT_DIR>
ExecStart=<UV_BIN> run fte watch --path <VAULT_PATH>
Restart=on-failure
RestartSec=5s
StartLimitBurst=5
StartLimitIntervalSec=60s
Environment=HOME=<HOME_DIR>
Environment=PATH=<UV_DIR>:/usr/local/bin:/usr/bin:/bin
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**fte-orchestrator.service** (adds soft dependency on watcher):
```ini
[Unit]
Description=FTE Orchestrator
After=network.target fte-watcher.service
Wants=network.target fte-watcher.service

[Service]
... (same restart/env config as watcher)
ExecStart=<UV_BIN> run fte orchestrate --path <VAULT_PATH> --interval 30
```

---

## Key Design Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Service type | System service + User= | More reliable for WSL2 boot (no linger requirement) |
| 2 | uv path strategy | Absolute path baked in at install time | systemd PATH is minimal; `~/.local/bin` not present |
| 3 | Unit file generation | Inline heredoc in install.sh | Avoids separate template files requiring sed substitution |
| 4 | Orchestrator → Watcher dependency | Soft: After= + Wants= | They share vault but are independent processes |
| 5 | Restart policy | on-failure, 5s delay, 5/60s limit | Satisfies FR-004 + FR-005 exactly |
| 6 | HOME env var | Explicit in unit file | System services start with HOME=/ unless set |

---

## Risks

1. **WSL2 PATH contains spaces** (e.g., Windows mounts): `WorkingDirectory=/mnt/d/projects/FTE` — spaces in the path would require quoting in the unit file. The install script must handle this.
2. **uv auto-sync on first start**: If `.venv` is missing, `uv run` downloads dependencies — first start is slow and requires internet access. If offline at first start, the service enters crash-loop.
3. **sudo requirement may surprise users**: The script requires `sudo` to write to `/etc/systemd/system/`. The README and quickstart must make this explicit.
