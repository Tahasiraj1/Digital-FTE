#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# FTE Silver Deploy — install-silver.sh
# Installs fte-gmail-watcher, fte-whatsapp-watcher, and fte-action-executor
# as systemd system services.
#
# Prerequisites:
#   - Bronze tier installed and running (install.sh already run)
#   - python scripts/oauth_setup.py completed (Gmail + Calendar tokens exist)
#   - WhatsApp QR scan completed (run: cd src/fte/whatsapp && node watcher.js)
#   - LinkedIn OAuth completed (run: fte linkedin-auth) if using LinkedIn
#   - MCP servers registered in ~/.claude/settings.json
#
# Usage: sudo bash deploy/install-silver.sh [--vault /path/to/vault]
# =============================================================================

REAL_USER="${SUDO_USER:-$(whoami)}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
VAULT_ARG=""
SKIP_WHATSAPP=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --vault)
            VAULT_ARG="$2"
            shift 2
            ;;
        --skip-whatsapp)
            SKIP_WHATSAPP=true
            shift
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: sudo bash deploy/install-silver.sh [--vault /path/to/vault] [--skip-whatsapp]" >&2
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# find_uv: same logic as install.sh
# ---------------------------------------------------------------------------
find_uv() {
    if command -v uv &>/dev/null; then command -v uv; return 0; fi
    if [[ -x "$REAL_HOME/.local/bin/uv" ]]; then echo "$REAL_HOME/.local/bin/uv"; return 0; fi
    local user_bin="${UV_INSTALL_DIR:-${XDG_BIN_HOME:-$REAL_HOME/.local/bin}}/uv"
    if [[ -x "$user_bin" ]]; then echo "$user_bin"; return 0; fi
    if [[ -x "$REAL_HOME/.cargo/bin/uv" ]]; then echo "$REAL_HOME/.cargo/bin/uv"; return 0; fi
    for p in /usr/local/bin/uv /usr/bin/uv; do
        if [[ -x "$p" ]]; then echo "$p"; return 0; fi
    done
    return 1
}

# ---------------------------------------------------------------------------
# find_node: locate node binary
# ---------------------------------------------------------------------------
find_node() {
    if command -v node &>/dev/null; then command -v node; return 0; fi
    for p in /usr/local/bin/node /usr/bin/node "$REAL_HOME/.nvm/versions/node/$(ls "$REAL_HOME/.nvm/versions/node/" 2>/dev/null | tail -1)/bin/node"; do
        if [[ -x "$p" ]]; then echo "$p"; return 0; fi
    done
    return 1
}

# ---------------------------------------------------------------------------
# detect_paths
# ---------------------------------------------------------------------------
detect_paths() {
    USER_NAME="$REAL_USER"
    HOME_DIR="$REAL_HOME"

    UV_BIN=$(find_uv) || { echo "ERROR: uv not found. Install uv first." >&2; exit 1; }
    UV_DIR=$(dirname "$UV_BIN")

    NODE_BIN=$(find_node) || { echo "ERROR: node not found. Install Node.js 20+ first." >&2; exit 1; }
    NODE_DIR=$(dirname "$NODE_BIN")

    PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
    WHATSAPP_DIR="$PROJECT_DIR/src/fte/whatsapp"

    if [[ -n "$VAULT_ARG" ]]; then
        VAULT_PATH="$VAULT_ARG"
    else
        VAULT_PATH="$HOME_DIR/AI_Employee_Vault"
    fi

    CONFIG_DIR="$HOME_DIR/.config/fte"
    mkdir -p "$CONFIG_DIR"
    chmod 700 "$CONFIG_DIR"

    WHATSAPP_SESSION_DIR="/var/lib/fte/whatsapp-session"
    mkdir -p "$WHATSAPP_SESSION_DIR"
    chown "$USER_NAME:$USER_NAME" "$WHATSAPP_SESSION_DIR"
    chmod 750 "$WHATSAPP_SESSION_DIR"

    echo "  User:          $USER_NAME"
    echo "  Home:          $HOME_DIR"
    echo "  uv:            $UV_BIN"
    echo "  node:          $NODE_BIN"
    echo "  Project:       $PROJECT_DIR"
    echo "  Vault:         $VAULT_PATH"
    echo "  Config:        $CONFIG_DIR"
    echo "  WA session:    $WHATSAPP_SESSION_DIR"
}

# ---------------------------------------------------------------------------
# install_npm_deps: install whatsapp watcher node_modules
# ---------------------------------------------------------------------------
install_npm_deps() {
    echo ""
    echo "Installing WhatsApp watcher npm dependencies..."
    cd "$WHATSAPP_DIR"
    NPM_BIN="$(dirname "$NODE_BIN")/npm"
    sudo -u "$USER_NAME" "$NPM_BIN" install --omit=dev
    echo "  ✓ npm dependencies installed"
}

