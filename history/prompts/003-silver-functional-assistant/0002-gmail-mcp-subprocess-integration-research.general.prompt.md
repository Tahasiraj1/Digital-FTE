---
id: "0002"
title: Gmail MCP Subprocess Integration Research
stage: general
date: 2026-02-27
surface: agent
model: claude-sonnet-4-6
feature: 003-silver-functional-assistant
branch: 002-systemd-daemon-setup
user: taha
command: research
labels: ["mcp","gmail","claude-code","subprocess","systemd","research"]
links:
  spec: specs/003-silver-functional-assistant/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/fte/orchestrator.py
  - deploy/install.sh
  - specs/002-systemd-daemon-setup/research.md
  - specs/003-silver-functional-assistant/spec.md
tests:
  - null
---

## Prompt

Research how to integrate a local Gmail MCP server with the Claude Code orchestrator for the FTE (Full-Time Employee) project.

Context:
- The orchestrator runs Claude Code as a subprocess: `claude --add-dir <vault> --allowedTools "..." --print "<prompt>"`
- We want to add a local Gmail MCP server (`@gongrzhe/server-gmail-autoauth-mcp`) so Claude can call Gmail MCP tools during task processing
- The project uses Python 3.13+ with uv, running as a systemd service
- Claude Code version: latest (2025)

Answer these specific questions:

1. **MCP configuration location**: Where does Claude Code look for MCP server config when invoked as a subprocess via `claude --print`? Is it:
   - `~/.claude/settings.json` (user-level)
   - `.claude/settings.json` (project-level, in the FTE project root)
   - `--mcp-config` flag on the CLI
   - Something else?

2. **MCP config format**: What is the exact JSON format for adding an npm MCP server (e.g., `npx @gongrzhe/server-gmail-autoauth-mcp`) to Claude Code's configuration? Provide the exact schema with all required fields.

3. **Environment variable injection**: The Gmail MCP needs `GMAIL_CREDENTIALS_PATH` and `GMAIL_TOKEN_PATH`. How do you pass environment variables to an MCP server defined in Claude Code config? Show the exact config snippet.

4. **--allowedTools flag**: When the orchestrator adds `--allowedTools`, does it need to explicitly list MCP tool names (e.g., `mcp__gmail__gmail_send_message`) or just allow MCP in general? What's the naming convention for MCP tool names in Claude Code?

5. **Subprocess MCP loading**: Does Claude Code load MCP servers defined in settings when run via `claude --print` (non-interactive mode)? Or does MCP only work in interactive mode?

6. **Best practice**: For a production daemon where the orchestrator subprocess needs Gmail MCP access, what is the recommended architecture? Should MCP config be at user-level or project-level?

## Response snapshot

Six concrete answers provided covering all questions:

1. **Config location**: Three-tier lookup: `--mcp-config` flag > `.claude/settings.json` (project) > `~/.claude/settings.json` (user). For systemd daemon, user-level (`~/.claude/settings.json`) is recommended since unit files already set `Environment=HOME=/home/taha`.

2. **Config format**: `mcpServers` object in settings.json with `type: "stdio"`, `command` (absolute path to npx), `args` array, `env` object. Server name key becomes the MCP namespace.

3. **Env var injection**: Use the `"env"` key inside the server definition in `mcpServers`. Variables are injected only into the MCP server subprocess. Use absolute paths for credential files, chmod 600. Do NOT put credentials in systemd `Environment=` directives (world-readable via `systemctl show`).

4. **--allowedTools naming**: Convention is `mcp__<server-name>__<tool-name>` (double underscore). Must list tools explicitly — no wildcard. Current orchestrator uses `--dangerously-skip-permissions` which bypasses this, consistent with HITL vault-based safety model.

5. **Subprocess MCP loading**: YES — Claude Code loads MCP servers in non-interactive `-p` mode. MCP initialization is part of core startup, not the interactive REPL. Critical caveat: OAuth first-time consent must be completed interactively before daemon use; subsequent runs use the cached refresh token.

6. **Best practice**: User-level `~/.claude/settings.json` for MCP config. Credential files at `~/.config/fte/` (chmod 600, never in git). Pre-install npm package globally. Complete OAuth interactively once before deploying daemon.

## Outcome

- Impact: Research complete; provides concrete implementation guidance for Silver tier Gmail MCP integration
- Tests: null
- Files: No files modified (research only)
- Next prompts: /sp.plan for 003-silver-functional-assistant incorporating Gmail MCP architecture
- Reflection: The autoauth OAuth first-run problem is the critical blocker — must be solved interactively before systemd service can use Gmail MCP headlessly

## Evaluation notes (flywheel)

- Failure modes observed: WebSearch and WebFetch permissions denied; Bash permissions denied — all answers derived from codebase analysis + model knowledge
- Graders run and results (PASS/FAIL): null
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Verify npx absolute path and test `claude -p "list tools" --dangerously-skip-permissions` after writing ~/.claude/settings.json
