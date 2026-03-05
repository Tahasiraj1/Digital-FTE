"""Ralph Loop state management — read/write/clear ralph_state.json.

The Ralph Wiggum Loop is a Claude Code Stop hook pattern that keeps Claude
iterating across a multi-step task chain until completion or an explicit
approval pause. This module manages the persistent state file that coordinates
between the orchestrator, the Stop hook script, and the executor.

State file location: Vault/ralph_state.json
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import frontmatter


@dataclass
class RalphLoopState:
    """Persistent state for a single Ralph Loop iteration chain."""

    loop_id: str
    task_file: str
    task_name: str
    iteration: int = 0
    max_iterations: int = 10
    continuation_prompt: str = "Continue working on the current task. Check your progress and proceed to the next step."
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    chain_step: int = 0
    chain_cap: int = 3


def _state_path(vault_path: Path) -> Path:
    """Return the path to ralph_state.json in the vault."""
    return vault_path / "ralph_state.json"


def read_state(vault_path: Path) -> RalphLoopState | None:
    """Read the current Ralph Loop state from the vault.

    Returns None if no state file exists or if it cannot be parsed.
    """
    path = _state_path(vault_path)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return RalphLoopState(**data)
    except (json.JSONDecodeError, TypeError, KeyError):
        return None


def write_state(vault_path: Path, state: RalphLoopState) -> None:
    """Write Ralph Loop state to the vault (atomic rename).

    Uses a temporary file + rename to prevent partial writes from
    corrupting the state file during a crash.
    """
    target = _state_path(vault_path)
    data = json.dumps(asdict(state), indent=2, ensure_ascii=False)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(vault_path), prefix=".ralph_state_", suffix=".tmp"
    )
    try:
        os.write(fd, data.encode("utf-8"))
        os.close(fd)
        os.replace(tmp_path, str(target))
    except Exception:
        os.close(fd) if not os.get_inheritable(fd) else None
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def clear_state(vault_path: Path) -> None:
    """Remove the Ralph Loop state file if it exists."""
    path = _state_path(vault_path)
    if path.exists():
        path.unlink()


def write_timeout_alert(vault_path: Path, state: RalphLoopState) -> None:
    """Write a SYSTEM_ralph-loop-timeout.md alert to Needs_Action/.

    Called when the loop reaches max_iterations without completing.
    """
    needs_action = vault_path / "Needs_Action"
    needs_action.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    alert_path = needs_action / "SYSTEM_ralph-loop-timeout.md"

    content = f"""\
---
type: system_alert
alert_type: ralph_loop_timeout
loop_id: "{state.loop_id}"
task_file: "{state.task_file}"
iterations_reached: {state.max_iterations}
created_at: "{now}"
---

# Ralph Loop Timeout

The autonomous loop for task `{state.task_file}` reached the maximum iteration limit ({state.max_iterations}) without completing.

**Action required**: Review the task and restart the loop manually, or resolve the blocking step.
"""
    alert_path.write_text(content, encoding="utf-8")


def generate_loop_id() -> str:
    """Generate a unique loop ID: ralph-YYYYMMDD-<random6>."""
    import secrets

    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = secrets.token_hex(3)
    return f"ralph-{date_part}-{random_part}"


def create_state_for_task(
    vault_path: Path, task_file: Path
) -> RalphLoopState:
    """Create a new RalphLoopState for a task file.

    Reads max_iterations and chain_cap from environment variables.
    """
    max_iter = int(os.environ.get("RALPH_MAX_ITERATIONS", "10"))
    chain_cap = int(os.environ.get("RALPH_CHAIN_CAP", "3"))

    # Read chain_step from frontmatter if this is a continuation task
    chain_step = 0
    try:
        post = frontmatter.load(str(task_file))
        chain_step = int(post.get("chain_step", 0))
    except Exception:
        pass

    return RalphLoopState(
        loop_id=generate_loop_id(),
        task_file=task_file.name,
        task_name=task_file.stem,
        max_iterations=max_iter,
        chain_step=chain_step,
        chain_cap=chain_cap,
    )
