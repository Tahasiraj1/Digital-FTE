---
id: "003"
title: Systemd Daemon Setup Task Generation
stage: tasks
date: 2026-02-23
surface: agent
model: claude-sonnet-4-6
feature: systemd-daemon-setup
branch: 002-systemd-daemon-setup
user: Tahasiraj1
command: /sp.tasks
labels: ["systemd","daemon","tasks","deploy","bash","WSL2"]
links:
  spec: specs/002-systemd-daemon-setup/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-systemd-daemon-setup/tasks.md
  - history/prompts/systemd-daemon-setup/003-systemd-daemon-setup-tasks.tasks.prompt.md
tests:
  - null
---

## Prompt

/sp.tasks

## Response snapshot

Generated 14 tasks across 7 phases for `002-systemd-daemon-setup`.

**Phase breakdown**:
- Phase 1 Setup: T001 (1 task) — create deploy/ directory
- Phase 2 Foundational: T002–T003 (2 tasks) — find_uv() + check_prerequisites()
- Phase 3 US1 One-Command Deploy: T004–T008 (5 tasks) — detect_paths, watcher unit, orchestrator unit, systemctl activation, main() wiring
- Phase 4 US2 Auto-Recovery: T009 (1 task) — audit StartLimit* placement in [Service] section
- Phase 5 US3 Status/Logs: T010 (1 task) — verify journal routing and Description fields
- Phase 6 US4 Uninstall: T011–T012 (2 tasks) — uninstall.sh + idempotency hardening
- Phase 7 Polish: T013–T014 (2 tasks) — chmod + set -euo pipefail, quickstart validation

**Parallel opportunities**: T002‖T003 (foundational), T005‖T006 (unit file generators), T011 starts in parallel with Phase 3 (uninstall independent of install)

**MVP scope**: T001–T008 — deploy/install.sh complete; both services running 24/7

**Key specificity**: Every task includes exact function names, exact unit file directives, exact contracts/deploy-interface.md output format, and exact error message strings. Tasks are immediately executable by an LLM without additional context.

## Outcome

- ✅ Impact: 14 atomic, executable tasks covering all 4 user stories. MVP is T001–T008.
- 🧪 Tests: Not requested — manual verification via systemctl and kill -9
- 📁 Files: 1 new file (tasks.md)
- 🔁 Next prompts: /sp.implement
- 🧠 Reflection: US2 and US3 have minimal tasks (1 each) because their acceptance criteria are satisfied by US1's unit file content. The tasks are audit/verification rather than new code — correctly reflecting the spec's intent.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): format validation — all 14 tasks follow checkbox + ID + optional [P] + optional [Story] + description with file path
- Prompt variant (if applicable): null
- Next experiment: null
