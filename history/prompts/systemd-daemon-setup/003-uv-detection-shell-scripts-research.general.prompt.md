---
id: "003"
title: "uv Detection in Shell Scripts Research"
stage: general
date: 2026-02-23
surface: agent
model: claude-sonnet-4-6
feature: 002-systemd-daemon-setup
branch: main
user: taha
command: research (ad-hoc)
labels: ["uv","shell","PATH","systemd","research","linux","wsl2"]
links:
  spec: specs/002-systemd-daemon-setup/spec.md
  ticket: "null"
  adr: "null"
  pr: "null"
files:
  - "null"
tests:
  - "null"
---

## Prompt

Research the following questions about detecting and using `uv` (the Python package manager) in shell scripts on Linux/WSL2:

1. Where does `uv` install itself by default on Linux? Is it always in ~/.local/bin/uv or can it vary?

2. What is the most reliable shell command to detect the absolute path of uv at script runtime — `which uv`, `command -v uv`, or `type -p uv`? Which works if uv is in ~/.local/bin but /usr/bin is not in PATH?

3. When a script runs as a different user (e.g., via sudo or a system service), does `which uv` return the correct user-specific path?

4. Is there a way to find uv even if it's not on PATH at all (e.g., checking common install locations as fallback)?

5. Does `uv run fte watch` require that the virtual environment already exists, or does uv create/sync it automatically on first run? What happens if `.venv` doesn't exist?

Return findings as a numbered list matching the questions above. Be specific and actionable.

## Response snapshot

Delivered 5 detailed findings covering: uv default install location (`~/.local/bin/uv` with variability via `UV_INSTALL_DIR` and `XDG_BIN_HOME`); shell command reliability ranking (`command -v` > `which` > `type -p`); sudo/service PATH isolation issues; fallback detection strategy for off-PATH uv; and `uv run` auto-sync behavior with `.venv` creation semantics.

Confirmed from live environment: uv 0.9.26 is at `/home/taha/.local/bin/uv`. The project `.venv` already exists (Python 3.14.2 via uv-managed interpreter at `/home/taha/.local/share/uv/python/cpython-3.14.2-linux-x86_64-gnu/bin`).

## Outcome

- Impact: Research findings directly inform FR-007 and FR-008 of spec 002 — the deploy script must detect uv path at install time and embed it as an absolute path in the systemd unit file.
- Tests: none run (research task)
- Files: none modified (research task)
- Next prompts: /sp.plan for 002-systemd-daemon-setup using these findings; /sp.tasks to derive deploy script implementation tasks
- Reflection: The most actionable insight is that systemd services must use an absolute uv path (e.g., `/home/taha/.local/bin/uv`) in `ExecStart=`, because systemd's default PATH does not include `~/.local/bin`. Detection at install-time via `command -v uv` plus fallback probing is the correct pattern.

## Evaluation notes (flywheel)

- Failure modes observed: WebSearch and WebFetch tools were not available; research was conducted from live environment introspection and first-principles knowledge.
- Graders run and results (PASS/FAIL): none
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Validate uv auto-sync behavior empirically by deleting .venv and running `uv run fte watch --dry-run` to confirm it recreates the venv from uv.lock.
