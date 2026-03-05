# Tasks: Gold Tier — Autonomous Employee

**Input**: Design documents from `/specs/004-gold-autonomous-employee/`
**Branch**: `004-gold-autonomous-employee`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Tests**: Unit tests generated for Ralph Loop and Odoo actions (core safety-critical logic). Integration test for end-to-end gold chain.

**Organization**: Tasks grouped by user story. Phase 2 (Ralph Loop Foundation) is a hard prerequisite — no user story can begin until it is complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared state)
- **[Story]**: User story label (US1–US5)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Deploy infrastructure required before any Gold implementation can begin.

- [x] T001 Create `deploy/docker-compose.odoo.yml` with Odoo 17 (+ PostgreSQL 15) per research.md §3 — ports 8069/8072, volumes pgdata/odoodata, restart-unless-stopped
- [x] T002 [P] Add Odoo MCP server config to project `.mcp.json` — `mcp-odoo-adv` via `npx -y mcp-odoo-adv` with env vars `ODOO_URL`, `ODOO_DB`, `ODOO_USERNAME`, `ODOO_PASSWORD` per contracts/mcp-config.md
- [x] T003 [P] Register Ralph Loop Stop hook in `.claude/settings.json` — add `hooks.Stop` entry pointing to `bash /mnt/d/projects/FTE/scripts/ralph-loop.sh`; preserve existing `permissions.allow` entries
- [x] T004 [P] Create `deploy/install-gold.sh` — script to: `npm install -g agent-browser`, `docker compose -f deploy/docker-compose.odoo.yml up -d db`, document manual Odoo DB init command and agent-browser session auth steps

**Checkpoint**: Infrastructure is deployable. Docker Compose file and MCP config exist. Stop hook registered.

---

## Phase 2: Foundational (Ralph Loop Core)

**Purpose**: Ralph Loop state management and continuation pattern — MUST be complete before any user story.

**⚠️ CRITICAL**: All Gold user stories depend on this phase.

- [x] T005 Create `src/fte/ralph_loop.py` — implement: `RalphLoopState` dataclass (fields: `loop_id`, `task_file`, `task_name`, `iteration`, `max_iterations`, `continuation_prompt`, `started_at`, `chain_step`, `chain_cap`); `read_state(vault)→RalphLoopState|None`; `write_state(vault, state)`(atomic rename); `clear_state(vault)`; `write_timeout_alert(vault, state)` (writes `SYSTEM_ralph-loop-timeout.md` to `Needs_Action/`)
- [x] T006 Create `scripts/ralph-loop.sh` — Stop hook bash script (~80 lines): (1) read `ralph_state.json` from `$VAULT_PATH`; if absent → exit 0 (guard); (2) parse `last_output` from stdin JSON; (3) if `<promise>AWAITING_APPROVAL</promise>` in last_output → exit 0; (4) if `<promise>TASK_COMPLETE</promise>` in last_output → clear_state + exit 0; (5) if `Done/<task_name>` exists → clear_state + exit 0; (6) if `iteration >= max_iterations` → write_timeout_alert + clear_state + exit 0; (7) else increment iteration + echo continuation_prompt + exit 1. Reads `VAULT_PATH` from env (default: `/mnt/d/AI_Employee_Vault`)
- [x] T007 Extend `src/fte/orchestrator.py` — (a) add `ralph_loop`, `ralph_continuation`, `ceo_briefing`, `invoice_request`, `social_post_chain`, `social_metrics_request` task types to `_route_files()`; (b) add `_invoke_claude_ralph(vault_path, files, loop_id)` that writes `ralph_state.json` before calling `claude -p` with `--mcp-config .mcp.json` flag (for Odoo MCP access) + existing `--dangerously-skip-permissions --add-dir`; log each Ralph invocation with `action_type="ralph_loop_iteration"` so T025 dashboard counts work; (c) add `_check_briefing_schedule(vault_path) -> bool` stub (returns False); (d) call `_check_briefing_schedule()` in the main polling loop after `_update_dashboard()`
- [x] T008 Extend `src/fte/executor.py` — (a) add to `DISPATCH_TABLE`: `"create_odoo_invoice": "fte.actions.odoo"`, `"confirm_odoo_invoice": "fte.actions.odoo"`, `"publish_facebook_post": "fte.actions.facebook"`, `"publish_instagram_post": "fte.actions.instagram"`; (b) add `_drop_continuation_task(vault, approved_path, step_completed)` helper: reads `ralph_loop_id` from frontmatter; if present, writes `CONTINUATION_<task>_<ts>.md` to `Needs_Action/` with `ralph_loop: true`, `ralph_loop_id`, `step_completed`, `chain_step+1`; (c) call `_drop_continuation_task()` in `_dispatch()` AFTER `_move_to_done()` succeeds — sequence: handler → set_status(done) → move_to_done → **_drop_continuation_task** → log (this ordering ensures the approved file is fully moved before the continuation re-triggers the orchestrator)
- [x] T009 [P] Create `tests/unit/test_ralph_loop.py` — test cases: `test_read_state_missing_returns_none`, `test_write_read_roundtrip`, `test_clear_state_removes_file`, `test_timeout_alert_creates_file`, `test_write_state_atomic` (verify tmp file not left on disk)

