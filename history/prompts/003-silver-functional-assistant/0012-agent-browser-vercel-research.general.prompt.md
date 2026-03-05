---
id: "0012"
title: Agent Browser Vercel Labs Research
stage: general
date: 2026-03-03
surface: agent
model: claude-sonnet-4-6
feature: 003-silver-functional-assistant
branch: 003-silver-functional-assistant
user: taha
command: research agent-browser by Vercel Labs
labels: ["research","browser-automation","facebook","instagram","social-media","mcp","vercel"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - null
tests:
  - null
---

## Prompt

Research "agent-browser" by Vercel Labs (https://agent-browser.dev or search GitHub for "vercel agent-browser").

We need to use this tool to automate Facebook and Instagram posting for a personal AI employee system.

Find out:
1. Installation method — npm package, binary, etc.
2. How it integrates with Claude Code — is there a `.claude-plugin` or MCP server config?
3. How persistent sessions work — where are cookies/auth stored? How do you save and restore a session?
4. The exact CLI commands for:
   - Starting a browser session / logging in
   - Saving a session to disk
   - Loading a saved session
   - Navigating to a URL and taking actions
5. Whether it supports headless mode (no visible browser window)
6. Any known issues with Facebook/Instagram automation specifically
7. Token efficiency claims — "93% fewer tokens than Playwright MCP" — verify this
8. Whether it can be invoked as a subprocess from Python (for our executor integration)
9. GitHub star count and maintenance status (last commit date, open issues)

Return findings in structured format with specific commands/config examples where found.

## Response snapshot

All external network and shell tools were denied (WebSearch, WebFetch, Bash/curl). Research could not be completed from training data alone — the tool was not in pre-August-2025 training data and was likely released after the knowledge cutoff.

Blocked on: WebSearch denied, WebFetch denied, Bash denied.

Recommended unblocking paths:
- Run `gh api repos/vercel/agent-browser` and paste output
- Enable WebFetch/WebSearch permissions in Claude Code settings
- Paste README contents directly into chat

## Outcome

- Impact: Research blocked — no findings retrievable without external network access
- Tests: none
- Files: PHR only
- Next prompts: Re-run after enabling WebFetch, or paste GitHub README manually
- Reflection: The tool likely postdates August 2025 training cutoff; all 9 questions remain open pending live data

## Evaluation notes (flywheel)

- Failure modes observed: All three network/shell tools denied; could not fabricate findings
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Enable WebFetch permission and re-run same prompt
