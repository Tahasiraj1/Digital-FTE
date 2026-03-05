---
id: "0001"
title: Gold Tier Autonomous Employee Spec
stage: spec
date: 2026-03-02
surface: agent
model: claude-sonnet-4-6
feature: 004-gold-autonomous-employee
branch: 004-gold-autonomous-employee
user: taha
command: /sp.specify
labels: ["gold-tier", "odoo", "facebook", "instagram", "ralph-loop", "browser-automation", "ceo-briefing"]
links:
  spec: specs/004-gold-autonomous-employee/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/004-gold-autonomous-employee/spec.md
  - specs/004-gold-autonomous-employee/checklists/requirements.md
  - history/prompts/004-gold-autonomous-employee/0001-gold-tier-autonomous-employee-spec.spec.prompt.md
tests:
  - null
---

## Prompt

let's go for gold tier, spec it out based on our findings and official hackathon doc.

## Response snapshot

Created full Gold tier spec at `specs/004-gold-autonomous-employee/spec.md` on branch `004-gold-autonomous-employee`.

5 user stories defined:
1. **P1 — Ralph Wiggum Loop**: Multi-step autonomous task chains with file-movement-based completion detection
2. **P2 — Odoo Accounting**: Local Odoo 19+ via JSON-RPC MCP, invoice creation/send, business summary queries
3. **P3 — Facebook & Instagram**: Browser automation (agent-browser) for posting and engagement metrics; persistent sessions same pattern as WhatsApp
4. **P4 — CEO Briefing**: Autonomous weekly business audit report aggregating all domains, schedulable via systemd timer
5. **P5 — Cross-Domain Integration**: Chained actions spanning email + Odoo + social within a single Ralph Loop run

24 functional requirements across 5 domains. 10 success criteria. 10 assumptions including explicit ToS risk acceptance for FB/IG browser automation.

## Outcome

- ✅ Impact: Full Gold tier spec covering all 5 hackathon requirements (cross-domain, Odoo, FB/IG, Ralph Loop, CEO Briefing)
- 🧪 Tests: No code tests — spec artifact only
- 📁 Files: spec.md, checklists/requirements.md created
- 🔁 Next prompts: /sp.plan to architect implementation; /sp.clarify if any requirements need deeper detail
- 🧠 Reflection: Facebook/Instagram integration via agent-browser is the right call — avoids Meta API review entirely, same pattern as whatsapp-web.js already proven in Silver

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): checklist all-pass
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): run /sp.plan to validate architecture feasibility before committing to Odoo setup
