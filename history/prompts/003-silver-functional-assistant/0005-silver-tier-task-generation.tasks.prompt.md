---
id: "0005"
title: Silver Tier Task Generation
stage: tasks
date: 2026-02-28
surface: agent
model: claude-sonnet-4-6
feature: 003-silver-functional-assistant
branch: 003-silver-functional-assistant
user: taha
command: /sp.tasks
labels: ["silver-tier","tasks","gmail-mcp","whatsapp","linkedin","calendar","hitl","agent-skills","executor"]
links:
  spec: specs/003-silver-functional-assistant/spec.md
  ticket: null
  adr: history/adr/0001-silver-tier-service-topology-three-separate-systemd-services.md
  pr: null
files:
  - specs/003-silver-functional-assistant/tasks.md
tests:
  - none — tasks stage
---

## Prompt

/sp.tasks Create tasks for silver tier, use context from this chat for tasks.

## Response snapshot

Generated `specs/003-silver-functional-assistant/tasks.md` — 68 tasks across 8 phases for the Silver Tier Functional Assistant.

Key chat context incorporated:
- Gmail MCP: Adapted from user's existing email-app (Python FastMCP) — strip multi-user OAuth, replace with local token file reader at `~/.config/fte/gmail_token.json`
- Calendar MCP: Custom Python FastMCP server (same pattern as Gmail)
- WhatsApp: `whatsapp-web.js` + `LocalAuth` Node.js daemon with HTTP IPC bridge on localhost:8766 for Python executor to call
- LinkedIn: Direct REST API `POST /v2/ugcPosts` from Python — no MCP needed
- 7 Agent Skills authored via `skill-creator` skill (already installed)
- Custom MCP servers required by hackathon (not third-party npm packages)

Phase structure:
- Phase 1 (T001–T006): Setup — deps, dirs, service stubs
- Phase 2 (T007–T025): Foundational — executor engine, Gmail MCP adaptation, Calendar MCP, OAuth setup
- Phase 3 (T026–T032): US1 Gmail Reply — MVP pipeline
- Phase 4 (T033–T042): US2 WhatsApp Detection & Reply
- Phase 5 (T043–T046): US3 Calendar Event Creation
- Phase 6 (T047–T052): US4 LinkedIn Post Publishing
- Phase 7 (T053–T060): US5 Agent Skills (7 SKILL.md files)
- Phase 8 (T061–T068): Polish — Dashboard.md, deploy scripts, E2E smoke test

MVP scope (working Gmail pipeline): T001–T018 + T024 + T026–T032 + T055 + T059 = 32 tasks

## Outcome

- ✅ Impact: 68 atomic, dependency-ordered tasks cover all 5 user stories and the full Silver tier pipeline — immediately executable by /sp.implement
- 🧪 Tests: none requested — quickstart.md provides manual verification steps for each user story
- 📁 Files: specs/003-silver-functional-assistant/tasks.md
- 🔁 Next prompts: /sp.implement | commit and PR 003
- 🧠 Reflection: The WhatsApp IPC bridge (Python executor → Node.js watcher via HTTP on localhost:8766) is the highest-risk interface — it's the only cross-runtime boundary. T038 (IPC bridge in watcher.js) and T040 (actions/whatsapp.py) should be validated together early. The Gmail MCP adaptation (T012–T018) reuses proven code from email-app — low risk, just OAuth layer stripping.

## Evaluation notes (flywheel)

- Failure modes observed: plan.md referenced npm MCP packages; chat context overrides this — tasks correctly use custom Python FastMCP servers instead; plan.md should be updated post-tasks to reflect this change
- Graders run and results (PASS/FAIL): All 68 tasks have checkbox + ID + file path; all US3–US5 tasks have [Story] label; parallelizable tasks marked [P]; phases follow Setup→Foundational→US1→US2→US3→US4→US5→Polish order — PASS
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): run /sp.implement starting from T001 with Phase 1 only to validate directory structure and dependency install before committing to full Silver build
