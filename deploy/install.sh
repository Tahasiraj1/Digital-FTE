#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# FTE Deploy — install.sh
# Installs fte-watcher and fte-orchestrator as systemd system services.
#
# Usage: sudo bash deploy/install.sh [--vault /path/to/vault]
#   --vault  Path to the AI Employee vault (default: ~/AI_Employee_Vault)
# =============================================================================

# ---------------------------------------------------------------------------
# Resolve the real invoking user even when run under sudo.
# sudo changes $HOME to /root and $USER to root, so we must look up the
# original user's home via /etc/passwd to find their uv install.
# ---------------------------------------------------------------------------
REAL_USER="${SUDO_USER:-$(whoami)}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
VAULT_ARG=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --vault)
            VAULT_ARG="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: sudo bash deploy/install.sh [--vault /path/to/vault]" >&2
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# find_uv: locate the uv binary via PATH or well-known install locations.
# Probes in this order:
#   1. PATH (via command -v) — fastest, correct in interactive shells
#   2. REAL_HOME/.local/bin — standard uv user install (sudo-safe)
#   3. $UV_INSTALL_DIR / $XDG_BIN_HOME fallbacks
#   4. REAL_HOME/.cargo/bin — cargo install
#   5. /usr/local/bin, /usr/bin — system-wide installs
# Prints absolute path to stdout; returns 1 if not found.
# ---------------------------------------------------------------------------
find_uv() {
    if command -v uv &>/dev/null; then
        command -v uv
        return 0
    fi

    # Check real user's home first (sudo-safe: $HOME is /root under sudo)
    if [[ -x "$REAL_HOME/.local/bin/uv" ]]; then
        echo "$REAL_HOME/.local/bin/uv"
        return 0
    fi

    local user_bin="${UV_INSTALL_DIR:-${XDG_BIN_HOME:-$REAL_HOME/.local/bin}}/uv"
    if [[ -x "$user_bin" ]]; then
        echo "$user_bin"
        return 0
    fi

    if [[ -x "$REAL_HOME/.cargo/bin/uv" ]]; then
        echo "$REAL_HOME/.cargo/bin/uv"
        return 0
    fi

    for candidate in /usr/local/bin/uv /usr/bin/uv; do
        if [[ -x "$candidate" ]]; then
            echo "$candidate"
            return 0
        fi
    done

    return 1
}

