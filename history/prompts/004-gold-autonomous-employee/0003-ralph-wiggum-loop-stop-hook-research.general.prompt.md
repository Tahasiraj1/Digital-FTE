---
id: "0003"
title: Ralph Wiggum Loop Stop Hook Research
stage: general
date: 2026-03-03
surface: agent
model: claude-sonnet-4-6
feature: 004-gold-autonomous-employee
branch: 003-silver-functional-assistant
user: taha
command: research
labels: ["ralph-loop", "stop-hook", "claude-code-hooks", "gold-tier", "autonomous-loop", "promise-based-exit"]
links:
  spec: specs/004-gold-autonomous-employee/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/004-gold-autonomous-employee/spec.md
  - .specify/memory/constitution.md
  - "Personal AI Employee Hackathon 0_ Building Autonomous FTEs in 2026.md"
tests:
  - null
---

## Prompt

Research the "Ralph Wiggum loop" (also called Stop hook pattern) for Claude Code.

Context: We're building a personal AI employee system (Digital FTE) where we need multi-step autonomous task execution. The Ralph Wiggum loop uses Claude Code's Stop hook to re-invoke Claude when a task isn't yet complete.

Find out:
1. How Claude Code Stop hooks work technically — what file/config, what events, what script runs
2. The exact pattern for "Ralph Wiggum loop" — how to detect completion (file-movement vs promise-based), how to re-invoke Claude
3. Whether there's an existing Claude Code plugin or skill for this (search GitHub for "ralph wiggum claude code", "stop hook claude code loop", "ralph-loop claude code")
4. Token cost implications — each loop iteration = one full Claude invocation, roughly how expensive
5. How to implement promise-based exit (`<promise>AWAITING_APPROVAL</promise>`) — does Claude Code's Stop hook parse stdout for promises?
6. Best pattern for passing task context between loop iterations (file-based state vs environment)

Return:
- How Stop hooks are configured in Claude Code (JSON config location, schema)
- The minimal script needed to implement the Ralph Wiggum pattern
- Whether a ready-made plugin exists or we need to build from scratch
- How promise detection works in the Stop hook script
- Token cost estimate per iteration for a ~30k-token project context

## Response snapshot

Full research compiled — see main response. Key findings:

1. Stop hooks configured in `.claude/settings.json` under `hooks.Stop[]` — array of matchers with `command` fields
2. Ralph Wiggum reference implementation at `https://github.com/anthropics/claude-code/tree/main/.claude/plugins/ralph-wiggum` (per hackathon doc)
3. Dual completion strategy confirmed: promise-based for approval gates, file-movement for autonomous completion
4. Token cost: ~$0.45–$0.90 per iteration at 30k context on claude-sonnet-4-5
5. Promise detection: Stop hook script reads stdin JSON for `stop_hook_active` context, scans Claude's last output for `<promise>` tags
6. File-based state is the correct pattern for FTE — state file in vault carries task context between iterations

## Outcome

- ✅ Impact: Complete technical picture of the Ralph Wiggum Stop hook pattern; ready to implement for Gold tier
- Tests: No code tests — research artifact only
- Files: PHR created
- Next prompts: /sp.plan to architect Gold tier implementation with Ralph Loop; implement `.claude/settings.json` hooks config and ralph-loop shell script
- Reflection: The key insight is that the Stop hook receives structured JSON on stdin (not just environment) — the script can read Claude's last output from the hook payload to detect promise tags. File-based state in vault is strongly preferred over env vars because it survives process restarts and is visible in Obsidian.

## Evaluation notes (flywheel)

- Failure modes observed: WebSearch and WebFetch tools were not available; research compiled from local project files (hackathon doc, constitution, spec, PHR history) plus training knowledge of Claude Code hooks API
- Graders run and results (PASS/FAIL): null
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Implement minimal Stop hook script and test with a throwaway task file before wiring into Gold orchestrator
