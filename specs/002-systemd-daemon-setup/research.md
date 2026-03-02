# Research: Systemd Daemon Setup

**Feature**: `002-systemd-daemon-setup`
**Date**: 2026-02-23
**Input**: Spec questions and unknowns from `specs/002-systemd-daemon-setup/spec.md`

---

## Decision 1: System Service vs User Service

**Decision**: Use system services (`/etc/systemd/system/`) with `User=` directive.

**Rationale**:
On WSL2, user services (`systemctl --user`) only auto-start at boot if `loginctl enable-linger <username>` has been explicitly run — a persistent manual step that is easy to forget and not enforced. System services with `User=` start during `multi-user.target` unconditionally, regardless of whether a user session is open. This is the only fully automatic path on WSL2.

**Tradeoffs**:
- Requires `sudo` to install unit files to `/etc/systemd/system/`
- Does NOT inherit user shell environment (PATH, HOME) — must be set explicitly
- More reliable for 24/7 boot-time startup than user services

**Alternatives considered**:
- User services (`~/.config/systemd/user/`): No sudo needed, but requires linger to be enabled. Rejected because it adds a hidden prerequisite that breaks 24/7 intent.
- PM2 (constitution recommendation): No systemd needed, cross-platform. Rejected because user has confirmed systemd 255 is available and systemd is the native Linux solution — no additional tool (Node.js, npm) required.
- supervisord: Python-native but adds a dependency and config file. Rejected in favour of systemd (already present).

---

## Decision 2: uv Binary Path Detection

**Decision**: Use `command -v uv` as the primary probe, with a multi-location fallback. Embed the resolved absolute path into `ExecStart=` at install time.

**Rationale**:
System services do not inherit the user's interactive shell PATH. `~/.local/bin` (default uv install location on Linux) is not in systemd's minimal PATH. If `ExecStart=uv run ...` is used, the service will fail silently with "command not found" every start.

The deploy script runs interactively as the target user (where PATH is fully set), so `command -v uv` reliably resolves to the absolute path at install time. That path is then baked directly into the unit file — no PATH lookup needed at service startup.

**Fallback probe order** (if `command -v` returns empty):
1. `$UV_INSTALL_DIR/uv` (if env var set)
2. `$XDG_BIN_HOME/uv` (if env var set)
3. `$HOME/.local/bin/uv` (standard default)
4. `$HOME/.cargo/bin/uv` (cargo install)
5. `/usr/local/bin/uv`, `/usr/bin/uv` (system-wide installs)

**Confirmed path on this machine**: `/home/taha/.local/bin/uv`

**Alternatives considered**:
- Hardcoding `~/.local/bin/uv`: Rejected — not guaranteed, breaks on cargo/pipx/system installs.
- Setting `Environment=PATH=...` in unit file: Partially effective, but fragile if uv is ever moved. Absolute path is simpler and more robust.

---

## Decision 3: Unit File Generation Strategy

**Decision**: Generate unit files inline via heredoc inside `install.sh`. Do not store unit file templates as separate files in the repository.

**Rationale**:
The unit files contain machine-specific absolute paths (uv binary, vault path, project directory, username) that differ per machine. A template file would require a sed-substitution step anyway. Generating inline in the deploy script is simpler, reduces file count, and keeps all deployment logic in one place.

**Alternatives considered**:
- Storing `.service` template files in `deploy/` and substituting with `envsubst`/`sed`: More visible but identical functional result. Rejected to keep deploy/ minimal.

---

## Decision 4: Service Dependency (Orchestrator → Watcher)

**Decision**: Soft dependency using `After=fte-watcher.service` + `Wants=fte-watcher.service` in the orchestrator unit.

**Rationale**:
`After=` ensures the orchestrator starts only after the watcher has been started. `Wants=` tells systemd to also start the watcher when the orchestrator starts (if not already running). Critically, `Wants=` does NOT propagate failures — if the watcher crashes or fails to start, the orchestrator continues running. This is correct because the orchestrator polls the vault filesystem independently; it does not have a runtime dependency on the watcher process being alive.

**Alternatives considered**:
- `Requires=`: Hard dependency — orchestrator dies if watcher dies. Rejected because they are independent processes that happen to share a vault.
- `BindsTo=`: Even stricter than Requires. Rejected for same reason.
- No dependency: Both start independently in undefined order. Rejected because ordering makes startup cleaner (watcher ready before orchestrator begins polling).

---

## Decision 5: Restart Policy

**Decision**:
```ini
Restart=on-failure
RestartSec=5s
StartLimitBurst=5
StartLimitIntervalSec=60s
```
All directives placed in `[Service]` section (required by systemd v229+; in `[Unit]` they are silently ignored on systemd 255).

**Rationale**:
- `on-failure`: Restart only on non-zero exit or signal. A clean `exit(0)` (user ran `fte watch` to completion normally) does not trigger restart.
- `RestartSec=5s`: 5-second delay satisfies FR-004 (restart within 5 seconds of crash).
- `StartLimitBurst=5` + `StartLimitIntervalSec=60s`: After 5 failures in 60 seconds, systemd marks the service `failed` and stops retrying. Satisfies FR-005. Reset with `systemctl reset-failed fte-watcher`.

---

## Decision 6: Environment Variables in Unit Files

**Decision**: Set `HOME` and `PATH` explicitly in each unit file; use absolute path for `ExecStart`.

**Rationale**:
System services start in a minimal environment. `HOME` defaults to `/` (or root's home), not `/home/taha`. `uv` uses `HOME` to locate its cache (`~/.cache/uv`) and configuration. Without explicit `HOME`, uv may fail to find its own Python interpreter or write its cache.

```ini
Environment=HOME=/home/taha
Environment=PATH=/home/taha/.local/bin:/usr/local/bin:/usr/bin:/bin
```

The `PATH` entry is a secondary safety measure. The primary protection is using the absolute path in `ExecStart` (Decision 2).

---

## Decision 7: uv run and .venv Auto-Sync

**Decision**: Rely on `uv run` auto-sync behaviour. No explicit `uv sync` step in the service unit.

**Rationale**:
`uv run fte watch` automatically runs `uv sync` if `.venv` is absent or out of date with `uv.lock`. The project already has a committed `uv.lock` and an existing `.venv`. If `.venv` is ever deleted, `uv run` recreates it on the next service start. This means the service is self-healing for missing virtual environments.

**Caveat**: First start after `.venv` deletion is slow (dependency download). The service must have network access and write permission to the project directory. Both are true in this setup.
