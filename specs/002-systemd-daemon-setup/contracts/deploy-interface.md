# Contract: Deploy Interface

**Feature**: `002-systemd-daemon-setup`
**Date**: 2026-02-23

---

## Script 1: `deploy/install.sh`

### Invocation

```bash
sudo bash deploy/install.sh
```

Must be run from the project root directory (where `pyproject.toml` lives).
Must be run as or via `sudo` to write to `/etc/systemd/system/`.

### Prerequisites (checked at runtime; script exits with code 1 if any fail)

| Check | Error message if fails |
|-------|----------------------|
| systemd is available | `ERROR: systemd is not available. WSL2 requires systemd enabled in /etc/wsl.conf` |
| uv binary found (PATH or fallback locations) | `ERROR: uv not found. Install uv first: curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Vault directory exists at `$HOME/AI_Employee_Vault` | `ERROR: Vault not initialized. Run: uv run fte init --path ~/AI_Employee_Vault` |
| pyproject.toml exists in project root | `ERROR: Must be run from the FTE project root (pyproject.toml not found)` |

### Output (stdout)

```
[FTE Deploy] Detecting paths...
  USER:        taha
  HOME:        /home/taha
  UV_BIN:      /home/taha/.local/bin/uv
  PROJECT_DIR: /mnt/d/projects/FTE
  VAULT_PATH:  /home/taha/AI_Employee_Vault

[FTE Deploy] Installing fte-watcher.service...
  ✓ Unit file written to /etc/systemd/system/fte-watcher.service

[FTE Deploy] Installing fte-orchestrator.service...
  ✓ Unit file written to /etc/systemd/system/fte-orchestrator.service

[FTE Deploy] Reloading systemd daemon...
  ✓ daemon-reload complete

[FTE Deploy] Enabling services (auto-start on boot)...
  ✓ fte-watcher.service enabled
  ✓ fte-orchestrator.service enabled

[FTE Deploy] Starting services...
  ✓ fte-watcher.service started
  ✓ fte-orchestrator.service started

[FTE Deploy] Done. FTE is running 24/7.

  Check status:  systemctl status fte-watcher fte-orchestrator
  View logs:     journalctl -u fte-watcher -f
                 journalctl -u fte-orchestrator -f
  Uninstall:     sudo bash deploy/uninstall.sh
```

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Both services installed, enabled, and started successfully |
| `1` | Prerequisite check failed (message printed to stderr) |

### Idempotency

Running `install.sh` when services are already installed:
- Stops running services first (`systemctl stop`)
- Overwrites existing unit files with current configuration
- Restarts services

This allows reconfiguration (e.g., vault path change) by editing the script and re-running.

---

## Script 2: `deploy/uninstall.sh`

### Invocation

```bash
sudo bash deploy/uninstall.sh
```

### Output (stdout)

```
[FTE Uninstall] Stopping services...
  ✓ fte-watcher.service stopped (or was not running)
  ✓ fte-orchestrator.service stopped (or was not running)

[FTE Uninstall] Disabling services...
  ✓ fte-watcher.service disabled (or was not enabled)
  ✓ fte-orchestrator.service disabled (or was not enabled)

[FTE Uninstall] Removing unit files...
  ✓ /etc/systemd/system/fte-watcher.service removed (or did not exist)
  ✓ /etc/systemd/system/fte-orchestrator.service removed (or did not exist)

[FTE Uninstall] Reloading systemd daemon...
  ✓ daemon-reload complete

[FTE Uninstall] Done. FTE services removed.
```

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Services removed (or were not installed — both idempotent) |

---

## Useful operational commands (not part of deploy scripts)

| Action | Command |
|--------|---------|
| Check status of both | `systemctl status fte-watcher fte-orchestrator` |
| Follow watcher logs | `journalctl -u fte-watcher -f` |
| Follow orchestrator logs | `journalctl -u fte-orchestrator -f` |
| View logs since boot | `journalctl -u fte-watcher --since today` |
| Restart both | `sudo systemctl restart fte-watcher fte-orchestrator` |
| Reset failed state | `sudo systemctl reset-failed fte-watcher fte-orchestrator` |
| View unit file | `systemctl cat fte-watcher` |