**Checkpoint**: Ralph Loop state machine fully implemented. Stop hook exits correctly under all conditions. Executor drops continuation tasks. Unit tests pass.

---

## Phase 3: User Story 1 — Autonomous Multi-Step Task Completion (Priority: P1) 🎯 MVP

**Goal**: Multi-step tasks execute to completion without manual re-triggering. Loop terminates cleanly via promise or file-movement.

**Independent Test**: Drop `TEST_autonomous_task_<date>.md` (type: `ralph_loop: true`, 2-step plan: write plan file → move to Done) into `Needs_Action/`. Start orchestrator. Verify: Claude writes a plan file to `Plans/`, loop continues, task moves to `Done/`, loop exits without manual kill. No approval required for this test (fully autonomous chain).

- [x] T010 [US1] Create `.claude/skills/ralph-loop/SKILL.md` — skill instructions for Claude when processing any `ralph_loop: true` task: (1) read task file and `Vault/Company_Handbook.md`; (2) execute the current step; (3) if step requires human approval → write approval file to `Pending_Approval/`, then output `<promise>AWAITING_APPROVAL</promise>` as the LAST line of the response; (4) if all steps complete → move task file from `In_Progress/` or `Needs_Action/` to `Done/`, then output `<promise>TASK_COMPLETE</promise>`; (5) if continuation task → read `step_completed` and `chain_context` from frontmatter, continue from next step; include example prompts for invoice chain, social post chain, CEO briefing
- [x] T011 [P] [US1] Create `tests/integration/test_ralph_loop_e2e.py` — test: create a mock 2-step autonomous task file in a temp vault, run orchestrator one cycle (mocked Claude invocation returning TASK_COMPLETE), verify task moves to Done/ and ralph_state.json is cleared; second test: mock Claude returning AWAITING_APPROVAL, verify state file iteration does NOT increment and continuation_task IS NOT dropped by executor (executor only drops after real dispatch)

**Checkpoint**: US1 complete. Ralph Loop works end-to-end for a simple autonomous chain.

---

## Phase 4: User Story 2 — Odoo Accounting Integration (Priority: P2)

**Goal**: Invoice requests processed via Odoo — draft created, confirmed, and emailed after approval.

**Independent Test**: Drop `INVOICE_REQUEST_<date>.md` (ralph_loop: true, type: invoice_request, client details + amount) into `Needs_Action/`. Verify: `ODOO_DRAFT_*.md` appears in `Pending_Approval/`. Move to `Approved/`. Verify: executor calls Odoo `account.move.create`, `CONTINUATION_*.md` drops into `Needs_Action/`, `ODOO_CONFIRM_*.md` appears in `Pending_Approval/`. Approve again. Verify: executor calls `action_post` + email send.

- [x] T012 [P] [US2] Create `src/fte/actions/odoo.py` — implement: `_get_odoo_client(vault)→(url,db,uid,password)` from env; `_jsonrpc(url, service, method, args)` with 15s timeout; `create_odoo_invoice_handler(approved_path, vault)` — calls `account.move.create` with line_items from frontmatter, writes `ODOO_CONFIRM_*.md` to `Pending_Approval/` with `odoo_invoice_id`; `confirm_odoo_invoice_handler(approved_path, vault)` — calls `action_post` then `account.move.action_invoice_sent`; on `ConnectionError` → write `SYSTEM_odoo-unreachable.md` to `Needs_Action/` and raise
- [x] T013 [P] [US2] Create `.claude/skills/odoo-invoice/SKILL.md` — skill for reading invoice_request task files and writing `ODOO_DRAFT_<client>_<ts>.md` to `Pending_Approval/`: extract client_name, client_email, line_items, currency, due_date from task; set `action_type: create_odoo_invoice`, `requires_human_review: true`, `ralph_loop_id` (from task frontmatter if present); character limits and field validation rules; example input/output pair
- [x] T014 [US2] Update `src/fte/orchestrator.py` `_invoke_claude_ralph()` — add `--add-dir Vault/Plans` flag so Claude can reference business context and past plans during invoice reasoning (note: `invoice_request` routing was already added to `_route_files()` in T007 — do NOT re-add it here)
- [x] T015 [P] [US2] Create `tests/unit/test_odoo_actions.py` — mock `_jsonrpc`: `test_create_invoice_writes_confirm_approval`, `test_confirm_invoice_calls_action_post`, `test_odoo_unreachable_writes_system_alert`, `test_create_invoice_requires_human_review_flag`

