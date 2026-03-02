---
id: "0004"
title: Silver Tier ADR Review
stage: misc
date: 2026-02-27
surface: agent
model: claude-sonnet-4-6
feature: 003-silver-functional-assistant
branch: 003-silver-functional-assistant
user: taha
command: /sp.adr
labels: ["silver-tier","adr","service-topology","whatsapp","mcp","gmail","calendar","action-executor","hitl","architecture"]
links:
  spec: specs/003-silver-functional-assistant/spec.md
  ticket: null
  adr: history/adr/
  pr: null
files:
  - history/adr/0001-silver-tier-service-topology-three-separate-systemd-services.md
  - history/adr/0002-whatsapp-integration-whatsapp-web-js-over-playwright-and-baileys.md
  - history/adr/0003-local-mcp-servers-for-gmail-and-calendar-over-cloud-relay.md
  - history/adr/0004-action-execution-via-claude-subprocess-with-constrained-tool-access.md
tests:
  - none — adr stage
---

## Prompt

/sp.adr

## Response snapshot

Executed full /sp.adr workflow for Silver Tier — Functional Assistant.

Loaded plan.md, research.md, data-model.md, and contracts/ artifacts. Extracted 4 architecturally significant decision clusters from the Silver tier plan:

1. **Service Topology** — 3 new systemd services vs extending orchestrator (incompatible timeout/concurrency requirements)
2. **WhatsApp Integration** — whatsapp-web.js + LocalAuth vs raw Playwright vs Baileys (ToS, ban risk, session persistence)
3. **Local MCP Servers** — locally-run npm MCP packages vs cloud relay (Composio/Rube) vs native Python (data locality constraint)
4. **Action Execution** — claude -p subprocess with --allowedTools constraint vs direct Python API calls vs direct MCP JSON-RPC

Checked existing ADRs: none pre-existed for Silver tier. All 4 clusters pass the significance test (impact + alternatives + cross-cutting scope).

Created 4 ADR files via create-adr.sh, then filled all placeholders with full context, decision rationale, consequences (positive and negative), alternatives with rejection reasons, and cross-references.

Significance grader results (all PASS):
- ADR-0001: Clustered (3 new services), 3 alternatives, explicit pros/cons ✅
- ADR-0002: Clustered (library + session + QR + crash recovery), 2 alternatives, explicit pros/cons ✅
- ADR-0003: Clustered (Gmail MCP + Calendar MCP + config location + token storage), 3 alternatives, explicit pros/cons ✅
- ADR-0004: Clustered (dispatch mechanism + tool constraint + expiry thread + timeout), 3 alternatives, explicit pros/cons ✅

## Outcome

- ✅ Impact: 4 ADRs document all Silver tier architectural decisions — service topology, WhatsApp daemon, MCP integration, and HITL action execution are all formally recorded with alternatives and rationale
- 🧪 Tests: none — misc/adr stage
- 📁 Files: 0001, 0002, 0003, 0004 ADR files in history/adr/
- 🔁 Next prompts: /sp.tasks
- 🧠 Reflection: The most architecturally interesting decision is ADR-0004 — the key insight is that approval files contain free-text instructions (not structured parameters), so Python direct calls cannot replace Claude subprocess dispatch without reimplementing a rule engine. The WhatsApp IPC bridge (Python executor → Node.js watcher) remains the highest-risk interface in Silver and must be addressed early in /sp.tasks.

## Evaluation notes (flywheel)

- Failure modes observed: create-adr.sh requires --title flag (not positional arg); ADR-0003 and ADR-0004 files were created in previous session but left with template placeholders due to context compaction — filled in resumed session
- Graders run and results (PASS/FAIL): Significance test (impact + alternatives + scope) — all 4 PASS; clustering check — all 4 PASS (no over-granular atomic ADRs)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): /sp.tasks to generate atomic, testable implementation tasks for all 8 Silver phases
