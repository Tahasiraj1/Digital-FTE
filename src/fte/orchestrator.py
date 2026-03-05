"""Orchestrator — polls Needs_Action/ and invokes Claude Code for reasoning.

Silver extension: routes email, whatsapp_message, linkedin, and scheduling-intent
task files to their respective skills, which produce ApprovalRequest files in
Pending_Approval/. Unrecognized types fall back to the Bronze plan-writing path.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import frontmatter

from fte.logger import log_action

CLAUDE_TIMEOUT_S = 300
EMAIL_BATCH_SIZE = 5  # max emails per Claude invocation

# ---------------------------------------------------------------------------
# Skill prompts — Silver tier routing (T032, T042, T045, T052)
# ---------------------------------------------------------------------------

_GMAIL_REPLY_PROMPT = """\
You are the FTE gmail-reply skill. Read the email task file(s) below and decide \
whether each needs a human reply.

SKIP the email entirely (write nothing) if ANY of these are true:
- Sender address contains: noreply, no-reply, donotreply, mailer-daemon, postmaster, \
security-noreply, notifications, automated, alert, eservice, bounce
- Email is a one-time password (OTP), verification code, or security notification
- Email is a marketing newsletter or promotional blast
- Email is an automated system notification with no human sender

For emails that DO need a reply, write EXACTLY ONE file to Pending_Approval/ per email.

Filename pattern: EMAIL_REPLY_<message_id>_<YYYYMMDD-HHMMSS>.md

File format:
---
action_type: send_email
source_task: "<filename of the task file>"
message_id: "<message_id from source task>"
to: "<sender email>"
to_name: "<sender display name>"
subject: "Re: <original subject>"
thread_id: "<thread_id from source task>"
proposed_reply: |
  <your drafted reply here>
created_at: "<ISO8601 timestamp>"
expiry_at: "<ISO8601 timestamp, 24h from now>"
status: pending
flags: []
---

# Email Reply — Awaiting Approval

**To**: <name> (`<email>`)
**Subject**: Re: <subject>

## Proposed Reply

<your drafted reply>

---
**To Approve**: Move this file to Approved/
**To Reject**: Move this file to Rejected/
**Expires**: <expiry_at>

Task files to process:
{file_list}
"""

_WHATSAPP_REPLY_PROMPT = """\
You are the FTE whatsapp-reply skill. Read the WhatsApp task file provided and \
draft a short, conversational reply appropriate for WhatsApp.

Rules:
- Reply must be under 500 characters for WhatsApp norms.
- All replies require manual approval — write to Pending_Approval/ only.
- Tone: friendly but professional, conversational.

Output: Write EXACTLY ONE file to Vault/Pending_Approval/ using this filename pattern:
  WHATSAPP_REPLY_<sanitized_id>_<YYYYMMDD-HHMMSS>.md

File frontmatter schema:
---
action_type: send_whatsapp
source_task: "<path of the Needs_Action/ file>"
to_jid: "<from_jid from source task>"
to_display: "<from_display from source task>"
proposed_reply: "<your drafted reply, max 500 chars>"
created_at: "<ISO8601 timestamp>"
expiry_at: "<ISO8601 timestamp, 24h from now>"
status: pending
---

Task files to process:
{file_list}
"""

_CALENDAR_PROMPT = """\
You are the FTE calendar-event skill. Extract the scheduling intent from the \
task file and draft a calendar event creation request.

Extract: event_title, event_date (ISO 8601 YYYY-MM-DD), event_time_start (HH:MM),
event_time_end (HH:MM), event_timezone (default: Asia/Karachi), attendees (list of emails),
event_description.

Rules:
- All event creation requires manual approval — write to Pending_Approval/ only.
- If no specific time given, suggest a sensible default (e.g., 10:00–11:00).
- Default duration: 1 hour unless specified.

Output: Write EXACTLY ONE file to Vault/Pending_Approval/ using this filename pattern:
  CALENDAR_<slug>_<YYYYMMDD-HHMMSS>.md

File frontmatter schema:
---
action_type: create_calendar_event
source_task: "<path of the Needs_Action/ file>"
event_title: "<title>"
event_date: "<YYYY-MM-DD>"
event_time_start: "<HH:MM>"
event_time_end: "<HH:MM>"
event_timezone: "Asia/Karachi"
attendees:
  - "<email1>"