**Checkpoint**: US2 complete. Invoice create → approve → confirm → email works end-to-end (with real Odoo running).

---

## Phase 5: User Story 3 — Facebook & Instagram Publishing (Priority: P3)

**Goal**: Social posts published to Facebook and Instagram via browser automation. Sessions persist across restarts.

**Independent Test**: Drop `SOCIAL_POST_CHAIN_<date>.md` (ralph_loop: true, type: social_post_chain, post text provided) into `Needs_Action/`. Verify: `SOCIAL_facebook_*.md` and `SOCIAL_instagram_*.md` appear in `Pending_Approval/`. Approve each. Verify: executor invokes `agent-browser --session-name facebook/instagram`, posts appear on platforms within 60s.

- [x] T016 [P] [US3] Create `src/fte/actions/facebook.py` — implement `publish_facebook_post_handler(approved_path, vault)`: read `post_text`, `hashtags`, `session_name` from frontmatter; run `agent-browser --session-name facebook open https://facebook.com` then navigation steps (snapshot, click post box, type, submit) via `subprocess.run`; after successful post, run `agent-browser state save ~/.config/fte/facebook-session.json --session-name facebook` to back up session per FR-014; DEV_MODE: log command without executing; detect session expiry (login page in output) → write `SYSTEM_social-session-expired.md` alert, raise; detect platform restriction → write alert, raise; timeout: 60s
- [x] T017 [P] [US3] Create `src/fte/actions/instagram.py` — implement `publish_instagram_post_handler(approved_path, vault)`: same subprocess pattern as facebook.py; check `image_required: true` and `image_path: null` → raise `ValueError("image_required")` (executor will reject with reason); after successful post, run `agent-browser state save ~/.config/fte/instagram-session.json --session-name instagram` per FR-014; DEV_MODE and error handling matching facebook.py
- [x] T018 [P] [US3] Create `.claude/skills/social-post/SKILL.md` — skill for reading social_post_chain task and writing TWO approval files: one `SOCIAL_facebook_<ts>.md` and one `SOCIAL_instagram_<ts>.md` (unless platforms list specifies only one); write platform-specific content (FB: up to 63k chars, richer; IG: max 2200 chars, hashtag-heavy); set `ralph_loop_id` from task frontmatter; output `<promise>AWAITING_APPROVAL</promise>` after writing both files
- [x] T019 [US3] Extend `src/fte/executor.py` — add pre-dispatch guard for `publish_instagram_post`: before `_set_status(approved_path, "executing")`, check frontmatter `image_required: true` and `image_path: null`; if true, call `_move_to_rejected(approved_path, vault, "image_required")` and log with `result="image_required"` without invoking handler
- [x] T028 [P] [US3] Create `.claude/skills/social-metrics/SKILL.md` — skill for collecting social engagement summary (FR-015): use `agent-browser --session-name facebook` to navigate to each published post's insights page and collect likes, comments, reach for the past 7 days; repeat for Instagram; write a `SOCIAL_METRICS_<YYYY-MM-DD>.md` report to `Vault/Plans/` with per-platform totals; no approval required (read-only browser action); add `collect_social_metrics` to `orchestrator.py` route for `type: social_metrics_request` task files

**Checkpoint**: US3 complete. Facebook and Instagram posts publish from approval → agent-browser within 60s (sessions authenticated). Social engagement metrics collectible on demand.

---

## Phase 6: User Story 4 — Monday Morning CEO Briefing (Priority: P4)

**Goal**: Weekly business audit report generated autonomously. No manual trigger after initial setup.

