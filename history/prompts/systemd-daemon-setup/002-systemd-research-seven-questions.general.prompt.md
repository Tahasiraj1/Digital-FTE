---
id: "002"
title: Systemd Research Seven Decision Questions
stage: general
date: 2026-02-23
surface: agent
model: claude-sonnet-4-6
feature: systemd-daemon-setup
branch: 002-systemd-daemon-setup
user: Tahasiraj1
command: research query
labels: ["systemd","WSL2","uv","service-unit","restart-policy","environment","After","Wants","daemon-reload"]
links:
  spec: specs/002-systemd-daemon-setup/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - history/prompts/systemd-daemon-setup/002-systemd-research-seven-questions.general.prompt.md
tests:
  - null
---

## Prompt

Research the following questions for a systemd service setup on WSL2 Ubuntu (systemd 255) that runs Python processes managed by `uv`. Return concise, decision-ready answers:

1. Should we use system services (/etc/systemd/system/) with User= directive, OR user services (~/.config/systemd/user/)? Which is more reliable for auto-start on WSL2 boot without an interactive login session? What are the tradeoffs?

2. What is the correct RestartSec, StartLimitBurst, StartLimitIntervalSec combination for a service that should restart on crash but stop retrying after 5 failures in 60 seconds?

3. Does a system service (with User= directive) inherit the user's HOME and PATH environment variables? How do we correctly set HOME inside the unit file for a non-root user?

4. Should WantedBy be multi-user.target or default.target for a system service that should start at boot?

5. For a service with ExecStart using `uv run fte watch`, does uv need WorkingDirectory to find pyproject.toml? What happens if WorkingDirectory is wrong?

6. What is the correct way to make one service start after another (soft dependency, not hard) in systemd — After= vs Requires= vs Wants=?

7. Is `systemctl daemon-reload` required after installing a new unit file? What happens if you skip it?

## Response snapshot

Delivered 7 decision-ready answers covering: system vs user service selection, restart limit configuration, environment variable inheritance, WantedBy target selection, uv WorkingDirectory behavior, After/Requires/Wants semantics, and daemon-reload necessity.

## Outcome

- Impact: Research phase complete for 002-systemd-daemon-setup; all 7 planning questions answered with actionable, concrete recommendations
- Tests: No tests — research/general stage
- Files: 1 new PHR file
- Next prompts: /sp.plan, /sp.tasks, /sp.implement
- Reflection: The system service + User= approach is the decisive recommendation for WSL2 auto-start; user services require lingering which is an extra manual step. The PATH pitfall (system PATH vs shell PATH) was already identified in FR-007 of the spec — this research confirms the mitigation approach (detect uv path at install time via `which uv` and embed the absolute path in ExecStart).

## Evaluation notes (flywheel)

- Failure modes observed: none — research stage
- Graders run and results (PASS/FAIL): n/a
- Prompt variant (if applicable): null
- Next experiment: null