event_description: "<description>"
created_at: "<ISO8601 timestamp>"
expiry_at: "<ISO8601 timestamp, 24h from now>"
status: pending
---

Task files to process:
{file_list}
"""

_LINKEDIN_PROMPT = """\
You are the FTE linkedin-post skill. Draft a professional LinkedIn post for \
business visibility and sales generation.

Rules:
- Post must be under 3,000 characters.
- Include 3–5 relevant hashtags.
- End with a call-to-action.
- No pricing or financial commitments — if present, add "requires_human_review" flag.
- All posts require manual approval — write to Pending_Approval/ only.

Output: Write EXACTLY ONE file to Vault/Pending_Approval/ using this filename pattern:
  LINKEDIN_<slug>_<YYYYMMDD-HHMMSS>.md

File frontmatter schema:
---
action_type: publish_linkedin_post
source_task: "<path of the Needs_Action/ file>"
proposed_post: |
  <your post, max 3000 chars>
character_count: <integer>
max_character_count: 3000
created_at: "<ISO8601 timestamp>"
expiry_at: "<ISO8601 timestamp, 24h from now>"
status: pending
flags: []
---

Task files to process:
{file_list}
"""

PROMPT_TEMPLATE = """\
You are the AI Employee reasoning engine. Your job is to read task files, \
think about what action is needed, and write plan files.

Instructions:
1. Read each file listed below from the Needs_Action/ folder.
2. Reference Company_Handbook.md for rules and business context.
3. For EACH file, create a plan file in Plans/ with this exact format:

   Filename: PLAN-<task-slug>.md  (derive slug from the task filename, \
removing the timestamp prefix and extension)

   Content:
   ---
   source_task: <original filename in Needs_Action/>
   created: <current ISO 8601 timestamp>
   status: proposed
   ---

   ## Summary
   [One-line summary of your recommendation]

   ## Reasoning
   [Your analysis of the task file content]

   ## Recommended Action
   [What should be done — this is advisory only at Bronze tier]

   ## Confidence
   [high / medium / low]

4. Process ALL files listed below. Create one plan per file.

