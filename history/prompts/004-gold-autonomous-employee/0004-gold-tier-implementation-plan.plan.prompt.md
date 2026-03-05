---
id: "0004"
title: Gold Tier Implementation Plan
stage: plan
date: 2026-03-03
surface: agent
model: claude-sonnet-4-6
feature: 004-gold-autonomous-employee
branch: 004-gold-autonomous-employee
user: taha
command: /sp.plan
labels: ["gold-tier", "ralph-loop", "odoo", "facebook", "instagram", "agent-browser", "ceo-briefing", "architecture"]
links:
  spec: specs/004-gold-autonomous-employee/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/004-gold-autonomous-employee/plan.md
  - specs/004-gold-autonomous-employee/research.md
  - specs/004-gold-autonomous-employee/data-model.md
  - specs/004-gold-autonomous-employee/quickstart.md
  - specs/004-gold-autonomous-employee/contracts/approval-schemas.md
  - specs/004-gold-autonomous-employee/contracts/mcp-config.md
tests:
  - null
---

## Prompt

/sp.plan

## Response snapshot

Full Gold tier implementation plan generated across 5 Phase 0 research areas and Phase 1 design artifacts:

**Research resolved (Phase 0)**:
1. Ralph Wiggum Stop hook — Claude Code `hooks.Stop` config, dual-completion bash script (~80 lines), `ralph_state.json` schema, ~$0.10–$0.12/iteration cost
2. agent-browser — `npm install -g agent-browser`, `--session-name` for persistent sessions, subprocess integration pattern, `~/.agent-browser/sessions/` storage
3. Odoo MCP — `mcp-odoo-adv` via npx, docker-compose.odoo.yml (Odoo 17 now, upgrade to 19 when Docker Hub tag available), key JSON-RPC endpoints documented
4. Continuation task pattern — `ralph_loop_id` on approval files triggers executor to drop `CONTINUATION_*.md` after dispatch
5. Briefing scheduler — `_check_briefing_schedule()` in orchestrator, `Vault/briefing_state.json` state

**Artifacts generated (Phase 1)**:
- `plan.md` — full architecture with 5 implementation phases, constitution check, risk analysis
- `research.md` — all research findings with decisions and rationale
- `data-model.md` — 7 entities, state transitions, new log action types
- `quickstart.md` — setup guide (Odoo Docker, agent-browser auth, Stop hook config)
- `contracts/approval-schemas.md` — frontmatter schemas for all new approval types
- `contracts/mcp-config.md` — Odoo MCP and agent-browser config

**5 implementation phases**:
1. Ralph Loop Foundation (blocks all others)
2. Odoo Integration
3. Facebook & Instagram Integration
4. CEO Briefing
5. Integration & Audit Logging

## Outcome

- ✅ Impact: Complete Gold tier architecture with all 5 hackathon requirements designed and unambiguous; implementation-ready
- 🧪 Tests: No code tests — plan artifact only; test files listed in project structure
- 📁 Files: plan.md, research.md, data-model.md, quickstart.md, contracts/ (2 files) created
- 🔁 Next prompts: /sp.tasks to generate actionable task list; /sp.adr ralph-loop-dual-completion to document the key architectural decision
- 🧠 Reflection: The Ralph Loop Stop hook guard (exit 0 if no ralph_state.json) is the most critical safety detail — without it, every normal orchestrator invocation would re-inject unexpectedly. Also noted: odoo:19 Docker tag not yet on Docker Hub — plan with odoo:17, upgrade path documented.

## Evaluation notes (flywheel)

- Failure modes observed: agent-browser research agent blocked (WebSearch/WebFetch denied); resolved by main agent fetching agent-browser.dev and /sessions directly
- Graders run and results (PASS/FAIL): constitution check all-pass (8/8 principles)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): run /sp.tasks to validate phase breakdown produces implementable task granularity
