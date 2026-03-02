# Silver Tier Quickstart Guide

**Feature**: 003-silver-functional-assistant
**Prerequisites**: Bronze tier fully deployed and working

---

## One-Time Setup (Do Before Deploying)

### Step 1: Google Cloud Console (Gmail + Calendar)

```bash
# 1. Go to console.cloud.google.com → Create Project
# 2. Enable APIs:
#    - Gmail API
#    - Google Calendar API
# 3. OAuth consent screen: External, add your Gmail as test user
# 4. Create OAuth2 credential: type = Desktop app
# 5. Download client_secrets.json

mkdir -p ~/.config/fte
cp ~/Downloads/client_secrets.json ~/.config/fte/client_secrets.json
chmod 600 ~/.config/fte/client_secrets.json
```

### Step 2: Authorize Gmail + Calendar (one-time browser flow)

Both Gmail and Calendar use the same Google Cloud project and the same token file.

```bash
cd /mnt/d/projects/FTE
uv run python scripts/oauth_setup.py
# Browser opens → sign in → grant access (Gmail read/send + Calendar)
# Token saved to ~/.config/fte/gmail_token.json (chmod 600 applied automatically)
```

The script is idempotent — safe to re-run. If the token is already valid it exits immediately.

### Step 2a: Register Gmail MCP Server in Claude Code

Edit `~/.claude/settings.json` and add the `mcpServers` section:

```json
{
  "mcpServers": {
    "gmail": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "/mnt/d/projects/FTE", "fte-gmail-mcp"],
      "env": {
        "GMAIL_TOKEN_PATH": "/home/taha/.config/fte/gmail_token.json"
      }
    },
    "calendar": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "/mnt/d/projects/FTE", "fte-calendar-mcp"],
      "env": {
        "CALENDAR_TOKEN_PATH": "/home/taha/.config/fte/gmail_token.json"
      }
    }
  }
}
```

**MCP tool names** (as seen by Claude Code):
- `mcp__gmail__list_emails` — search inbox
- `mcp__gmail__read_email` — read full email content
- `mcp__gmail__send_reply` — send a reply (requires `confirm=true`)
- `mcp__calendar__create_event` — create a calendar event
- `mcp__calendar__list_events` — list events in a date range

Restart Claude Code after editing settings.json.

### Step 2b: Verify MCP servers load

```bash
# In Claude Code, run:
# /mcp
# Should list: gmail (3 tools), calendar (2 tools)
```

### Step 3: LinkedIn Developer App + OAuth2

```bash
# 1. Go to developer.linkedin.com → Create App
# 2. Products tab → Request "Share on LinkedIn" (instant approval)
# 3. Auth tab → Add redirect URL: http://localhost:8765/callback
# 4. Copy Client ID and Client Secret

# Add to .env (gitignored)
echo "LINKEDIN_CLIENT_ID=your-client-id" >> .env
echo "LINKEDIN_CLIENT_SECRET=your-secret" >> .env

# Run one-time auth flow
uv run python -m fte.linkedin_auth
# Browser opens → sign in → grant access → tokens saved to ~/.config/fte/linkedin_token.json
```

### Step 4: Node.js + WhatsApp dependencies

```bash
# Install Node.js 20+ if not installed
node --version  # should be v20+

# Install WhatsApp watcher dependencies
cd /mnt/d/projects/FTE/src/fte/whatsapp
npm install
cd /mnt/d/projects/FTE
```

### Step 5: WhatsApp — First-Time QR Scan

```bash
# Create session directory
sudo mkdir -p /var/lib/fte/whatsapp-session
sudo chown $USER:$USER /var/lib/fte/whatsapp-session

# Run the watcher interactively for the first time
# It will print a QR code as ASCII art in the terminal
node src/fte/whatsapp/watcher.js
# Scan the QR code with WhatsApp on your phone:
#   WhatsApp → Settings → Linked Devices → Link a Device
# Wait for "Client is ready" message
# Press Ctrl+C — session is saved to /var/lib/fte/whatsapp-session/
```

### Step 6: Install Agent Skills

```bash
# Skills are auto-discovered from .claude/skills/ at Claude Code startup
# They are created during implementation — no install command needed
ls .claude/skills/
# Should show: gmail-watcher/ whatsapp-watcher/ gmail-reply/
#              whatsapp-reply/ calendar-event/ linkedin-post/ hitl-approval/
```

### Step 7: Smoke Test in DEV_MODE

