# Quickstart: Bronze Tier — Vault & Filesystem Watcher

**Time to complete**: ~15 minutes
**Prerequisites**: Python 3.13+, uv, Claude Code CLI (authenticated)

## Step 1: Clone the Repository

```bash
git clone git@github.com:Tahasiraj1/Digital-FTE.git
cd Digital-FTE
```

## Step 2: Install Dependencies

```bash
uv sync
```

## Step 3: Initialize the Vault

```bash
uv run fte init --path ~/AI_Employee_Vault
```

Verify: Open `~/AI_Employee_Vault` in Obsidian. You should see 9
folders and `Company_Handbook.md`.

## Step 4: Edit Your Company Handbook (Optional)

Open `~/AI_Employee_Vault/Company_Handbook.md` in Obsidian or any
editor. Add your business context and rules. Claude will reference this
during reasoning.

## Step 5: Start the Filesystem Watcher

```bash
uv run fte watch --path ~/AI_Employee_Vault
```

Leave this terminal running.

## Step 6: Test — Drop a File

Open a new terminal:

```bash
echo "Client asked about project timeline. Please draft a reply." \
  > ~/AI_Employee_Vault/Inbox/reply-to-client.md
```

Within 5 seconds, check `Needs_Action/`:
```bash
ls ~/AI_Employee_Vault/Needs_Action/
# Expected: 2026-02-20-HHMMSS-reply-to-client.md
```

## Step 7: Start the Orchestrator

Open another terminal:

```bash
uv run fte orchestrate --path ~/AI_Employee_Vault --interval 30
```

Wait up to 30 seconds. Then check `Plans/`:
```bash
ls ~/AI_Employee_Vault/Plans/
# Expected: PLAN-reply-to-client.md
```

Read the plan:
```bash
cat ~/AI_Employee_Vault/Plans/PLAN-reply-to-client.md
```

## Step 8: Verify Logging

```bash
cat ~/AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json
```

You should see log entries for the file move and the reasoning run.

## Step 9: Stop

Press `Ctrl+C` in the watcher terminal and the orchestrator terminal.
Both shut down gracefully.

## What You've Proven

- [x] Vault folder structure works with Obsidian
- [x] Watcher detects new files and moves them with timestamps
- [x] Orchestrator invokes Claude and produces plan files
- [x] Logging captures every action
- [x] The Perception → Reasoning pipeline works end-to-end

## Next Steps

- Edit `Company_Handbook.md` with real business rules
- Drop real tasks into `Inbox/` and review Claude's plans
- When comfortable, proceed to Silver tier (Gmail watcher + MCP +
  approval workflow)