Files to process:
{file_list}
"""


# ---------------------------------------------------------------------------
# Scheduling intent detection — T046
# ---------------------------------------------------------------------------

_SCHEDULING_KEYWORDS = re.compile(
    r"\b(meet|call|schedule|appointment|meeting|session|tuesday|monday|wednesday|"
    r"thursday|friday|saturday|sunday|am|pm|tomorrow|today|next week|"
    r"\d{1,2}:\d{2}|\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.IGNORECASE)


def _has_scheduling_intent(task_file: Path) -> bool:
    """Heuristic check: does this task file describe a scheduling request?"""
    try:
        content = task_file.read_text(encoding="utf-8", errors="replace")
        keyword_matches = len(_SCHEDULING_KEYWORDS.findall(content))
        email_matches = len(_EMAIL_PATTERN.findall(content))
        return keyword_matches >= 2 and email_matches >= 1
    except Exception:
        return False


def _get_task_type(task_file: Path) -> str:
    """Return the task type from frontmatter, or 'unknown'."""
    try:
        post = frontmatter.load(str(task_file))
        return str(post.get("type", "unknown"))
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Silver skill routing — route files to appropriate skill prompts
# ---------------------------------------------------------------------------

def _is_ralph_loop_task(task_file: Path) -> bool:
    """Check if a task file has ralph_loop: true in frontmatter."""
    try:
        post = frontmatter.load(str(task_file))
        return bool(post.get("ralph_loop", False))
    except Exception:
        return False


def _route_files(vault_path: Path, files: list[Path]) -> dict[str, list[Path]]:
    """Split files into routing groups based on their type/content.

    Returns:
        {
          "ralph_loop": [...],
          "email": [...],
          "whatsapp": [...],
          "calendar": [...],
          "linkedin": [...],
          "bronze": [...],   # fallback: Bronze plan-writing
        }
    """
    routes: dict[str, list[Path]] = {
        "ralph_loop": [],
        "email": [],
        "whatsapp": [],
        "calendar": [],
        "linkedin": [],
        "bronze": [],
    }

    for f in files:
        task_type = _get_task_type(f)
        # Gold: Ralph Loop tasks take priority
        if _is_ralph_loop_task(f):
            routes["ralph_loop"].append(f)
        elif task_type == "email":
            routes["email"].append(f)
        elif task_type == "whatsapp_message":
            routes["whatsapp"].append(f)
        elif task_type in ("linkedin", "linkedin_post"):
            routes["linkedin"].append(f)
        elif _has_scheduling_intent(f):
            routes["calendar"].append(f)
        else:
            routes["bronze"].append(f)

    return routes


def _list_needs_action(vault_path: Path) -> list[Path]:
    """Return sorted list of files in Needs_Action/."""
    needs_action = vault_path / "Needs_Action"
    if not needs_action.exists():
        return []
    return sorted(f for f in needs_action.iterdir() if f.is_file())


def _invoke_claude_with_prompt(
    vault_path: Path,
    prompt: str,
    files: list[Path],
    action_type: str,
) -> bool:
    """Invoke Claude Code with a given prompt. Returns True on success."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    start = time.monotonic()
    try:
        result = subprocess.run(
            [
                "claude",
                "-p", prompt,
                "--add-dir", str(vault_path / "Needs_Action"),
                "--dangerously-skip-permissions",
            ],
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT_S,
            env=env,
            cwd=str(vault_path),
        )
        duration = int((time.monotonic() - start) * 1000)

        if result.returncode != 0:
            log_action(
                vault_path,
                action_type="error",
                actor="orchestrator",
                parameters={"skill": action_type, "stderr": result.stderr[:500]},
                result="error",
                error_message=f"Claude exited with code {result.returncode}",
                duration_ms=duration,
            )
            print(f"Claude error ({action_type}, exit {result.returncode}): {result.stderr[:200]}", file=sys.stderr)
            return False

        log_action(
            vault_path,
            action_type=action_type,
            actor="claude",
            parameters={"file_count": len(files)},
            result="success",
            duration_ms=duration,
        )
        return True

    except FileNotFoundError:
        log_action(
            vault_path,
            action_type="error",
            actor="orchestrator",
            result="error",
            error_message="Claude Code CLI not found. Install with: npm install -g @anthropic/claude-code",
        )
        print("Error: Claude Code CLI not found. Install with: npm install -g @anthropic/claude-code", file=sys.stderr)
        return False

    except subprocess.TimeoutExpired:
        log_action(
            vault_path,
            action_type="error",
            actor="orchestrator",
            result="error",
            error_message=f"Claude timed out after {CLAUDE_TIMEOUT_S}s",
        )
        print(f"Error: Claude timed out after {CLAUDE_TIMEOUT_S}s", file=sys.stderr)
        return False




def _invoke_claude_ralph(
    vault_path: Path,
    files: list[Path],
    loop_id: str | None = None,
) -> bool:
    """Invoke Claude Code in Ralph Loop mode for multi-step autonomous tasks.

    Writes ralph_state.json before invocation. The Stop hook
    (scripts/ralph-loop.sh) handles continuation logic.
    """
    from fte.ralph_loop import create_state_for_task, write_state

    # Process one Ralph task at a time (single active loop)
    task_file = files[0]
    state = create_state_for_task(vault_path, task_file)
    if loop_id:
        state.loop_id = loop_id
    write_state(vault_path, state)

    # Build the prompt for the Ralph Loop skill
    task_type = _get_task_type(task_file)
    prompt = (
        f"You are the FTE autonomous employee running in Ralph Loop mode. "
        f"Read the task file '{task_file.name}' in Needs_Action/ and execute it.\n\n"
        f"Task type: {task_type}\n"
        f"Loop ID: {state.loop_id}\n\n"
        f"IMPORTANT:\n"
        f"- If a step requires human approval, write an approval file to Pending_Approval/ "
        f"and output <promise>AWAITING_APPROVAL</promise> as the LAST line.\n"
        f"- If the task is fully complete, move the task file to Done/ "
        f"and output <promise>TASK_COMPLETE</promise> as the LAST line.\n"
        f"- Reference Company_Handbook.md for business rules.\n"
    )

    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    start = time.monotonic()
    try:
        cmd = [
            "claude",
            "-p", prompt,
            "--add-dir", str(vault_path / "Needs_Action"),
            "--add-dir", str(vault_path / "Plans"),
            "--mcp-config", str(Path(__file__).resolve().parents[2] / ".mcp.json"),
            "--dangerously-skip-permissions",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT_S,
            env=env,
            cwd=str(vault_path),
        )
        duration = int((time.monotonic() - start) * 1000)

        log_action(
            vault_path,
            action_type="ralph_loop_iteration",
            actor="claude",
            parameters={
                "loop_id": state.loop_id,
                "task_file": state.task_file,
                "iteration": state.iteration,
            },
            result="success" if result.returncode == 0 else "error",
            error_message=result.stderr[:500] if result.returncode != 0 else None,
            duration_ms=duration,
        )
        return result.returncode == 0

    except FileNotFoundError:
        log_action(
            vault_path,
            action_type="error",
            actor="orchestrator",
            result="error",
            error_message="Claude Code CLI not found.",
        )
        return False

    except subprocess.TimeoutExpired:
        log_action(
            vault_path,
            action_type="error",
            actor="orchestrator",
            result="error",
            error_message=f"Ralph Loop Claude timed out after {CLAUDE_TIMEOUT_S}s",
        )
        return False


