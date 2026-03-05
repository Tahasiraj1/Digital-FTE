# Quickstart: Gold Tier Setup

**Prerequisites**: Silver tier fully deployed and running.

---

## 1. Install agent-browser

```bash
npm install -g agent-browser

# Verify
agent-browser --version
```

---

## 2. Deploy Odoo via Docker Compose

```bash
# Start Odoo + PostgreSQL
docker compose -f deploy/docker-compose.odoo.yml up -d

# Wait ~60s for Odoo to initialize, then init the database
# (only needed on first run)
docker compose -f deploy/docker-compose.odoo.yml run --rm odoo \
  odoo --db_host db --db_user odoo --db_password odoo \
  -d fte_db --init base --stop-after-init

# Restart after init
docker compose -f deploy/docker-compose.odoo.yml up -d odoo

# Verify Odoo is up
curl -s http://localhost:8069/web/database/list
```

Generate an API key: **Odoo UI → Settings → Technical → API Keys → New**

---

## 3. Configure Odoo MCP

Add to project `.mcp.json`:
```json
{
  "mcpServers": {
    "odoo": {
      "command": "npx",
      "args": ["-y", "mcp-odoo-adv"],
      "env": {
        "ODOO_URL": "http://localhost:8069",
        "ODOO_DB": "fte_db",
        "ODOO_USERNAME": "admin",
        "ODOO_PASSWORD": "${ODOO_API_KEY}"
      }
    }
  }
}
```

Add to `.env`:
```
ODOO_API_KEY=<your-api-key>
ODOO_DB=fte_db
ODOO_URL=http://localhost:8069
RALPH_MAX_ITERATIONS=10
RALPH_CHAIN_CAP=3
```

---

## 4. Configure Ralph Loop Stop Hook

Add to `.claude/settings.json`:
```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash /mnt/d/projects/FTE/scripts/ralph-loop.sh"
          }
        ]
      }
    ]
  }
}
```

---

## 5. Authenticate Social Sessions

```bash
# Facebook — opens browser, log in manually, session auto-saved
agent-browser --session-name facebook open https://facebook.com
# Complete login in the browser window

# Instagram
agent-browser --session-name instagram open https://instagram.com
# Complete login

# Backup sessions
agent-browser state save ~/.config/fte/facebook-session.json --session-name facebook
agent-browser state save ~/.config/fte/instagram-session.json --session-name instagram
```

---

## 6. Test End-to-End

```bash
# Smoke test: Ralph Loop
echo "---
type: invoice_request
ralph_loop: true
---

# Invoice Request

Draft an invoice for Acme Corp, 5 hours AI consulting at \$100/hr.
Client email: test@example.com
" > /mnt/d/AI_Employee_Vault/Needs_Action/TEST_invoice_request_$(date +%Y%m%d).md

# Start Ralph Loop manually (orchestrator will auto-detect on next poll cycle)
# OR invoke directly:
claude --add-dir /mnt/d/AI_Employee_Vault/Needs_Action \
  -p "Process the invoice request task in Needs_Action/. Use the Odoo MCP to create a draft invoice."

# Verify: approval file appears in Pending_Approval/
ls /mnt/d/AI_Employee_Vault/Pending_Approval/ODOO_DRAFT_*.md
```

---

## 7. Verify CEO Briefing Trigger

```bash
# Trigger manually
echo "---
type: ceo_briefing
ralph_loop: true
---

# CEO Briefing Request

Generate the Monday morning CEO briefing for the week of 2026-03-03.
" > /mnt/d/AI_Employee_Vault/Needs_Action/CEO_BRIEFING_$(date +%Y%m%d).md

# After orchestrator processes it, verify:
ls /mnt/d/AI_Employee_Vault/Plans/CEO_Briefing_*.md
```
