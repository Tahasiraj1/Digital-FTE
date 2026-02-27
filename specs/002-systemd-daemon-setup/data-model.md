# Data Model: Systemd Daemon Setup

**Feature**: `002-systemd-daemon-setup`
**Date**: 2026-02-23

This feature does not manage application data. Its "entities" are the deployment artifacts produced and managed by the deploy scripts.

---

## Entity 1: SystemdUnitFile

A `.service` file installed to `/etc/systemd/system/`. One exists per FTE component.

| Field | Value (watcher) | Value (orchestrator) |
|-------|----------------|---------------------|
| `filename` | `fte-watcher.service` | `fte-orchestrator.service` |
| `Description` | FTE Filesystem Watcher | FTE Orchestrator |
| `After` | `network.target` | `network.target fte-watcher.service` |
| `Wants` | `network.target` | `fte-watcher.service` |
| `Type` | `simple` | `simple` |
| `User` | `<detected at install>` | `<detected at install>` |
| `Group` | `<detected at install>` | `<detected at install>` |
| `WorkingDirectory` | `<project root — absolute>` | `<project root — absolute>` |
| `ExecStart` | `<uv absolute path> run fte watch --path <vault absolute path>` | `<uv absolute path> run fte orchestrate --path <vault absolute path> --interval 30` |
| `Restart` | `on-failure` | `on-failure` |
| `RestartSec` | `5s` | `5s` |
| `StartLimitBurst` | `5` | `5` |
| `StartLimitIntervalSec` | `60s` | `60s` |
| `Environment HOME` | `<home dir — absolute>` | `<home dir — absolute>` |
| `Environment PATH` | `<uv dir>:/usr/local/bin:/usr/bin:/bin` | `<uv dir>:/usr/local/bin:/usr/bin:/bin` |
| `StandardOutput` | `journal` | `journal` |
| `StandardError` | `journal` | `journal` |
| `WantedBy` | `multi-user.target` | `multi-user.target` |

**Install path**: `/etc/systemd/system/<filename>`
**State after install**: enabled + active (running)

---

## Entity 2: DeployScript (install.sh)

The install script that generates and activates both service units.

| Property | Value |
|----------|-------|
| Path | `deploy/install.sh` |
| Invocation | `sudo bash deploy/install.sh` (from project root) |
| Prerequisites | systemd available, uv on PATH, vault initialized |
| Idempotent | Yes — re-running stops, reinstalls, and restarts services |
| Output | Confirmation line per step to stdout |
| Exit codes | `0` success, `1` prerequisite check failed |

**Runtime-detected values** (resolved at install time, embedded in unit files):
- `USER` — current user (`whoami`)
- `HOME_DIR` — absolute home path (`$HOME`)
- `UV_BIN` — absolute path to uv binary (`command -v uv` + fallback probe)
- `PROJECT_DIR` — absolute path to project root (directory of install.sh's parent)
- `VAULT_PATH` — `$HOME/AI_Employee_Vault`
- `UV_DIR` — parent directory of UV_BIN (for PATH environment variable)

---

## Entity 3: UninstallScript (uninstall.sh)

The script that removes both service units cleanly.

| Property | Value |
|----------|-------|
| Path | `deploy/uninstall.sh` |
| Invocation | `sudo bash deploy/uninstall.sh` |
| Idempotent | Yes — safe to run when services are not installed |
| Output | Confirmation line per step to stdout |
| Exit codes | `0` success |

**Operations performed** (in order):
1. Stop both services (ignore error if not running)
2. Disable both services (ignore error if not enabled)
3. Remove both unit files from `/etc/systemd/system/`
4. `systemctl daemon-reload`

---

## Entity 4: ServiceState

The runtime state of a deployed service as tracked by systemd.

| State | Meaning | Recovery |
|-------|---------|----------|
| `active (running)` | Process running normally | None needed |
| `activating` | Process starting up | Wait |
| `failed` | Hit StartLimitBurst within StartLimitIntervalSec | `systemctl reset-failed <name>` then `systemctl start <name>` |
| `inactive (dead)` | Stopped cleanly | `systemctl start <name>` |
| `Unit not found` | Service not installed | Run `deploy/install.sh` |
