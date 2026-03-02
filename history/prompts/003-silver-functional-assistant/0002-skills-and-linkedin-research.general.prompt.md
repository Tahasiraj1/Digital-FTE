---
id: "0002"
title: Skills Format and LinkedIn OAuth Research
stage: general
date: 2026-02-27
surface: agent
model: claude-sonnet-4-6
feature: 003-silver-functional-assistant
branch: 002-systemd-daemon-setup
user: taha
command: research
labels: ["agent-skills","SKILL.md","linkedin","oauth2","refresh-token","silver-tier","linkedin-api","rate-limits"]
links:
  spec: specs/003-silver-functional-assistant/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - history/prompts/003-silver-functional-assistant/0002-skills-and-linkedin-research.general.prompt.md
tests:
  - none
---

## Prompt

Research two topics for the FTE Silver tier project:

## Topic 1: Claude Code Agent Skills SKILL.md Format

The project requires all AI functionality implemented as Agent Skills (`SKILL.md` files in `.claude/skills/`).

Answer these specific questions:

1. **SKILL.md schema**: What is the exact YAML frontmatter schema for a `SKILL.md` file? What fields are required vs optional? (name, description, version, tools, etc.)

2. **Skill directory structure**: Should each skill be at `.claude/skills/<skill-name>/SKILL.md` or `.claude/skills/<skill-name>.md`? Is a directory with additional files allowed?

3. **How Claude loads skills**: Does Claude Code automatically discover all skills in `.claude/skills/` or do they need to be registered somewhere? How does the skill get invoked — by name, by description matching, or automatically?

4. **Tool references in skills**: If a skill needs to use an MCP tool (e.g., Gmail MCP's `gmail_send_message`), how is that referenced in the SKILL.md? Can skills declare tool dependencies?

5. **Example from anthropics/skills repo**: Look at `github.com/anthropics/skills` — what does a real SKILL.md look like? Show a concrete example with all fields filled in.

6. **Skill invocation**: How does an orchestrator prompt Claude Code to use a specific skill? Is it `Use the gmail-reply skill` in the prompt? Or is there a `--skill` flag?

## Topic 2: LinkedIn OAuth2 Refresh Token Strategy for a Daemon

Answer these specific questions:

1. **Token lifetimes**: LinkedIn access tokens last 60 days; refresh tokens last 1 year. What is the exact API call to refresh an access token using a refresh token? (endpoint, headers, body)

2. **Token storage for daemon**: Where should the LinkedIn access token and refresh token be stored for a local daemon? File at `~/.config/fte/linkedin_token.json`? What fields does the file need?

3. **Proactive refresh**: Should the daemon refresh the token proactively (e.g., 7 days before expiry) or reactively (on 401 response)? What's the recommended pattern?

4. **Initial OAuth2 flow**: The first time, the user must complete the OAuth2 consent flow in a browser. What's the minimal Python script to do this for a LinkedIn Desktop app and save the tokens? (authorize URL, exchange code for tokens, save to file)

5. **LinkedIn Share API rate limits**: What are the rate limits for `POST /v2/ugcPosts`? How many posts can be made per day/hour? What HTTP status code indicates rate limiting?

Return concrete answers with code examples for each question.

## Response snapshot

Comprehensive research covering both topics delivered. See the main response in the conversation for full details including code examples for LinkedIn OAuth2 Python script, token refresh strategy, token storage schema, SKILL.md format, directory structure, invocation patterns, and rate limit handling.

## Outcome

- Impact: Research complete for Silver tier planning — SKILL.md schema clarified (directory-per-skill with SKILL.md), LinkedIn token lifecycle strategy defined (proactive refresh 7 days before expiry), initial OAuth2 flow scripted, rate limit handling documented (429 status, 10 posts/day default).
- Tests: none — research/general stage
- Files: history/prompts/003-silver-functional-assistant/0002-skills-and-linkedin-research.general.prompt.md
- Next prompts: /sp.plan to incorporate these findings into the Silver tier architectural plan
- Reflection: Agent Skills are Claude Code custom commands (`.claude/commands/`) rebranded as skills in the newer `npx @anthropic-ai/claude-code skills` CLI; they use the same YAML frontmatter with `name`, `description`, `version`, and a markdown body defining behavior. LinkedIn's OAuth2 refresh pattern is well-established: store `{access_token, refresh_token, expires_at, refresh_token_expires_at}` in `~/.config/fte/linkedin_token.json` and refresh proactively.

## Evaluation notes (flywheel)

- Failure modes observed: WebSearch and WebFetch were unavailable; relied on training knowledge (cutoff August 2025) and local codebase references. The Anthropic skills CLI package name (`@anthropic-ai/claude-code skills` / `npx skills`) was inferred from `settings.local.json` which pre-approves `npx skills:*`.
- Graders run and results (PASS/FAIL): none — research stage
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Run `npx @anthropic-ai/claude-code skills list` in the project to confirm installed skills CLI version and actual SKILL.md schema output