def _check_briefing_schedule(vault_path: Path) -> bool:
    """Check if a CEO briefing is due. Returns True if a briefing task was created.

    Reads Vault/briefing_state.json, computes next scheduled time, and drops
    a CEO_BRIEFING_<date>.md into Needs_Action/ if due. Updates last_run.
    """
    state_file = vault_path / "briefing_state.json"
    if not state_file.exists():
        return False

    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False

    last_run_raw = state.get("last_run")
    weekday = state.get("schedule_utc_weekday", 6)  # 0=Mon, 6=Sun
    hour = state.get("schedule_utc_hour", 18)
    minute = state.get("schedule_utc_minute", 0)

    now = datetime.now(timezone.utc)

    # Parse last_run (or treat as epoch if null)
    if last_run_raw:
        try:
            last_run = datetime.fromisoformat(str(last_run_raw).replace("Z", "+00:00"))
        except ValueError:
            last_run = datetime(2000, 1, 1, tzinfo=timezone.utc)
    else:
        last_run = datetime(2000, 1, 1, tzinfo=timezone.utc)

    # Compute next scheduled time after last_run
    # Find the next occurrence of weekday+hour+minute after last_run
    candidate = last_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
    # Advance to the correct weekday
    days_ahead = weekday - candidate.weekday()
    if days_ahead < 0:
        days_ahead += 7
    candidate += timedelta(days=days_ahead)
    # If candidate is still <= last_run, advance by a week
    if candidate <= last_run:
        candidate += timedelta(weeks=1)

    if now < candidate:
        return False

    # Deduplication: check if CEO_BRIEFING_<today>.md already exists
    today_str = now.strftime("%Y-%m-%d")
    needs_action = vault_path / "Needs_Action"
    in_progress = vault_path / "In_Progress"
    for d in (needs_action, in_progress):
        if d.exists():
            for f in d.iterdir():
                if f.name.startswith("CEO_BRIEFING_") and today_str in f.name:
                    return False

    # Drop briefing task
    task_name = f"CEO_BRIEFING_{today_str}.md"
    task_path = needs_action / task_name
    task_path.write_text(
        f"---\ntype: ceo_briefing\nralph_loop: true\ncreated_at: \"{now.isoformat()}\"\n---\n\n"
        f"# CEO Briefing Request\n\n"
        f"Generate the weekly CEO briefing report for the week ending {today_str}.\n"
        f"Aggregate data from Vault/Logs/ for the past 7 days across all domains.\n"
        f"Write report to Vault/Plans/CEO_Briefing_{today_str}.md.\n"
        f"When complete, move this task to Done/ and output <promise>TASK_COMPLETE</promise>.\n",
        encoding="utf-8",
    )

    # Update last_run
    state["last_run"] = now.isoformat()
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    log_action(
        vault_path,
        action_type="briefing_schedule_trigger",
        actor="orchestrator",
        parameters={"task_file": task_name},
        result="success",
    )
    print(f"[orchestrator] CEO Briefing triggered: {task_name}")
    return True