# ---------------------------------------------------------------------------
# install_gmail_watcher_unit
# ---------------------------------------------------------------------------
install_gmail_watcher_unit() {
    tee /etc/systemd/system/fte-gmail-watcher.service > /dev/null <<EOF
[Unit]
Description=FTE Gmail Watcher
After=network.target
Wants=network.target
StartLimitBurst=5
StartLimitIntervalSec=60s

[Service]
Type=simple
User=$USER_NAME
Group=$USER_NAME
WorkingDirectory=$PROJECT_DIR
ExecStart=$UV_BIN run fte gmail-watcher --path $VAULT_PATH
Restart=always
RestartSec=5s
Environment=HOME=$HOME_DIR
Environment=PATH=$UV_DIR:/usr/local/bin:/usr/bin:/bin
Environment=VAULT_PATH=$VAULT_PATH
Environment=DEV_MODE=false
MemoryMax=256M
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    echo "  ✓ fte-gmail-watcher.service installed"
}

# ---------------------------------------------------------------------------
# install_whatsapp_watcher_unit
# ---------------------------------------------------------------------------
install_whatsapp_watcher_unit() {
    tee /etc/systemd/system/fte-whatsapp-watcher.service > /dev/null <<EOF
[Unit]
Description=FTE WhatsApp Watcher
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER_NAME
Group=$USER_NAME
WorkingDirectory=$WHATSAPP_DIR
ExecStart=$NODE_BIN $WHATSAPP_DIR/watcher.js
Restart=always
RestartSec=10s
StartLimitBurst=3
StartLimitIntervalSec=120s
RuntimeMaxSec=86400
Environment=HOME=$HOME_DIR
Environment=PATH=$NODE_DIR:/usr/local/bin:/usr/bin:/bin
Environment=VAULT_PATH=$VAULT_PATH
Environment=WHATSAPP_SESSION_PATH=$WHATSAPP_SESSION_DIR
Environment=WHATSAPP_IPC_PORT=8766
Environment=DEV_MODE=false
MemoryMax=512M
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    echo "  ✓ fte-whatsapp-watcher.service installed"
}

# ---------------------------------------------------------------------------
# install_action_executor_unit
# ---------------------------------------------------------------------------
install_action_executor_unit() {
    tee /etc/systemd/system/fte-action-executor.service > /dev/null <<EOF
[Unit]
Description=FTE Action Executor
After=network.target fte-orchestrator.service
Wants=network.target
StartLimitBurst=5
StartLimitIntervalSec=60s

[Service]
Type=simple
User=$USER_NAME
Group=$USER_NAME
WorkingDirectory=$PROJECT_DIR
ExecStart=$UV_BIN run fte execute --path $VAULT_PATH
Restart=always
RestartSec=5s
Environment=HOME=$HOME_DIR
Environment=PATH=$UV_DIR:/usr/local/bin:/usr/bin:/bin
Environment=VAULT_PATH=$VAULT_PATH
Environment=DEV_MODE=false
Environment=WHATSAPP_IPC_PORT=8766
MemoryMax=256M
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    echo "  ✓ fte-action-executor.service installed"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   FTE Silver Tier — Install              ║"
echo "╚══════════════════════════════════════════╝"
echo ""

echo "Detecting paths..."
detect_paths

if [[ "$SKIP_WHATSAPP" == "true" ]]; then
    echo ""
    echo "Skipping WhatsApp watcher (--skip-whatsapp specified)"
else
    install_npm_deps
    install_whatsapp_watcher_unit
fi

install_gmail_watcher_unit
install_action_executor_unit

echo ""
echo "Reloading systemd..."
systemctl daemon-reload

echo ""
echo "Enabling services..."
if [[ "$SKIP_WHATSAPP" == "true" ]]; then
    systemctl enable fte-gmail-watcher fte-action-executor
else
    systemctl enable fte-gmail-watcher fte-whatsapp-watcher fte-action-executor
fi
echo "  ✓ Services enabled (will start on next boot)"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Silver install complete!               ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Post-install checklist:"
echo "  1. Run OAuth setup (if not done):  uv run python scripts/oauth_setup.py"
echo "  2. Register MCP servers:           See specs/003-silver-functional-assistant/quickstart.md"
echo "  3. WhatsApp QR scan (if not done): cd src/fte/whatsapp && node watcher.js"
echo "  4. LinkedIn auth (if needed):      uv run fte linkedin-auth"
echo "  5. Start services:                 sudo systemctl start fte-gmail-watcher fte-action-executor"
echo "  6. Smoke test (DEV_MODE):          sudo systemctl set-environment DEV_MODE=true && sudo systemctl restart fte-action-executor"
echo ""
echo "Check logs with: journalctl -u fte-gmail-watcher -f"
