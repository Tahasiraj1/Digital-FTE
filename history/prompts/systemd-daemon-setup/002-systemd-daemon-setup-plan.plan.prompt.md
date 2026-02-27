---
id: "002"
title: Systemd Daemon Setup Implementation Plan
stage: plan
date: 2026-02-23
surface: agent
model: claude-sonnet-4-6
feature: systemd-daemon-setup
branch: 002-systemd-daemon-setup
user: Tahasiraj1
command: /sp.plan
labels: ["systemd","daemon","process-management","deploy","bash","WSL2"]
links:
  spec: specs/002-systemd-daemon-setup/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-systemd-daemon-setup/plan.md
  - specs/002-systemd-daemon-setup/research.md
  - specs/002-systemd-daemon-setup/data-model.md
  - specs/002-systemd-daemon-setup/quickstart.md
  - specs/002-systemd-daemon-setup/contracts/deploy-interface.md
  - history/prompts/systemd-daemon-setup/002-systemd-daemon-setup-plan.plan.prompt.md
tests:
  - null
---

## Prompt

/sp.plan

## Response snapshot

Generated full implementation plan for `002-systemd-daemon-setup`. Two research agents dispatched and completed:
- Research 1: systemd best practices (7 questions — system vs user services, restart policy, environment variables, WantedBy target, WorkingDirectory, service ordering, daemon-reload)
- Research 2: uv PATH detection (5 questions — install locations, command -v vs which, sudo context, fallback probe, auto-sync behaviour)

**Key decisions**:
1. System services (`/etc/systemd/system/`) with `User=` directive — more reliable than user services on WSL2 (no linger requirement)
2. uv absolute path baked in at install time via `command -v uv` + fallback probe
3. Unit files generated inline via heredoc in install.sh (no separate template files)
4. Soft dependency: orchestrator uses `After=fte-watcher.service` + `Wants=fte-watcher.service`
5. Restart policy: `on-failure`, `RestartSec=5s`, `StartLimitBurst=5`, `StartLimitIntervalSec=60s` — all in [Service]
6. Explicit `Environment=HOME=` in unit file (system services start with HOME=/ without it)

**Artifacts generated**:
- plan.md — component design, unit file structure, install.sh flow, find_uv() fallback probe
- research.md — 7 decisions with rationale and alternatives
- data-model.md — SystemdUnitFile, DeployScript, UninstallScript, ServiceState entities
- contracts/deploy-interface.md — install.sh and uninstall.sh CLI contracts with exact output format
- quickstart.md — 7-step deploy guide including crash-recovery and reboot tests

**Constitution check**: All 8 principles PASS. Justified deviation: using systemd instead of PM2 (constitution recommendation) because systemd 255 is confirmed available and more reliable for WSL2 boot.

**Source structure**: New `deploy/` directory with `install.sh` and `uninstall.sh`. Zero changes to `src/` or `tests/`.

## Outcome

- ✅ Impact: Complete plan ready for /sp.tasks. All unknowns resolved by research agents.
- 🧪 Tests: No tests yet — plan stage. Testing is manual (systemctl status, kill -9, wsl --shutdown).
- 📁 Files: 5 new artifact files
- 🔁 Next prompts: /sp.tasks, /sp.implement
- 🧠 Reflection: The HOME env var requirement in unit files is a silent failure mode — services start, uv runs, but fails to find its cache. Worth calling out explicitly in tasks.

## Evaluation notes (flywheel)

- Failure modes observed: none at plan stage
- Graders run and results (PASS/FAIL): constitution check — all 8 PASS (1 justified deviation)
- Prompt variant (if applicable): null
- Next experiment: null