**Independent Test**: Drop `CEO_BRIEFING_<date>.md` (ralph_loop: true, type: ceo_briefing) into `Needs_Action/`. Verify: `CEO_Briefing_<date>.md` appears in `Plans/` within 3 minutes with all sections (emails, WhatsApp, Odoo, social, pending items). Task moves to `Done/`.

- [x] T020 [P] [US4] Extend `src/fte/vault.py` `init_vault()` — add `briefing_state.json` initialization: create `Vault/briefing_state.json` with `{"last_run": null, "schedule_utc_weekday": 6, "schedule_utc_hour": 18, "schedule_utc_minute": 0}` if absent
- [x] T021 [US4] Implement `_check_briefing_schedule(vault_path)` in `src/fte/orchestrator.py` — full implementation: read `Vault/briefing_state.json`; if `last_run` is null treat as epoch; compute next scheduled datetime (next weekday+hour+minute in UTC after last_run); if `datetime.now(UTC) >= next_scheduled`: check deduplication (no `CEO_BRIEFING_*.md` already in `Needs_Action/` or `In_Progress/`); write `CEO_BRIEFING_<YYYY-MM-DD>.md` to `Needs_Action/` with `type: ceo_briefing, ralph_loop: true`; update `last_run` in `briefing_state.json`; log `action_type: briefing_schedule_trigger`
- [x] T022 [P] [US4] Create `.claude/skills/ceo-briefing/SKILL.md` — skill for generating CEO Briefing: read `Vault/Logs/*.json` for past 7 days; aggregate by action_type; query Odoo MCP for `outstanding_invoices` and `monthly_revenue`; scan `Vault/Pending_Approval/` for overdue items; write `CEO_Briefing_<YYYY-MM-DD>.md` to `Vault/Plans/` with sections: Action Required, Emails Handled, WhatsApp Replies, Odoo Activity, Social Posts, Pending Tasks; include totals and counts; output `<promise>TASK_COMPLETE</promise>`; move task to `Done/`

**Checkpoint**: US4 complete. Briefing generates on schedule and on manual trigger. All domain sections present.

---

## Phase 7: User Story 5 — Cross-Domain Integration (Priority: P5)

**Goal**: Multi-domain chains (invoice → email → social) execute with per-action approvals and a 3-action cap.

**Independent Test**: Drop `CROSS_DOMAIN_invoice_paid_<date>.md` (ralph_loop: true, type: invoice_paid_trigger) into `Needs_Action/`. Verify: thank-you email approval in `Pending_Approval/` → approve → sent → CONTINUATION drops → LinkedIn win post approval → approve → posted. Chain terminates after 3 downstream actions.

- [x] T023 [US5] Extend `src/fte/executor.py` `_drop_continuation_task()` — add chain cap enforcement: read `chain_step` from approval frontmatter (or ralph_state.json); if `chain_step >= int(os.environ.get("RALPH_CHAIN_CAP", 3))` → log `action_type: ralph_chain_cap_reached`, do NOT write continuation task; chain_context dict propagated from approved file to continuation task frontmatter (pass `odoo_invoice_id`, `client_email`, etc.)
- [x] T024 [P] [US5] Create `tests/integration/test_gold_chain.py` — mock end-to-end invoice chain: (1) create invoice_request task; (2) mock orchestrator Claude → writes ODOO_DRAFT_* + AWAITING_APPROVAL; (3) mock executor approves → calls create_odoo_invoice_handler mock → drops CONTINUATION; (4) mock Claude → writes ODOO_CONFIRM_* + AWAITING_APPROVAL; (5) mock executor approves → calls confirm_odoo_invoice_handler mock → drops CONTINUATION (chain_step=2); (6) mock Claude → writes EMAIL_REPLY_* + AWAITING_APPROVAL; (7) mock executor approves → sends email → chain_step=3 = cap → no more continuation. Verify: 3 approval files created, chain terminated at cap.

**Checkpoint**: US5 complete. Cross-domain chains run with per-action approvals and terminate cleanly at cap.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Audit logging, dashboard Gold metrics, handbook update, smoke test.

- [x] T025 [P] Extend `src/fte/orchestrator.py` `_update_dashboard()` — add Gold tier metric section: read today's log for `create_odoo_invoice`, `confirm_odoo_invoice`, `publish_facebook_post`, `publish_instagram_post`, `ralph_loop_iteration`, `ceo_briefing_generated` counts; append below existing Silver metrics
- [x] T026 [P] Extend `src/fte/vault.py` `COMPANY_HANDBOOK_CONTENT` — add Gold tier rules section: Odoo financial actions always require human review; FB/IG max 2 posts/day; cross-domain chain cap = 3; Ralph Loop max 10 iterations
- [ ] T027 Run `specs/004-gold-autonomous-employee/quickstart.md` end-to-end — install agent-browser, start Odoo, authenticate sessions, trigger manual invoice request, verify full chain. Document any deviations from quickstart as issues.