# ---------------------------------------------------------------------------
# check_prerequisites: validate all required conditions before installing.
# Exits 1 with a clear error message if any condition is unmet.
# ---------------------------------------------------------------------------
check_prerequisites() {
    if ! systemctl --version &>/dev/null; then
        echo "ERROR: systemd is not available. WSL2 requires systemd enabled in /etc/wsl.conf" >&2
        exit 1
    fi

    if ! find_uv &>/dev/null; then
        echo "ERROR: uv not found. Install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
        exit 1
    fi

    local vault="${VAULT_ARG:-$REAL_HOME/AI_Employee_Vault}"
    if [[ ! -d "$vault" ]]; then
        echo "ERROR: Vault not found at $vault" >&2
        echo "       Run: uv run fte init --path $vault" >&2
        exit 1
    fi

    if [[ ! -f "pyproject.toml" ]]; then
        echo "ERROR: Must be run from the FTE project root (pyproject.toml not found)" >&2
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# detect_paths: resolve all machine-specific absolute paths and export them
# as global variables for use by the unit file generators.
# ---------------------------------------------------------------------------
detect_paths() {
    USER_NAME="$REAL_USER"
    HOME_DIR="$REAL_HOME"
    UV_BIN=$(find_uv)
    UV_DIR=$(dirname "$UV_BIN")
    PROJECT_DIR=$(realpath .)
    VAULT_PATH="${VAULT_ARG:-$REAL_HOME/AI_Employee_Vault}"

    echo "  USER:        $USER_NAME"
    echo "  HOME:        $HOME_DIR"
    echo "  UV_BIN:      $UV_BIN"
    echo "  PROJECT_DIR: $PROJECT_DIR"
    echo "  VAULT_PATH:  $VAULT_PATH"
}

# ---------------------------------------------------------------------------
# install_watcher_unit: generate and install /etc/systemd/system/fte-watcher.service
# Requires detect_paths() to have run first (uses USER_NAME, UV_BIN, etc.)
# ---------------------------------------------------------------------------
install_watcher_unit() {
    sudo tee /etc/systemd/system/fte-watcher.service > /dev/null <<EOF
[Unit]
Description=FTE Filesystem Watcher
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER_NAME
Group=$USER_NAME
WorkingDirectory=$PROJECT_DIR
ExecStart=$UV_BIN run fte watch --path $VAULT_PATH
Restart=on-failure
RestartSec=5s
# systemd v229+: StartLimit* must be in [Service], silently ignored in [Unit]
StartLimitBurst=5
StartLimitIntervalSec=60s
Environment=HOME=$HOME_DIR
Environment=PATH=$UV_DIR:/usr/local/bin:/usr/bin:/bin
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    echo "  ✓ Unit file written to /etc/systemd/system/fte-watcher.service"
}

# ---------------------------------------------------------------------------
# install_orchestrator_unit: generate and install fte-orchestrator.service
# Soft dependency on fte-watcher (After= + Wants=, not Requires=).
# Requires detect_paths() to have run first.
# ---------------------------------------------------------------------------
install_orchestrator_unit() {
    sudo tee /etc/systemd/system/fte-orchestrator.service > /dev/null <<EOF
[Unit]
Description=FTE Orchestrator
After=network.target fte-watcher.service
Wants=network.target fte-watcher.service

[Service]
Type=simple
User=$USER_NAME
Group=$USER_NAME
WorkingDirectory=$PROJECT_DIR
ExecStart=$UV_BIN run fte orchestrate --path $VAULT_PATH --interval 30
Restart=on-failure
RestartSec=5s
# systemd v229+: StartLimit* must be in [Service], silently ignored in [Unit]
StartLimitBurst=5
StartLimitIntervalSec=60s
Environment=HOME=$HOME_DIR
Environment=PATH=$UV_DIR:/usr/local/bin:/usr/bin:/bin
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    echo "  ✓ Unit file written to /etc/systemd/system/fte-orchestrator.service"
}

# ---------------------------------------------------------------------------
# activate_services: reload systemd daemon, enable auto-start, and start both.
# Uses restart (not start) so re-running install.sh is idempotent.
# ---------------------------------------------------------------------------
activate_services() {
    echo ""
    echo "[FTE Deploy] Reloading systemd daemon..."
    sudo systemctl daemon-reload
    echo "  ✓ daemon-reload complete"

    echo ""
    echo "[FTE Deploy] Enabling services (auto-start on boot)..."
    sudo systemctl enable fte-watcher.service
    echo "  ✓ fte-watcher.service enabled"
    sudo systemctl enable fte-orchestrator.service
    echo "  ✓ fte-orchestrator.service enabled"

    echo ""
    echo "[FTE Deploy] Starting services..."
    sudo systemctl restart fte-watcher.service
    echo "  ✓ fte-watcher.service started"
    sudo systemctl restart fte-orchestrator.service
    echo "  ✓ fte-orchestrator.service started"
}

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
main() {
    echo ""
    echo "[FTE Deploy] Checking prerequisites..."
    check_prerequisites
    echo "  ✓ All prerequisites met"

    echo ""
    echo "[FTE Deploy] Detecting paths..."
    detect_paths

    echo ""
    echo "[FTE Deploy] Installing fte-watcher.service..."
    install_watcher_unit

    echo ""
    echo "[FTE Deploy] Installing fte-orchestrator.service..."
    install_orchestrator_unit

    activate_services

    echo ""
    echo "[FTE Deploy] Done. FTE is running 24/7."
    echo ""
    echo "  Check status:  systemctl status fte-watcher fte-orchestrator"
    echo "  View logs:     journalctl -u fte-watcher -f"
    echo "                 journalctl -u fte-orchestrator -f"
    echo "  Uninstall:     sudo bash deploy/uninstall.sh"
    echo ""
}

main
