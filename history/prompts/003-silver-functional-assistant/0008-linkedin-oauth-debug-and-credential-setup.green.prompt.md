---
id: "0008"
title: LinkedIn OAuth Debug and Credential Setup
stage: green
date: 2026-03-01
surface: agent
model: claude-sonnet-4-6
feature: 003-silver-functional-assistant
branch: 003-silver-functional-assistant
user: taha
command: "uv run --env-file .env fte linkedin-auth"
labels: ["linkedin", "oauth", "debugging", "credentials", "google-oauth"]
links:
  spec: "specs/003-silver-functional-assistant/spec.md"
  ticket: "null"
  adr: "null"
  pr: "null"
files:
  - src/fte/linkedin_auth.py
tests:
  - "Gmail API: list_emails returned 5 real unread emails"
  - "Calendar API: list_events returned 0 events (empty calendar)"
  - "LinkedIn token saved at ~/.config/fte/linkedin_token.json (chmod 600)"
  - "LinkedIn scopes: email,openid,profile,w_member_social"
---

## Prompt

"done" (user confirmed LinkedIn Products were added in developer portal, and auth succeeded)

Previous session context: LinkedIn OAuth was timing out — browser showed "Authorization complete" but token was never saved. Root cause investigation needed.

## Response

Diagnosed and fixed three LinkedIn OAuth issues in sequence:

1. **Silent exception swallowing**: `run_auth_flow()` had no try/except around `httpx.post()` — HTTP errors from LinkedIn were raised but not printed. Added debug prints (`resp.status_code`, `resp.text`) and a proper `try/except httpx.HTTPStatusError` block with `sys.exit(1)`.

2. **Callback handler masking errors**: `_CallbackHandler.do_GET()` always responded with "Authorization complete!" regardless of whether LinkedIn sent `?code=...` (success) or `?error=...` (failure). The polling loop checked `_CallbackHandler.code is None` — if LinkedIn sent an error, `code` stayed None and the loop ran until timeout. Fixed by:
   - Adding `_CallbackHandler.error` class variable
   - Parsing `error` and `error_description` from callback params
   - Polling loop now breaks on `_CallbackHandler.error is not None`
   - Clear error message explaining which LinkedIn Products to add

3. **`unauthorized_scope_error`**: Root cause confirmed — LinkedIn app was missing required Products. Scopes `openid`, `profile`, `email` require "Sign In with LinkedIn using OpenID Connect" product; `w_member_social` requires "Share on LinkedIn" product. User added both products in LinkedIn Developer Portal. Auth succeeded on next run.

**Final token state:**
- `access_token`: present (truncated)
- `scope`: `email,openid,profile,w_member_social`
- `expires_at`: 2026-04-30
- `linkedin_user_id`: `OhuO7nCdA5`
- File permissions: `chmod 600` ✓

**All credential setup complete:**
| Integration | Status | Token |
|---|---|---|
| Gmail | ✅ | `~/.config/fte/gmail_token.json` |
| Calendar | ✅ | `~/.config/fte/gmail_token.json` (shared) |
| LinkedIn | ✅ | `~/.config/fte/linkedin_token.json` |
| WhatsApp | ⏸ Skipped | (official API later) |

## Outcome

- PASS: All three OAuth integrations functional
- PASS: LinkedIn token saved with correct scopes and expiry
- NEXT: T067 DEV_MODE smoke test, T068 constitution compliance review
