---
id: 001
title: Initial FTE Constitution
stage: constitution
date: 2026-02-20
surface: agent
model: claude-opus-4-6
feature: none
branch: master
user: taha
command: /sp.constitution
labels: ["constitution", "project-setup", "principles"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
tests:
  - none
---

## Prompt

Clearly I don't have exact roadmap about this project in my mind, and I don't even know all the tools we're gonna use for this, that's why we are gonna write constitutation, and specification in an iterative way so everything becomes clear. For now I need you to write constitution based on the context about this project you got from @"Personal AI Employee Hackathon 0_ Building Autonomous FTEs in 2026.md"

## Response snapshot

Created the initial v1.0.0 constitution for the Personal AI Employee (FTE) project at `.specify/memory/constitution.md`. Derived 8 core principles from the hackathon blueprint: (I) Local-First Privacy, (II) Human-in-the-Loop Safety (NON-NEGOTIABLE), (III) Perception-Reasoning-Action Pipeline, (IV) Agent Skill Architecture, (V) Security by Default, (VI) Observability & Auditability, (VII) Autonomous Persistence (Ralph Wiggum Pattern), (VIII) Incremental Delivery & Iterative Scope. Also defined Technology Stack & Constraints, Development Workflow (spec-driven, watcher-first, dry-run gate), and Governance sections. Two TODOs deferred: tier target declaration and Odoo integration decision.

## Outcome

- ✅ Impact: Foundation governance document established for all future specs and plans
- 🧪 Tests: N/A (governance document, not code)
- 📁 Files: .specify/memory/constitution.md (created v1.0.0)
- 🔁 Next prompts: /sp.specify for first feature (likely Bronze tier vault setup), declare tier target
- 🧠 Reflection: User explicitly wants iterative approach — constitution left Gold/Platinum scope deferred as TODOs rather than speculating

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Manual validation PASS — no unresolved placeholders, all principles declarative and testable
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Run /sp.specify for Bronze tier vault+watcher feature
