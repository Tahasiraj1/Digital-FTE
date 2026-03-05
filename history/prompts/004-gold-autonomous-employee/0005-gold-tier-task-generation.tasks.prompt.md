---
id: "0005"
title: Gold Tier Task Generation
stage: tasks
date: 2026-03-03
surface: agent
model: claude-sonnet-4-6
feature: 004-gold-autonomous-employee
branch: 004-gold-autonomous-employee
user: taha
command: /sp.tasks
labels: ["gold-tier", "ralph-loop", "odoo", "facebook", "instagram", "ceo-briefing", "tasks"]
links:
  spec: specs/004-gold-autonomous-employee/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/004-gold-autonomous-employee/tasks.md
tests:
  - tests/unit/test_ralph_loop.py
  - tests/unit/test_odoo_actions.py
  - tests/integration/test_ralph_loop_e2e.py
  - tests/integration/test_gold_chain.py
---

## Prompt

/sp.tasks

## Response snapshot

Generated `specs/004-gold-autonomous-employee/tasks.md` with 27 tasks across 8 phases for the Gold tier implementation.

Phase breakdown:
- Phase 1 (Setup): T001–T004 — docker-compose.odoo.yml, .mcp.json, Stop hook config, install-gold.sh
- Phase 2 (Foundational — Ralph Loop): T005–T009 — ralph_loop.py, ralph-loop.sh, orchestrator extension, executor extension, unit tests
- Phase 3 (US1 — Ralph Loop E2E): T010–T011 — ralph-loop skill, integration test
- Phase 4 (US2 — Odoo): T012–T015 — odoo.py action handler, odoo-invoice skill, routing, unit tests
- Phase 5 (US3 — Social): T016–T019 — facebook.py, instagram.py, social-post skill, image_required guard
- Phase 6 (US4 — CEO Briefing): T020–T022 — vault init, scheduler impl, ceo-briefing skill
- Phase 7 (US5 — Cross-Domain): T023–T024 — chain cap enforcement, integration test
- Phase 8 (Polish): T025–T027 — dashboard Gold metrics, handbook, smoke test

## Outcome

- ✅ Impact: 27 implementation-ready tasks, each with exact file paths; maps directly to plan.md phase structure
- 🧪 Tests: 4 test files specified (test_ralph_loop.py, test_odoo_actions.py, test_ralph_loop_e2e.py, test_gold_chain.py)
- 📁 Files: tasks.md created at specs/004-gold-autonomous-employee/tasks.md
- 🔁 Next prompts: /sp.implement to execute tasks; /sp.adr ralph-loop-dual-completion before implementing T006
- 🧠 Reflection: Phase 2 is the critical-path bottleneck — all 5 user stories block on it. Ralph Loop Stop hook guard (exit 0 if no ralph_state.json) is the most important safety detail in T006.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): format validation — all 27 tasks have checkbox + ID + description + file path
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): run /sp.implement starting at T001 to validate task granularity is correct for single-agent implementation