def invoke_claude(vault_path: Path, files: list[Path]) -> bool:
    """Invoke Claude Code to reason over files, routing each to the right skill.

    Returns True if all routes succeeded (or had no files).
    """
    routes = _route_files(vault_path, files)
    all_ok = True

    # Gold: Ralph Loop tasks (T007)
    if routes["ralph_loop"]:
        for ralph_file in routes["ralph_loop"]:
            ok = _invoke_claude_ralph(vault_path, [ralph_file])
            all_ok = all_ok and ok

    # Email → gmail-reply skill (T032)
    if routes["email"]:
        batch = routes["email"][:EMAIL_BATCH_SIZE]
        file_list = "\n".join(f"- {f.name}" for f in batch)
        prompt = _GMAIL_REPLY_PROMPT.format(file_list=file_list)
        ok = _invoke_claude_with_prompt(vault_path, prompt, batch, "gmail-reply")
        all_ok = all_ok and ok

    # WhatsApp → whatsapp-reply skill (T042)
    if routes["whatsapp"]:
        file_list = "\n".join(f"- {f.name}" for f in routes["whatsapp"])
        prompt = _WHATSAPP_REPLY_PROMPT.format(file_list=file_list)
        ok = _invoke_claude_with_prompt(vault_path, prompt, routes["whatsapp"], "whatsapp-reply")
        all_ok = all_ok and ok

    # Calendar → calendar-event skill (T045)
    if routes["calendar"]:
        file_list = "\n".join(f"- {f.name}" for f in routes["calendar"])
        prompt = _CALENDAR_PROMPT.format(file_list=file_list)
        ok = _invoke_claude_with_prompt(vault_path, prompt, routes["calendar"], "calendar-event")
        all_ok = all_ok and ok

    # LinkedIn → linkedin-post skill (T052)
    if routes["linkedin"]:
        file_list = "\n".join(f"- {f.name}" for f in routes["linkedin"])
        prompt = _LINKEDIN_PROMPT.format(file_list=file_list)
        ok = _invoke_claude_with_prompt(vault_path, prompt, routes["linkedin"], "linkedin-post")
        all_ok = all_ok and ok

    # Fallback → Bronze plan-writing (original behaviour)
    if routes["bronze"]:
        file_list = "\n".join(f"- {f.name}" for f in routes["bronze"])
        prompt = PROMPT_TEMPLATE.format(file_list=file_list)
        ok = _invoke_claude_with_prompt(vault_path, prompt, routes["bronze"], "reasoning")
        all_ok = all_ok and ok

    return all_ok


def _move_to_in_progress(vault_path: Path, files: list[Path]) -> None:
    """Move processed files from Needs_Action/ to In_Progress/."""
    in_progress = vault_path / "In_Progress"
    for f in files:
        dest = in_progress / f.name
        try:
            shutil.move(str(f), str(dest))
            log_action(
                vault_path,
                action_type="file_move",
                actor="orchestrator",
                source=str(f),
                destination=str(dest),
                result="success",
            )
            print(f"  Moved: {f.name} → In_Progress/")
        except Exception as exc:
            log_action(
                vault_path,
                action_type="error",
                actor="orchestrator",
                source=str(f),
                result="error",
                error_message=str(exc),
            )
            print(f"  Error moving {f.name}: {exc}", file=sys.stderr)


