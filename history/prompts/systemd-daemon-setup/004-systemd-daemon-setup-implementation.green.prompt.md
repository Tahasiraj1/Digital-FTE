---
id: "004"
title: Systemd Daemon Setup Implementation
stage: green
date: 2026-02-23
surface: agent
model: claude-sonnet-4-6
feature: systemd-daemon-setup
branch: 002-systemd-daemon-setup
user: Tahasiraj1
command: /sp.implement
labels: ["systemd","daemon","deploy","bash","install","uninstall","WSL2"]
links:
  spec: specs/002-systemd-daemon-setup/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - deploy/install.sh
  - deploy/uninstall.sh
  - specs/002-systemd-daemon-setup/tasks.md
  - history/prompts/systemd-daemon-setup/004-systemd-daemon-setup-implementation.green.prompt.md
tests:
  - bash -n deploy/install.sh (PASS)
  - bash -n deploy/uninstall.sh (PASS)
---

## Prompt

/sp.implement Continue implementation.

## Response snapshot

Implemented 13 of 14 tasks (T001–T013). T014 is manual live validation left for user.

**deploy/install.sh** (188 lines):
- `find_uv()` — 5-location fallback probe (PATH → UV_INSTALL_DIR/XDG_BIN_HOME/.local/bin → .cargo/bin → /usr/local/bin → /usr/bin)
- `check_prerequisites()` — 4 guards (systemd, uv, vault dir, pyproject.toml); each exits 1 with clear message
- `detect_paths()` — resolves USER_NAME, HOME_DIR, UV_BIN, UV_DIR, PROJECT_DIR, VAULT_PATH at runtime; prints labeled output
- `install_watcher_unit()` — generates fte-watcher.service via heredoc with variable substitution; all absolute paths baked in
- `install_orchestrator_unit()` — generates fte-orchestrator.service; adds `After=fte-watcher.service` + `Wants=fte-watcher.service` soft dependency
- `activate_services()` — daemon-reload, enable, restart (idempotent) both services with step confirmations
- `main()` — wires all functions with section headers per contracts/deploy-interface.md

Both unit files contain:
- `Restart=on-failure`, `RestartSec=5s` (FR-004: restart within 5s)
- `StartLimitBurst=5`, `StartLimitIntervalSec=60s` in `[Service]` (not [Unit] — systemd v229+ requirement per research Decision 5)
- `Environment=HOME=` and `Environment=PATH=` (explicit, not inherited)
- `StandardOutput=journal`, `StandardError=journal`
- `WantedBy=multi-user.target`

**deploy/uninstall.sh** (58 lines):
- `check_systemd()` guard
- Stops, disables, removes both services with `|| true` and `rm -f` for full idempotency
- daemon-reload after removal

Both scripts: `#!/usr/bin/env bash` + `set -euo pipefail`, `chmod +x`, `bash -n` syntax check passed.

## Outcome

- ✅ Impact: 2 scripts implement full 24/7 daemon lifecycle — install, crash recovery, log inspection, uninstall
- 🧪 Tests: bash -n syntax check PASS on both scripts. T014 (live validation) left for user per quickstart.md
- 📁 Files: 2 new files (deploy/install.sh, deploy/uninstall.sh), 1 updated (tasks.md — 13/14 tasks marked complete)
- 🔁 Next prompts: /sp.git.commit_pr, then live T014 validation per quickstart.md
- 🧠 Reflection: The heredoc variable expansion approach (<<EOF not <<'EOF') is the right choice — shell expands the machine-specific paths before writing to disk, so systemd never needs to do any PATH lookups at service start time.

## Evaluation notes (flywheel)

- Failure modes observed: none (syntax clean on both scripts)
- Graders run and results (PASS/FAIL): bash -n PASS × 2; grep verifications PASS (StartLimit* in [Service], journal routing, || true idempotency)
- Prompt variant (if applicable): null
- Next experiment: T014 live test — wsl --shutdown and kill -9 verification
