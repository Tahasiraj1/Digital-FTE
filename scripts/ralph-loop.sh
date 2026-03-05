#!/usr/bin/env bash
# Ralph Wiggum Loop — Claude Code Stop Hook
#
# This script runs every time Claude Code finishes a turn and tries to exit.
# It implements the dual-completion strategy:
#   - AWAITING_APPROVAL in output → exit 0 (loop pauses for HITL)
#   - TASK_COMPLETE in output     → clear state, exit 0
#   - Task file in Done/          → clear state, exit 0
#   - Max iterations reached      → write timeout alert, clear state, exit 0
#   - Otherwise                   → increment iteration, exit 1 (re-inject prompt)
#
# The hook receives JSON on stdin: { "last_output": "...", "transcript_path": "..." }
#
# Environment:
#   VAULT_PATH — path to the Obsidian vault (default: /mnt/d/AI_Employee_Vault)

set -euo pipefail

VAULT_PATH="${VAULT_PATH:-/mnt/d/AI_Employee_Vault}"
STATE_FILE="${VAULT_PATH}/ralph_state.json"

# ---- Guard: If no state file, this is a normal (non-Ralph) invocation ----
if [ ! -f "$STATE_FILE" ]; then
    exit 0
fi

# ---- Read state ----
loop_id=$(python3 -c "import json,sys; d=json.load(open('$STATE_FILE')); print(d['loop_id'])")
task_file=$(python3 -c "import json,sys; d=json.load(open('$STATE_FILE')); print(d['task_file'])")
task_name=$(python3 -c "import json,sys; d=json.load(open('$STATE_FILE')); print(d['task_name'])")
iteration=$(python3 -c "import json,sys; d=json.load(open('$STATE_FILE')); print(d['iteration'])")
max_iterations=$(python3 -c "import json,sys; d=json.load(open('$STATE_FILE')); print(d['max_iterations'])")
continuation_prompt=$(python3 -c "import json,sys; d=json.load(open('$STATE_FILE')); print(d['continuation_prompt'])")

# ---- Read last_output from stdin JSON ----
last_output=""
if [ -t 0 ]; then
    # No stdin (manual invocation) — treat as no output
    last_output=""
else
    input_json=$(cat)
    last_output=$(echo "$input_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('last_output',''))" 2>/dev/null || echo "")
fi

# ---- Check 1: Approval gate reached ----
if echo "$last_output" | grep -q '<promise>AWAITING_APPROVAL</promise>'; then
    # Loop pauses — executor will re-trigger after dispatch
    exit 0
fi

# ---- Check 2: Task complete (promise) ----
if echo "$last_output" | grep -q '<promise>TASK_COMPLETE</promise>'; then
    rm -f "$STATE_FILE"
    exit 0
fi

# ---- Check 3: Task file moved to Done/ ----
if [ -f "${VAULT_PATH}/Done/${task_file}" ] || [ -f "${VAULT_PATH}/Done/${task_name}.md" ]; then
    rm -f "$STATE_FILE"
    exit 0
fi

# ---- Check 4: Max iterations ----
if [ "$iteration" -ge "$max_iterations" ]; then
    # Write timeout alert via Python helper
    python3 -c "
import sys
sys.path.insert(0, '/mnt/d/projects/FTE/src')
from fte.ralph_loop import read_state, write_timeout_alert, clear_state
from pathlib import Path
vault = Path('$VAULT_PATH')
state = read_state(vault)
if state:
    write_timeout_alert(vault, state)
    clear_state(vault)
"
    exit 0
fi

# ---- Default: Continue looping ----
# Increment iteration count
new_iteration=$((iteration + 1))
python3 -c "
import json
with open('$STATE_FILE', 'r') as f:
    state = json.load(f)
state['iteration'] = $new_iteration
with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
"

# Output the continuation prompt — Claude Code re-injects it
echo "$continuation_prompt"

# Exit non-zero to signal Claude Code to continue
exit 1
