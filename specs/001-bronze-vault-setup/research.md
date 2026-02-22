# Research: Bronze Tier — Vault & Filesystem Watcher

**Date**: 2026-02-20
**Branch**: `001-bronze-vault-setup`

## R1: Filesystem Watching — watchdog vs polling

**Decision**: Use `watchdog` library for the filesystem watcher (Inbox →
Needs_Action), and simple `time.sleep` polling for the orchestrator
(Needs_Action → Claude invocation).

**Rationale**: The hackathon doc explicitly uses `watchdog` for the
filesystem watcher (line 354: `from watchdog.observers import Observer`).
For the orchestrator's polling of Needs_Action, a simple
`os.listdir()` + `time.sleep(interval)` loop is sufficient — no event-
driven watching needed since files arrive infrequently and latency of
30-60s is acceptable.

**Alternatives considered**:
- `inotify` (Linux-only, not cross-platform)
- Pure polling for both (works but misses rapid Inbox drops)
- `asyncio` + `aiofiles` (over-engineered for Bronze)

## R2: Claude Code Invocation Method

**Decision**: Invoke Claude Code via `subprocess.run()` using the `-p`
(print/non-interactive) flag with `--cwd` pointing to the vault.

**Rationale**: The hackathon doc states Claude runs "pointed at your
Obsidian vault" (line 208) and the troubleshooting FAQ suggests using
`--cwd` flag (line 993). The `-p` flag runs Claude in non-interactive
mode, processes the prompt, writes output, and exits — perfect for the
orchestrator's invoke-and-wait pattern.

**Command pattern**:
```
claude -p "Read all files in Needs_Action/. For each file, reason about
what action is needed and write a plan to Plans/. Move processed files
to In_Progress/. Reference Company_Handbook.md for rules." --cwd /path/to/vault
```

**Alternatives considered**:
- Claude Code SDK (Python) — not yet stable for subprocess orchestration
- Direct Anthropic API — bypasses Claude Code's file system tools
- Interactive mode with pipe — fragile, hard to capture completion

## R3: Project Structure — uv for Python Project Management

**Decision**: Use `uv` with `pyproject.toml` for dependency management
and virtual environment. Single `src/` layout.

**Rationale**: Constitution mandates Python 3.13+ with `uv` (line 132).
`uv` is the modern Python project manager — handles venv creation,
dependency resolution, and script running. A single `src/` directory
keeps Bronze simple.

**Alternatives considered**:
- `poetry` (slower, heavier)
- `pip` + `requirements.txt` (no lock file, no venv management)
- `conda` (data science focused, overkill)

## R4: Logging Format — JSON Lines

**Decision**: Use JSON Lines format (one JSON object per line, appended)
for log files at `Logs/YYYY-MM-DD.json`.

**Rationale**: Constitution requires structured JSON to
`/Logs/YYYY-MM-DD.json` (Principle VI). JSON Lines (JSONL) allows
atomic appends without reading/parsing the entire file. Each line is a
self-contained JSON object. This is the standard pattern for append-only
structured logs.

**Alternatives considered**:
- JSON array (requires read-modify-write, not append-safe)
- CSV (not structured enough for nested fields)
- SQLite (overkill for Bronze, adds dependency)

## R5: Lockfile Strategy for Single-Instance Watcher

**Decision**: Use a PID-based lockfile at `/tmp/fte-watcher.pid` (or
vault-relative `.lock` file). Check PID validity on startup; stale locks
are cleaned automatically.

**Rationale**: FR-005 requires lockfile for duplicate prevention. PID
files are the standard Unix pattern. Checking whether the PID is still
running prevents stale lock issues after crashes.

**Alternatives considered**:
- `fcntl.flock` (Unix-only, not cross-platform on Windows/WSL edge cases)
- Named mutex (OS-specific)
- Port binding (unnecessary network dependency)

## R6: Process Management at Bronze

**Decision**: No process manager at Bronze. Users start the watcher and
orchestrator manually via CLI. Recommend PM2 in docs for users who want
persistence.

**Rationale**: Constitution mentions PM2 as "recommended" (line 135),
but Bronze tier is about understanding the system, not production
deployment. Adding PM2 as a hard dependency increases setup complexity
and obscures the actual process lifecycle. The quickstart should show
manual start/stop; docs can mention PM2 as an upgrade.

**Alternatives considered**:
- PM2 required (adds Node.js dependency just for process management)
- supervisord (Linux-only)
- systemd (Linux-only, requires root)
