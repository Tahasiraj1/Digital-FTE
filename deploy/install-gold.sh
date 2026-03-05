#!/usr/bin/env bash
# Gold Tier Installation Script
# Installs agent-browser, starts Odoo, and documents manual steps.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Gold Tier Installation ==="
echo ""

# 1. Install agent-browser globally
echo "[1/3] Installing agent-browser..."
if command -v agent-browser &>/dev/null; then
    echo "  agent-browser already installed: $(agent-browser --version 2>/dev/null || echo 'unknown version')"
else
    npm install -g agent-browser
    echo "  agent-browser installed."
fi

# 2. Start Odoo + PostgreSQL via Docker Compose
echo ""
echo "[2/3] Starting Odoo + PostgreSQL containers..."
docker compose -f "$SCRIPT_DIR/docker-compose.odoo.yml" up -d db
echo "  Waiting 10s for PostgreSQL to initialize..."
sleep 10

# 3. Initialize Odoo database (first run only)
echo ""
echo "[3/3] Odoo database initialization..."
echo "  Checking if fte_db exists..."
if docker compose -f "$SCRIPT_DIR/docker-compose.odoo.yml" exec -T db \
    psql -U odoo -lqt 2>/dev/null | grep -q fte_db; then
    echo "  fte_db already exists — skipping init."
else
    echo "  Initializing fte_db (this may take 60-90 seconds)..."
    docker compose -f "$SCRIPT_DIR/docker-compose.odoo.yml" run --rm odoo \
        odoo --db_host db --db_user odoo --db_password odoo \
        -d fte_db --init base --stop-after-init
    echo "  fte_db initialized."
fi

# Start Odoo service
docker compose -f "$SCRIPT_DIR/docker-compose.odoo.yml" up -d odoo
echo ""
echo "  Odoo is starting at http://localhost:8069"

echo ""
echo "=== Manual Steps Required ==="
echo ""
echo "1. Generate Odoo API Key:"
echo "   - Open http://localhost:8069/web"
echo "   - Login as admin/admin"
echo "   - Settings → Technical → API Keys → New"
echo "   - Copy the key and add to .env: ODOO_API_KEY=<your-key>"
echo ""
echo "2. Authenticate social sessions (Facebook & Instagram):"
echo "   agent-browser --session-name facebook open https://facebook.com"
echo "   agent-browser --session-name instagram open https://instagram.com"
echo "   # Complete login in the browser windows"
echo ""
echo "3. Backup sessions after login:"
echo "   mkdir -p ~/.config/fte"
echo "   agent-browser state save ~/.config/fte/facebook-session.json --session-name facebook"
echo "   agent-browser state save ~/.config/fte/instagram-session.json --session-name instagram"
echo ""
echo "=== Gold Tier Installation Complete ==="
