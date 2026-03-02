#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# FTE Silver Deploy — uninstall-silver.sh
# Stops and removes the 3 Silver systemd services.
# Data directories and token files are preserved.
#
# Usage: sudo bash deploy/uninstall-silver.sh
# =============================================================================

SERVICES="fte-gmail-watcher fte-whatsapp-watcher fte-action-executor"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   FTE Silver Tier — Uninstall           ║"
echo "╚══════════════════════════════════════════╝"
echo ""

for svc in $SERVICES; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        systemctl stop "$svc"
        echo "  ✓ Stopped $svc"
    fi
    if systemctl is-enabled --quiet "$svc" 2>/dev/null; then
        systemctl disable "$svc"
        echo "  ✓ Disabled $svc"
    fi
    if [[ -f "/etc/systemd/system/$svc.service" ]]; then
        rm -f "/etc/systemd/system/$svc.service"
        echo "  ✓ Removed /etc/systemd/system/$svc.service"
    fi
done

systemctl daemon-reload
echo ""
echo "Silver services removed. Data preserved:"
echo "  - Vault files:       ~/AI_Employee_Vault/"
echo "  - OAuth tokens:      ~/.config/fte/"
echo "  - WhatsApp session:  /var/lib/fte/whatsapp-session/"
echo ""
echo "To reinstall: sudo bash deploy/install-silver.sh"