```bash
# Test executor without real outbound calls
DEV_MODE=true fte execute --path /mnt/d/AI_Employee_Vault --dry-run

# Test Gmail MCP
DEV_MODE=true fte gmail-watcher --path /mnt/d/AI_Employee_Vault

# Check logs
cat /mnt/d/AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json | python3 -m json.tool
```

---

## Deployment

```bash
# Deploy all Silver services (adds fte-gmail-watcher, fte-whatsapp-watcher, fte-action-executor)
sudo bash deploy/install-silver.sh --vault /mnt/d/AI_Employee_Vault

# Verify all 5 services running
systemctl status fte-watcher fte-orchestrator fte-gmail-watcher fte-whatsapp-watcher fte-action-executor
```

---

## Testing Silver Tier End-to-End

### Test 1: Gmail → Reply

```bash
# Send a test email to your Gmail from another account
# Subject: "Test FTE Silver — Invoice Request"
# Body: "Hi, can you send me the invoice for February?"

# Check Inbox/ for task file (within 3 minutes)
ls /mnt/d/AI_Employee_Vault/Inbox/EMAIL_*.md

# Check Pending_Approval/ for draft reply (after orchestrator runs)
ls /mnt/d/AI_Employee_Vault/Pending_Approval/EMAIL_REPLY_*.md

# Approve: move file to Approved/
mv /mnt/d/AI_Employee_Vault/Pending_Approval/EMAIL_REPLY_*.md \
   /mnt/d/AI_Employee_Vault/Approved/

# Check email was sent (Gmail Sent folder) within 30s
# In DEV_MODE, check Logs/ instead of actual email
```

### Test 2: WhatsApp → Reply

```bash
# Send a WhatsApp message to your phone containing: "urgent invoice payment"

# Check Inbox/ within 60 seconds
ls /mnt/d/AI_Employee_Vault/Inbox/WHATSAPP_*.md

# After orchestrator: approve the WhatsApp reply draft
# Move from Pending_Approval/ to Approved/

# Verify reply sent in WhatsApp conversation (or logged in DEV_MODE)
```

### Test 3: LinkedIn Post

```bash
# Drop a task file into Inbox/
cat > /mnt/d/AI_Employee_Vault/Inbox/TASK_linkedin-q1.md << 'EOF'
---
type: task
---
Write a professional LinkedIn post about our Q1 2026 results to generate sales interest.
EOF

# After orchestrator: check Pending_Approval/LINKEDIN_*.md
# Read the draft, approve if it looks good:
mv /mnt/d/AI_Employee_Vault/Pending_Approval/LINKEDIN_*.md \
   /mnt/d/AI_Employee_Vault/Approved/

# Verify post appears on your LinkedIn profile within 30s (or logged in DEV_MODE)
```

### Test 4: Calendar Event

```bash
# Drop a task file with scheduling intent into Inbox/
cat > /mnt/d/AI_Employee_Vault/Inbox/TASK_meeting.md << 'EOF'
---
type: task
---
Can we schedule a call with John (john@example.com) on Tuesday at 3pm?
EOF

# After orchestrator: check Pending_Approval/CALENDAR_*.md
# Approve to create the event (or log in DEV_MODE)
```

### Test 5: Crash Recovery

```bash
# Kill the Gmail watcher
sudo systemctl kill fte-gmail-watcher

# Verify it restarts within 15 seconds
systemctl status fte-gmail-watcher
# Should show: active (running), restarts: 1
```

### Test 6: DEV_MODE — Zero Real Outbound Calls

```bash
# Run executor with DEV_MODE=true, move a file to Approved/
DEV_MODE=true fte execute --path /mnt/d/AI_Employee_Vault

# Verify: check Logs/ for action logged but NO real email/WhatsApp/LinkedIn calls
# Check Done/ — file should be moved there with status: completed (dev_mode)
```

---

## Service Logs

```bash
# Gmail watcher logs
journalctl -u fte-gmail-watcher -f

# WhatsApp watcher logs
journalctl -u fte-whatsapp-watcher -f

# Action executor logs (see what actions were executed)
journalctl -u fte-action-executor -f

# Vault action log (JSON)
cat /mnt/d/AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json | python3 -m json.tool
```

---

## Uninstall Silver

```bash
sudo bash deploy/uninstall-silver.sh
# Removes: fte-gmail-watcher, fte-whatsapp-watcher, fte-action-executor
# Keeps: fte-watcher, fte-orchestrator (Bronze services)
# Preserves: ~/.config/fte/ token files, /var/lib/fte/whatsapp-session/
```