def _update_dashboard(vault_path: Path) -> None:
    """Overwrite Vault/Dashboard.md with today's stats — T061.

    Pure Python log aggregation — no Claude invocation.
    """
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Count today's log entries by result
        log_file = vault_path / "Logs" / f"{today}.json"
        approved = rejected = 0
        action_counts: dict[str, int] = {}

        if log_file.exists():
            try:
                entries = json.loads(log_file.read_text(encoding="utf-8"))
                if isinstance(entries, list):
                    for entry in entries:
                        status = entry.get("approval_status", entry.get("result", ""))
                        if status == "approved":
                            approved += 1
                        elif status in ("rejected", "expired", "failed"):
                            rejected += 1
                        atype = entry.get("action_type", "")
                        if atype and atype not in ("system_start", "system_shutdown", "error", "file_move"):
                            action_counts[atype] = action_counts.get(atype, 0) + 1
            except Exception:
                pass

        pending = len(list((vault_path / "Pending_Approval").glob("*.md"))) if (vault_path / "Pending_Approval").exists() else 0
        needs_action = len(list((vault_path / "Needs_Action").glob("*.md"))) if (vault_path / "Needs_Action").exists() else 0

        action_lines = "\n".join(
            f"| {k} | {v} |" for k, v in sorted(action_counts.items())
        ) or "| (none) | 0 |"

        # Gold tier metrics
        gold_types = {
            "create_odoo_invoice": 0,
            "confirm_odoo_invoice": 0,
            "publish_facebook_post": 0,
            "publish_instagram_post": 0,
            "ralph_loop_iteration": 0,
            "ceo_briefing_generated": 0,
        }
        for k in gold_types:
            gold_types[k] = action_counts.get(k, 0)

        gold_lines = "\n".join(
            f"| {k} | {v} |" for k, v in gold_types.items()
        )

        dashboard = f"""\
# FTE Dashboard

**Updated**: {now_str}
**Date**: {today}

---

## Today's Activity

| Metric | Count |
|--------|-------|
| Actions approved | {approved} |
| Actions rejected/expired | {rejected} |
| Pending approval | {pending} |
| Needs action | {needs_action} |

## Action Breakdown (Today)

| Action Type | Count |
|-------------|-------|
{action_lines}

## Gold Tier Metrics (Today)

| Metric | Count |
|--------|-------|
{gold_lines}

---

*Auto-generated by fte-orchestrator. Last update: {now_str}*
"""
        (vault_path / "Dashboard.md").write_text(dashboard, encoding="utf-8")
    except Exception as exc:
        print(f"[orchestrator] Dashboard update failed: {exc}", file=sys.stderr)


def run_orchestrator(
    vault_path: Path,
    *,
    interval: int = 30,
    dry_run: bool = False,
) -> None:
    """Run the orchestrator as a blocking polling loop.

    Polls Needs_Action/ every ``interval`` seconds. When files are found,
    invokes Claude Code to generate plans, then moves processed files to
    In_Progress/.
    """
    shutdown_requested = False
    in_flight = False

    def _shutdown(signum, frame):  # noqa: ARG001
        nonlocal shutdown_requested
        shutdown_requested = True
        if not in_flight:
            pass  # Will exit at next loop check

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    mode = "[DRY RUN] " if dry_run else ""
    print(f"{mode}Orchestrator started. Polling Needs_Action/ every {interval}s.")

    log_action(
        vault_path,
        action_type="system_start",
        actor="orchestrator",
        parameters={
            "interval": interval,
            "vault_path": str(vault_path),
            "dry_run": dry_run,
        },
        result="success",
    )

    try:
        while not shutdown_requested:
            files = _list_needs_action(vault_path)

            if files:
                ts = time.strftime("%H:%M:%S")
                if dry_run:
                    print(f"[DRY RUN] Would invoke Claude for {len(files)} file(s):")
                    for f in files:
                        print(f"  - {f.name}")
                    print("[DRY RUN] No files moved. No Claude invocation.")
                    log_action(
                        vault_path,
                        action_type="reasoning",
                        actor="orchestrator",
                        parameters={"file_count": len(files), "dry_run": True},
                        result="skipped",
                    )
                else:
                    print(f"[{ts}] Found {len(files)} file(s) in Needs_Action/. Invoking Claude...")
                    in_flight = True
                    success = invoke_claude(vault_path, files)
                    in_flight = False

                    if success:
                        _move_to_in_progress(vault_path, files)
                        print(f"[{ts}] Claude completed.")
                    else:
                        print(f"[{ts}] Claude invocation failed. Files left in Needs_Action/.")
            else:
                ts = time.strftime("%H:%M:%S")
                print(f"[{ts}] Polling... (0 files in Needs_Action/)")

            # Update dashboard on every cycle — T061
            if not dry_run:
                _update_dashboard(vault_path)
                _check_briefing_schedule(vault_path)

            if shutdown_requested:
                break
            time.sleep(interval)
    finally:
        log_action(
            vault_path,
            action_type="system_shutdown",
            actor="orchestrator",
            result="success",
        )
        print(f"\n{mode}Orchestrator stopped.")
