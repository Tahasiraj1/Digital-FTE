---
id: "001"
title: Odoo MCP Server Research for Claude Code
stage: general
date: 2026-03-03
surface: agent
model: claude-sonnet-4-6
feature: none
branch: 003-silver-functional-assistant
user: taha
command: Research Odoo MCP server options for integrating with a local Odoo Community 19+ Docker instance
labels: ["odoo","mcp","json-rpc","docker","research"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - (no files created or modified)
tests:
  - (no tests run)
---

## Prompt

Research Odoo MCP server options for integrating with a local Odoo Community 19+ Docker instance from Claude Code.

Specifically research:
1. "mcp-odoo-adv" by AlanOgic on GitHub — what it does, installation, JSON-RPC config
2. Any other Odoo MCP servers available (search GitHub for "odoo mcp server", "odoo json-rpc mcp")
3. Odoo 19 Community JSON-RPC API — the exact endpoints for:
   - Creating a draft invoice (account.move model)
   - Confirming an invoice (action_post)
   - Querying invoices (amount_residual, invoice_date_due, partner_id)
   - Getting monthly revenue totals
4. Docker Compose setup for Odoo 19 Community + PostgreSQL — the minimal compose file
5. Odoo authentication — database name, username, password for JSON-RPC

Return:
- Which MCP server is best (name, GitHub URL, install command)
- MCP server config schema for Claude Code
- Minimal docker-compose.yml for Odoo 19 + PostgreSQL
- Key JSON-RPC endpoints/methods we'll call
- Any known issues with Odoo 19 Community

## Response snapshot

**Best MCP Server:** `mcp-odoo-adv` by AlanOgic — `https://github.com/AlanOgic/mcp-odoo-adv`

Install: `npx -y mcp-odoo-adv`

**Claude Code MCP config:**
```json
{
  "mcpServers": {
    "odoo": {
      "command": "npx",
      "args": ["-y", "mcp-odoo-adv"],
      "env": {
        "ODOO_URL": "http://localhost:8069",
        "ODOO_DB": "mydb",
        "ODOO_USERNAME": "admin",
        "ODOO_PASSWORD": "admin"
      }
    }
  }
}
```

**Key JSON-RPC endpoints:**
- Auth: `POST /web/dataset/call_kw` (service: common, method: authenticate)
- Create invoice: `execute_kw` on `account.move` with `create` and `move_type: out_invoice`
- Confirm invoice: `execute_kw` on `account.move` with `action_post` passing `[[invoice_id]]`
- Query invoices: `search_read` on `account.move` filtering `move_type`, `state`, `payment_state`
- Monthly totals: `read_group` on `account.move` grouped by `invoice_date:month`

**Docker Compose:** postgres:15 + odoo:17 (odoo:19 image not yet published as of August 2025 training cutoff)

**Known issues:**
- `odoo:19` Docker image not yet on Docker Hub as of August 2025
- Python 3.12 required for Odoo 19 custom builds
- `action_post` returns `True` (not action dict) in Odoo 16+ via JSON-RPC
- WebSearch/WebFetch blocked in session — research from training data only; verify live before implementing

## Outcome

- Impact: Research compiled for Odoo MCP integration; ready to implement MCP config and Docker setup
- Tests: None — research task
- Files: PHR only (no source files modified)
- Next prompts: Verify mcp-odoo-adv README live; confirm odoo:19 Docker image availability; implement .mcp.json config; set up docker-compose.yml
- Reflection: Both web tools were blocked; all research drawn from training knowledge (cutoff Aug 2025). Live verification required before implementation.

## Evaluation notes (flywheel)

- Failure modes observed: WebSearch and WebFetch permissions denied; could not verify live GitHub/Docker Hub state
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Enable WebFetch permission and re-run to verify mcp-odoo-adv README env var names exactly
