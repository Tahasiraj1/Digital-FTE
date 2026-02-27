# Feature Specification: Systemd Daemon Setup

**Feature Branch**: `002-systemd-daemon-setup`
**Created**: 2026-02-23
**Status**: Draft
**Input**: User description: "Add systemd service files and a deploy script so the watcher and orchestrator run 24/7 on WSL2 without manual terminal sessions, with auto-restart on crash and auto-start on boot."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — One-Command Deploy (Priority: P1)

As a developer who has completed Bronze tier setup, I want to run a single deploy script that installs and activates both FTE services so that both the watcher and orchestrator start immediately and survive reboots — with no manual terminal management required.

**Why this priority**: This is the core value of the feature. Without it, the user must open two terminals every time their machine restarts. A single deploy command is the minimum viable deliverable.

**Independent Test**: Run `deploy/install.sh` on a machine with a working Bronze tier install. Both services should be active immediately without any further user action.

**Acceptance Scenarios**:

1. **Given** the vault has been initialized with `fte init`, **When** the user runs `deploy/install.sh`, **Then** both `fte-watcher` and `fte-orchestrator` services are installed, enabled, and started in under 30 seconds.
2. **Given** both services are running, **When** the user reboots their WSL2 instance, **Then** both services resume automatically without any user action.
3. **Given** both services are running, **When** the user runs `deploy/install.sh` again, **Then** the script is idempotent — it succeeds without errors and does not create duplicate services.

---

### User Story 2 — Auto-Recovery from Crash (Priority: P2)

As a developer running the FTE 24/7, I want the watcher and orchestrator to automatically restart if they crash so that a transient error (network blip, API timeout, unhandled exception) does not require manual intervention to recover.

**Why this priority**: Without crash recovery, 24/7 operation is impossible in practice. Any unhandled exception silently kills the process and leaves tasks unprocessed.

**Independent Test**: Kill one of the service processes directly (`kill <pid>`), wait 5 seconds, verify the service is running again via `systemctl status`.

**Acceptance Scenarios**:

1. **Given** `fte-watcher` is running as a service, **When** the process is killed with SIGKILL, **Then** systemd restarts it within 5 seconds.
2. **Given** `fte-orchestrator` is running as a service, **When** the process exits with a non-zero code, **Then** systemd restarts it within 5 seconds.
3. **Given** a service is crash-looping (failing on every start), **When** it fails 5 times in 60 seconds, **Then** systemd stops retrying to prevent runaway resource use.

---

### User Story 3 — Status and Log Inspection (Priority: P3)

As a developer, I want to check the health and logs of both services using standard OS tools so that I can diagnose issues without navigating to vault log files.

**Why this priority**: Without visibility into running services, debugging a 24/7 daemon is very difficult. This is about operational usability, not core function.

**Independent Test**: After services are running, use `systemctl status fte-watcher` and `journalctl -u fte-orchestrator` to confirm output is readable and informative.

**Acceptance Scenarios**:

1. **Given** both services are running, **When** the user runs `systemctl status fte-watcher`, **Then** the output shows `Active: active (running)` with uptime and recent log lines.
2. **Given** the orchestrator has processed a task, **When** the user runs `journalctl -u fte-orchestrator`, **Then** relevant output is visible (startup, poll cycle, Claude invocation result).
3. **Given** a service has crashed and restarted, **When** the user inspects its journal, **Then** both the crash and restart events are visible with timestamps.

---

### User Story 4 — Clean Uninstall (Priority: P4)

As a developer, I want to remove the systemd services cleanly with a single command so that I can reset to manual operation or reconfigure without leaving orphaned service files.

**Why this priority**: Uninstall is needed only occasionally but must exist to avoid leaving the system in a broken state.

**Independent Test**: Run `deploy/uninstall.sh`, then confirm `systemctl status fte-watcher` reports "Unit not found".

**Acceptance Scenarios**:

1. **Given** both services are installed and running, **When** the user runs `deploy/uninstall.sh`, **Then** both services are stopped, disabled, and their unit files removed.
2. **Given** the services are not installed, **When** the user runs `deploy/uninstall.sh`, **Then** the script exits cleanly without errors (idempotent).

---

### Edge Cases

- What happens if `uv` is not on system `PATH` when systemd starts the service? (System PATH differs from interactive shell PATH)
- What happens if `~/AI_Employee_Vault` does not exist when the service starts?
- What happens if systemd is not enabled in WSL2 and the user runs the deploy script?
- What happens if the deploy script is run as root instead of the regular user?
- What happens if one service installs successfully but the second fails mid-script?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The deploy script MUST install systemd unit files for both `fte-watcher` and `fte-orchestrator` services.
- **FR-002**: Both services MUST start immediately after installation without requiring a reboot.
- **FR-003**: Both services MUST be enabled to auto-start on WSL2 boot.
- **FR-004**: Both services MUST restart automatically within 5 seconds of an unclean exit (crash or non-zero exit code).
- **FR-005**: Services MUST NOT restart infinitely on persistent failure — a restart limit MUST be configured (max 5 restarts per 60 seconds).
- **FR-006**: The deploy script MUST be idempotent — running it multiple times MUST NOT create duplicate services or fail.
- **FR-007**: The deploy script MUST detect the correct `uv` binary path at install time and embed it in the service unit file.
- **FR-008**: The deploy script MUST detect the current user's home directory and vault path dynamically — no hardcoded paths.
- **FR-009**: The deploy script MUST detect the project working directory dynamically (where `pyproject.toml` lives).
- **FR-010**: Service logs MUST be captured by the systemd journal (stdout and stderr).
- **FR-011**: The uninstall script MUST stop, disable, and remove both service unit files cleanly.
- **FR-012**: Both scripts MUST check that systemd is available before proceeding and exit with a clear error message if not.
- **FR-013**: The deploy script MUST print a confirmation of each step so the user can verify progress.

### Key Entities

- **Service Unit File**: A systemd `.service` file defining how to start, stop, and restart an FTE process. One per component (watcher, orchestrator).
- **Deploy Script** (`deploy/install.sh`): Shell script that installs unit files, reloads the service manager, and enables and starts both services.
- **Uninstall Script** (`deploy/uninstall.sh`): Shell script that stops, disables, and removes both services cleanly.
- **`deploy/` directory**: New top-level directory in the repository holding all deployment artifacts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After running the deploy script, both services are active with zero additional user actions required.
- **SC-002**: After a WSL2 restart, both services resume without any terminal interaction — confirmed by checking service status from a fresh WSL2 session.
- **SC-003**: After killing a service process directly, it recovers and is running again within 5 seconds.
- **SC-004**: The deploy script completes successfully in under 30 seconds on a machine with working Bronze tier setup.
- **SC-005**: Running the deploy script a second time produces no errors and leaves services in the same running state (idempotent).
- **SC-006**: After running the uninstall script, no FTE service unit files remain and both service names are unknown to the service manager.
- **SC-007**: A task file placed in `Needs_Action/` is processed within one poll interval (≤ 30 seconds) after services auto-start on reboot — confirming the full pipeline is operational with no manual action.

## Assumptions

- **A-001**: Python 3.13+ and `uv` are already installed (Bronze tier prerequisite). The deploy script does not install them.
- **A-002**: The vault has already been initialized with `fte init` before the deploy script is run.
- **A-003**: The user is on WSL2 with systemd enabled (confirmed: systemd 255 is running).
- **A-004**: Services run as the current non-root user to match vault file ownership and `uv` install location.
- **A-005**: The vault path defaults to `~/AI_Employee_Vault`. Making this configurable is a future concern.
- **A-006**: The orchestrator poll interval defaults to 30 seconds. Tuning this is out of scope for this feature.
- **A-007**: The deploy script is run from the project root directory (`/mnt/d/projects/FTE` or equivalent).
