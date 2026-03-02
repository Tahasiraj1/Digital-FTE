#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# FTE Uninstall — uninstall.sh
# Stops, disables, and removes fte-watcher and fte-orchestrator systemd services.
# Idempotent: safe to run even when services are not installed.
#
# Usage: sudo bash deploy/uninstall.sh
# =============================================================================

# ---------------------------------------------------------------------------
# check_systemd: verify systemd is available before proceeding.
# ---------------------------------------------------------------------------
check_systemd() {
    if ! systemctl --version &>/dev/null; then
        echo "ERROR: systemd is not available." >&2
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
main() {
    check_systemd

    echo ""
    echo "[FTE Uninstall] Stopping services..."
    sudo systemctl stop fte-watcher.service 2>/dev/null || true
    echo "  ✓ fte-watcher.service stopped (or was not running)"
    sudo systemctl stop fte-orchestrator.service 2>/dev/null || true
    echo "  ✓ fte-orchestrator.service stopped (or was not running)"

    echo ""
    echo "[FTE Uninstall] Disabling services..."
    sudo systemctl disable fte-watcher.service 2>/dev/null || true
    echo "  ✓ fte-watcher.service disabled (or was not enabled)"
    sudo systemctl disable fte-orchestrator.service 2>/dev/null || true
    echo "  ✓ fte-orchestrator.service disabled (or was not enabled)"

    echo ""
    echo "[FTE Uninstall] Removing unit files..."
    sudo rm -f /etc/systemd/system/fte-watcher.service
    echo "  ✓ /etc/systemd/system/fte-watcher.service removed (or did not exist)"
    sudo rm -f /etc/systemd/system/fte-orchestrator.service
    echo "  ✓ /etc/systemd/system/fte-orchestrator.service removed (or did not exist)"

    echo ""
    echo "[FTE Uninstall] Reloading systemd daemon..."
    sudo systemctl daemon-reload
    echo "  ✓ daemon-reload complete"

    echo ""
    echo "[FTE Uninstall] Done. FTE services removed."
    echo ""
}

main
