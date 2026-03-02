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

def _route_files(vault_path: Path, files: list[Path]) -> dict[str, list[Path]]:
    """Split files into routing groups based on their type/content.

    Returns:
        {
          "email": [...],
          "whatsapp": [...],
          "calendar": [...],
          "linkedin": [...],
          "bronze": [...],   # fallback: Bronze plan-writing
        }
    """
    routes: dict[str, list[Path]] = {
        "email": [],
        "whatsapp": [],
        "calendar": [],
        "linkedin": [],
        "bronze": [],
    }

    for f in files:
        task_type = _get_task_type(f)
        if task_type == "email":
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




def invoke_claude(vault_path: Path, files: list[Path]) -> bool:
    """Invoke Claude Code to reason over files, routing each to the right skill.

    Returns True if all routes succeeded (or had no files).
    """
    routes = _route_files(vault_path, files)
    all_ok = True

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
