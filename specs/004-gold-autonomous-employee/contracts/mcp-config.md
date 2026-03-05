# MCP Server Configurations — Gold Tier

## Odoo MCP Server

**Package**: `mcp-odoo-adv` by AlanOgic
**Install**: Zero local install — runs via `npx -y mcp-odoo-adv`

### `.mcp.json` entry (project-level)

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

**Env vars** (add to `.env`):
```
ODOO_API_KEY=<generate via Odoo Settings → Technical → API Keys>
ODOO_DB=fte_db
ODOO_URL=http://localhost:8069
```

### Claude Code tool calls (reasoning phase)

Claude uses these during Ralph Loop iterations:

```
# Create draft invoice
odoo_call_method(model="account.move", method="create", args=[{
  "move_type": "out_invoice",
  "partner_id": <partner_id>,
  "invoice_date": "YYYY-MM-DD",
  "invoice_line_ids": [[0, 0, {
    "name": "Description",
    "quantity": 1.0,
    "price_unit": 500.00
  }]]
}])

# Query outstanding invoices
odoo_call_method(model="account.move", method="search_read", args=[[
  ["move_type", "=", "out_invoice"],
  ["state", "=", "posted"],
  ["payment_state", "!=", "paid"]
]], kwargs={"fields": ["name", "partner_id", "amount_residual", "invoice_date_due"]})

# Monthly revenue
odoo_call_method(model="account.move", method="read_group", args=[[
  ["move_type", "=", "out_invoice"],
  ["state", "=", "posted"]
], ["amount_total:sum"], ["invoice_date:month"]])
```

---

## Existing MCP Servers (Silver — unchanged)

| Server | Package | Domain |
|--------|---------|--------|
| Gmail | `src/mcp_servers/gmail/` | Email read/search |
| Calendar | `src/mcp_servers/calendar/` | Calendar event creation |

---

## agent-browser (not an MCP server)

agent-browser is invoked as a **shell subprocess** from executor action handlers — not as an MCP server. It is also available as a native Claude Code plugin (agent-browser registers itself when installed globally).

**Claude Code native integration**: After `npm install -g agent-browser`, the tool registers as a native Claude Code capability. Claude can call browser actions directly during Ralph Loop reasoning without subprocess overhead.

**Session names used by FTE**:
- `facebook` → `~/.agent-browser/sessions/facebook/`
- `instagram` → `~/.agent-browser/sessions/instagram/`

**Backup locations** (excluded from git and cloud sync):
- `~/.config/fte/facebook-session.json`
- `~/.config/fte/instagram-session.json`
