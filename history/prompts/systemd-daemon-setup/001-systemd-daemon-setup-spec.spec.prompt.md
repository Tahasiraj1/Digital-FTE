---
id: "001"
title: Systemd Daemon Setup Spec Creation
stage: spec
date: 2026-02-23
surface: agent
model: claude-sonnet-4-6
feature: systemd-daemon-setup
branch: 002-systemd-daemon-setup
user: Tahasiraj1
command: /sp.specify
labels: ["systemd","daemon","process-management","24/7","watcher","orchestrator","WSL2"]
links:
  spec: specs/002-systemd-daemon-setup/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-systemd-daemon-setup/spec.md
  - specs/002-systemd-daemon-setup/checklists/requirements.md
  - history/prompts/systemd-daemon-setup/001-systemd-daemon-setup-spec.spec.prompt.md
tests:
  - null
---

## Prompt

/sp.specify Add systemd service files and a deploy script so the watcher and orchestrator run 24/7 on WSL2 without manual terminal sessions, with auto-restart on crash and auto-start on boot.

## Response snapshot

Created feature branch `002-systemd-daemon-setup` and wrote spec at `specs/002-systemd-daemon-setup/spec.md`.

Spec covers 4 user stories:
- **US1 (P1)**: One-Command Deploy — `deploy/install.sh` installs, enables, and starts both services in under 30 seconds
- **US2 (P2)**: Auto-Recovery from Crash — services restart within 5 seconds of unclean exit; backoff after 5 failures per 60 seconds
- **US3 (P3)**: Status and Log Inspection — `systemctl status` and `journalctl` show useful output
- **US4 (P4)**: Clean Uninstall — `deploy/uninstall.sh` removes all traces idempotently

13 functional requirements defined (FR-001–FR-013), covering: unit file installation, idempotency, dynamic path detection (uv binary, vault path, project dir), crash recovery limits, journal logging, systemd availability check.

7 measurable success criteria defined (SC-001–SC-007), including: zero-action reboot recovery, 5-second crash recovery, 30-second deploy time, end-to-end task processing confirmed post-reboot.

Key assumptions documented: systemd 255 confirmed running (user verified), services run as non-root user, vault defaulted to ~/AI_Employee_Vault, orchestrator interval defaults to 30s.

All checklist items pass — spec is ready for `/sp.plan`.

## Outcome

- ✅ Impact: Feature scoped, 4 user stories defined, all FRs testable, edge cases identified (system PATH vs shell PATH pitfall explicitly called out in FR-007)
- 🧪 Tests: No tests yet — spec stage
- 📁 Files: 2 new files (spec.md, checklists/requirements.md)
- 🔁 Next prompts: `/sp.plan`, `/sp.tasks`, `/sp.implement`
- 🧠 Reflection: The system PATH vs user shell PATH difference in WSL2 is a critical detail that would cause silent service startup failures if not explicitly required — worth calling out in the spec rather than leaving to planning.

## Evaluation notes (flywheel)

- Failure modes observed: none at spec stage
- Graders run and results (PASS/FAIL): spec quality checklist — all 14 items PASS
- Prompt variant (if applicable): null
- Next experiment: null
