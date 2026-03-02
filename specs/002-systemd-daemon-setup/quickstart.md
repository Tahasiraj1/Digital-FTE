# Quickstart: Systemd Daemon Setup

**Feature**: `002-systemd-daemon-setup`
**Time to complete**: ~5 minutes
**Prerequisites**: Bronze tier complete (`fte init` run, vault exists at `~/AI_Employee_Vault`)

---

## Step 1: Confirm systemd is available

```bash
systemctl --version
```

Expected: `systemd 2XX ...`. If this errors, enable systemd in `/etc/wsl.conf` first.

---

## Step 2: Confirm uv is on PATH

```bash
which uv
```

Expected: `/home/<you>/.local/bin/uv` (or similar). If not found, install uv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Step 3: Run the deploy script from the project root

```bash
cd /mnt/d/projects/FTE
sudo bash deploy/install.sh
```

The script will:
1. Detect your username, home dir, uv path, vault path, and project dir
2. Generate and install both unit files to `/etc/systemd/system/`
3. Enable auto-start on boot
4. Start both services immediately

Expected output ends with: `FTE is running 24/7.`

---

## Step 4: Verify both services are active

```bash
systemctl status fte-watcher fte-orchestrator
```

Both should show `Active: active (running)`.

---

## Step 5: Test — drop a task without any terminal

Close all terminals. Open a new WSL2 window and drop a task:

```bash
echo "Draft a reply to Ahmed about the project status." \
  > ~/AI_Employee_Vault/Inbox/reply-ahmed.md
```

Wait ~35 seconds (watcher interval + orchestrator interval). Then check:

```bash
ls ~/AI_Employee_Vault/Plans/
ls ~/AI_Employee_Vault/In_Progress/
```

No `fte watch` or `fte orchestrate` terminal needed — the daemons are running in the background.

---

## Step 6: Test crash recovery

```bash
# Get the watcher PID
systemctl status fte-watcher | grep "Main PID"

# Kill it hard
sudo kill -9 <pid>

# Wait 5 seconds, then check
sleep 6 && systemctl status fte-watcher
```

Expected: `Active: active (running)` again — systemd restarted it automatically.

---

## Step 7: Test reboot persistence

From PowerShell (Windows):
```powershell
wsl --shutdown
wsl
```

After WSL2 restarts, run:
```bash
systemctl status fte-watcher fte-orchestrator
```

Both should be running — no manual action needed.

---

## Viewing logs

```bash
# Follow watcher live
journalctl -u fte-watcher -f

# Follow orchestrator live
journalctl -u fte-orchestrator -f

# All FTE logs since boot
journalctl -u fte-watcher -u fte-orchestrator --since today
```

---

## Uninstall

```bash
sudo bash deploy/uninstall.sh
```

Stops, disables, and removes both services. Returns to manual operation mode.

---

## What you've proven

- [x] Both FTE processes run permanently without any terminal session
- [x] Services survive WSL2 reboots
- [x] Crash recovery is automatic (no manual restart needed)
- [x] Logs are accessible via `journalctl`
- [x] The full Perception → Reasoning pipeline is always-on: 168 hours/week, zero manual intervention
