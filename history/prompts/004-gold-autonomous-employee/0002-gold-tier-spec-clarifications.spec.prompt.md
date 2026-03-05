---
id: "0002"
title: Gold Tier Spec Clarifications
stage: spec
date: 2026-03-03
surface: agent
model: claude-sonnet-4-6
feature: 004-gold-autonomous-employee
branch: 004-gold-autonomous-employee
user: taha
command: /sp.clarify
labels: ["gold-tier", "ralph-loop", "agent-browser", "odoo", "ceo-briefing", "clarification"]
links:
  spec: specs/004-gold-autonomous-employee/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/004-gold-autonomous-employee/spec.md
tests:
  - null
---

## Prompt

/sp.clarify — 5 clarification questions answered for Gold tier spec

## Response snapshot

5 clarification questions asked and answered, spec updated with each decision:

1. **Ralph Loop approval pauses** → Dual completion strategy: promise-based (`<promise>AWAITING_APPROVAL</promise>`) at approval gates; file-movement (`Done/`) for autonomous steps. Executor drops continuation task after dispatching approved action.

2. **agent-browser session model** → On-demand launch per approved action. No persistent daemon. Sessions saved to `~/.config/fte/`, loaded at launch. FB/IG are outbound-only so daemon adds no value.

3. **Odoo deployment** → Docker (docker-compose). Odoo 19+ + PostgreSQL in isolated containers. Portable to cloud VM at Platinum tier.

4. **CEO Briefing trigger** → Orchestrator-internal scheduler. Tracks last-run time in `Vault/briefing_state.json`, self-triggers on next poll cycle after scheduled time. No cron or systemd timer needed.

5. **Cross-domain chain cap** → 3 downstream actions. Conservative for initial implementation. Cap stored as config value — uncapped mode deferred to future iteration.

## Outcome

- ✅ Impact: All 5 critical ambiguities resolved; spec is now unambiguous and implementation-ready
- 🧪 Tests: No code tests — spec clarification only
- 📁 Files: specs/004-gold-autonomous-employee/spec.md updated (Clarifications section added, FR-002/004/014/019 updated, Assumptions 7/9/11 updated)
- 🔁 Next prompts: /sp.plan to design implementation architecture
- 🧠 Reflection: Dual completion strategy for Ralph Loop is the key architectural insight — prevents token waste during approval waits while keeping the loop pattern clean

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): null
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): run /sp.plan to validate architecture against these decisions