**Checkpoint**: All Gold tier features complete, logged, and documented.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ──────────────────────────────────────────┐
                                                           ↓
Phase 2 (Foundational — Ralph Loop) ─────── BLOCKS ALL USER STORIES
                                                           ↓
Phase 3 (US1 — Ralph Loop E2E)     ───────────────────────┐
Phase 4 (US2 — Odoo)               ─────── can run in parallel ─→ Phase 7 (US5)
Phase 5 (US3 — Social)             ─────── can run in parallel ─→ Phase 7 (US5)
Phase 6 (US4 — CEO Briefing)       ─────── can run after Phase 2 ─┘
                                                           ↓
Phase 8 (Polish) ────────────────────────── After all US complete
```

### User Story Dependencies

| Story | Depends On | Can Parallelize With |
|-------|-----------|---------------------|
| US1 (Ralph Loop E2E) | Phase 2 | US2, US3, US4 |
| US2 (Odoo) | Phase 2 | US1, US3, US4 |
| US3 (Social) | Phase 2 | US1, US2, US4 |
| US4 (CEO Briefing) | Phase 2 | US1, US2, US3 |
| US5 (Cross-Domain) | US1 + US2 + US3 | — |

### Within Phase 2 (Sequential)

```
T005 (ralph_loop.py) ──→ T006 (ralph-loop.sh) ──→ T007 (orchestrator.py) ──→ T008 (executor.py)
T009 (tests) [P] — can start after T005
```

### Phase 2 Internal Note

T007 and T008 both modify existing files in the same package — do these sequentially. T005 and T006 are new files — can be written simultaneously.

---

## Parallel Opportunities

### Phase 2

```bash
# These two can run in parallel (new files):
Task T005: Create src/fte/ralph_loop.py
Task T006: Create scripts/ralph-loop.sh
Task T009: Create tests/unit/test_ralph_loop.py
# Then sequentially:
Task T007: Extend orchestrator.py (reads ralph_loop.py)
Task T008: Extend executor.py (reads ralph_loop.py)
```

### Phases 4–6 (after Phase 3 complete)

```bash
# All three user stories can run in parallel:
Task T012+T013+T014+T015: US2 (Odoo)
Task T016+T017+T018+T019: US3 (Social)
Task T020+T021+T022: US4 (CEO Briefing)
```

---

## Implementation Strategy

### MVP First (US1 Only — Phases 1–3)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T009) — CRITICAL
3. Complete Phase 3: US1 (T010–T011)
4. **STOP and VALIDATE**: A simple 2-step autonomous task runs end-to-end without manual re-triggering
5. Ralph Loop infrastructure proven before investing in Odoo/Social

### Incremental Delivery

1. Setup + Foundational → Ralph Loop proven
2. Add US1 (Ralph Loop skill) → autonomous chains work
3. Add US2 (Odoo) → invoice chains work
4. Add US3 (Social) → social chains work
5. Add US4 (CEO Briefing) → weekly briefing works
6. Add US5 (Cross-Domain) → full integration proven
7. Polish → production-grade

### Critical Risk: Stop Hook Guard

**T006 must include the guard on first line**: if `ralph_state.json` does not exist, `exit 0` immediately. Without this guard, every normal orchestrator invocation (non-Ralph) will have the Stop hook fire and potentially misbehave. Test this guard explicitly in T009.

---

## Notes

- [P] tasks = different files, safe to run concurrently
- T007 and T008 both modify `src/fte/orchestrator.py` and `src/fte/executor.py` respectively — do NOT parallelize these with other tasks touching the same file
- Ralph Loop tasks (T005–T008) must be completed and passing before any Gold user story begins
- Odoo 19 Docker image: use `odoo:17` in T001 (note in compose file to upgrade when `odoo:19` tag appears on Docker Hub)
- agent-browser selector brittleness: FB/IG navigation steps in T016/T017 must be documented in the action handler comments for easy selector updates when platform UI changes
- All real external actions gated behind `DEV_MODE` check — test everything in DEV_MODE first (per Constitution §V)
