---
id: 004
title: Bronze Tier Implementation Plan
stage: plan
date: 2026-02-20
surface: agent
model: claude-opus-4-6
feature: bronze-vault-setup
branch: 001-bronze-vault-setup
user: taha
command: /sp.plan
labels: ["plan", "bronze-tier", "architecture", "vault", "watcher", "orchestrator"]
links:
  spec: specs/001-bronze-vault-setup/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-bronze-vault-setup/plan.md
  - specs/001-bronze-vault-setup/research.md
  - specs/001-bronze-vault-setup/data-model.md
  - specs/001-bronze-vault-setup/contracts/cli-interface.md
  - specs/001-bronze-vault-setup/quickstart.md
tests:
  - none
---

## Prompt

/sp.plan (no additional arguments)

## Response snapshot

Generated the full Bronze tier implementation plan with 5 artifacts: (1) research.md — 6 decisions covering watchdog vs polling, Claude invocation via subprocess -p, uv project management, JSONL logging, PID lockfiles, and manual process management at Bronze. (2) data-model.md — 6 entities (Vault structure, Task File, Plan File, Log Entry, Company Handbook, Lockfile) with schemas and state transitions. (3) contracts/cli-interface.md — 3 CLI commands (fte init, fte watch, fte orchestrate) with args, behavior, exit codes, and stdout formats. (4) quickstart.md — 9-step guide targeting <15 min setup time. (5) plan.md — full plan with Technical Context, Constitution Check (PASS with 2 justified deferrals), source code structure (6 modules under src/fte/), and component design for all 6 modules. Agent context updated in CLAUDE.md.

## Outcome

- ✅ Impact: Complete architecture defined — ready for task decomposition
- 🧪 Tests: N/A (plan phase, no code yet)
- 📁 Files: 5 artifacts created in specs/001-bronze-vault-setup/
- 🔁 Next prompts: /sp.tasks to generate implementation task list
- 🧠 Reflection: Constitution Check revealed 2 principles (Agent Skills, Ralph Wiggum) that are intentionally deferred to later tiers — documented as justified deferrals rather than violations.

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Constitution Check PASS (6 pass, 2 justified deferrals)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Generate tasks with /sp.tasks
