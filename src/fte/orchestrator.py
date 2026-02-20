"""Orchestrator — polls Needs_Action/ and invokes Claude Code for reasoning."""

from __future__ import annotations

import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from fte.logger import log_action

CLAUDE_TIMEOUT_S = 120

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


def _list_needs_action(vault_path: Path) -> list[Path]:
    """Return sorted list of files in Needs_Action/."""
    needs_action = vault_path / "Needs_Action"
    if not needs_action.exists():
        return []
    return sorted(f for f in needs_action.iterdir() if f.is_file())


def invoke_claude(vault_path: Path, files: list[Path]) -> bool:
    """Invoke Claude Code via subprocess to reason over the given files.

    Returns True on success, False on failure.
    """
    file_list = "\n".join(f"- {f.name}" for f in files)
    prompt = PROMPT_TEMPLATE.format(file_list=file_list)

    start = time.monotonic()
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--cwd", str(vault_path)],
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT_S,
        )
        duration = int((time.monotonic() - start) * 1000)

        if result.returncode != 0:
            log_action(
                vault_path,
                action_type="error",
                actor="orchestrator",
                parameters={"stderr": result.stderr[:500]},
                result="error",
                error_message=f"Claude exited with code {result.returncode}",
                duration_ms=duration,
            )
            print(f"Claude error (exit {result.returncode}): {result.stderr[:200]}", file=sys.stderr)
            return False

        log_action(
            vault_path,
            action_type="reasoning",
            actor="claude",
            parameters={"file_count": len(files)},
            result="success",
            duration_ms=duration,
        )
        return True

    except FileNotFoundError:
        duration = int((time.monotonic() - start) * 1000)
        log_action(
            vault_path,
            action_type="error",
            actor="orchestrator",
            result="error",
            error_message="Claude Code CLI not found. Install with: npm install -g @anthropic/claude-code",
            duration_ms=duration,
        )
        print("Error: Claude Code CLI not found. Install with: npm install -g @anthropic/claude-code", file=sys.stderr)
        return False

    except subprocess.TimeoutExpired:
        duration = int((time.monotonic() - start) * 1000)
        log_action(
            vault_path,
            action_type="error",
            actor="orchestrator",
            result="error",
            error_message=f"Claude timed out after {CLAUDE_TIMEOUT_S}s",
            duration_ms=duration,
        )
        print(f"Error: Claude timed out after {CLAUDE_TIMEOUT_S}s", file=sys.stderr)
        return False


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
