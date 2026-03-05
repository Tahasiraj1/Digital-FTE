/**
 * FTE WhatsApp Watcher — T033-T039
 *
 * Watches WhatsApp for keyword-matching messages, writes task files to
 * Vault/Inbox/, and exposes an HTTP IPC bridge on localhost:8766 for
 * the Python executor to send replies.
 *
 * Usage:
 *   VAULT_PATH=/mnt/d/AI_Employee_Vault node src/fte/whatsapp/watcher.js
 *
 * First run: prints QR code → scan with WhatsApp → session saved.
 * Subsequent runs: session restored automatically.
 */

import { Client, LocalAuth } from 'whatsapp-web.js';
import qrcode from 'qrcode-terminal';
import fs from 'fs-extra';
import path from 'path';
import http from 'http';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ---------------------------------------------------------------------------
// Configuration — T034
// ---------------------------------------------------------------------------

const VAULT_PATH = process.env.VAULT_PATH || path.join(process.env.HOME, 'AI_Employee_Vault');
const SESSION_DATA_PATH = process.env.WHATSAPP_SESSION_PATH || '/var/lib/fte/whatsapp-session';
const IPC_PORT = parseInt(process.env.WHATSAPP_IPC_PORT || '8766', 10);
const ALLOW_GROUPS = process.env.WHATSAPP_ALLOW_GROUPS === 'true';

const DEFAULT_KEYWORDS = 'urgent,asap,invoice,payment,help,contract';
const KEYWORD_LIST = (process.env.WHATSAPP_KEYWORDS || DEFAULT_KEYWORDS)
  .split(',')
  .map(k => k.trim().toLowerCase())
  .filter(Boolean);

// Pre-compile keyword regex — T034
const KEYWORD_PATTERN = new RegExp(
  `\\b(${KEYWORD_LIST.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})\\b`,
  'i'
);

const STATE_FILE = path.join(SESSION_DATA_PATH, 'watcher-state.json');
const STATE_MAX_IDS = 2000;

// ---------------------------------------------------------------------------
// WatcherState — T036
// ---------------------------------------------------------------------------

let processedIds = [];

async function loadState() {
  try {
    const data = await fs.readJson(STATE_FILE);
    processedIds = Array.isArray(data.processed_ids) ? data.processed_ids : [];
  } catch {
    processedIds = [];
  }
}

async function saveState() {
  // Enforce FIFO cap
  if (processedIds.length > STATE_MAX_IDS) {
    processedIds = processedIds.slice(-STATE_MAX_IDS);
  }
  const data = {
    processed_ids: processedIds,
    processed_ids_max: STATE_MAX_IDS,
    schema_version: '1',
    updated_at: new Date().toISOString(),
  };
  // Atomic write via temp + rename — T036
  const tmpFile = STATE_FILE + '.tmp';
  await fs.ensureDir(path.dirname(STATE_FILE));
  await fs.outputJson(tmpFile, data, { spaces: 2 });
  await fs.move(tmpFile, STATE_FILE, { overwrite: true });
}

function isProcessed(messageId) {
  return processedIds.includes(messageId);
}

function markProcessed(messageId) {
  if (!processedIds.includes(messageId)) {
    processedIds.push(messageId);
  }
}

// ---------------------------------------------------------------------------
// Vault file writer — T035
// ---------------------------------------------------------------------------

function sanitizeId(id) {
  return id.replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 64);
}

async function writeInboxFile(msg, keywordsMatched) {
  const sanitizedId = sanitizeId(msg.id.id || msg.id._serialized || String(Date.now()));
  const filename = `WHATSAPP_${sanitizedId}.md`;
  const dest = path.join(VAULT_PATH, 'Inbox', filename);

  if (await fs.pathExists(dest)) {
    return null; // Already written
  }

  const fromJid = msg.from || '';
  const fromDisplay = msg._data?.notifyName || msg.author || fromJid.split('@')[0];
  const body = msg.body || '';
  const timestampUnix = msg.timestamp || Math.floor(Date.now() / 1000);
  const timestampIso = new Date(timestampUnix * 1000).toISOString();
  const chatType = fromJid.includes('@g.us') ? 'group' : 'private';
  const isUrgent = keywordsMatched.some(k => ['urgent', 'asap'].includes(k.toLowerCase()));
  const priority = isUrgent ? 'high' : 'normal';

  const bodyPreview = body.slice(0, 100).replace(/\n/g, ' ');

  const content = `---
type: whatsapp_message
source: whatsapp
status: unprocessed
message_id: "${sanitizedId}"
from_jid: "${fromJid}"
from_display: "${fromDisplay}"
chat_type: ${chatType}
group_name: null
timestamp_unix: ${timestampUnix}
timestamp_iso: "${timestampIso}"
body_preview: "${bodyPreview}"
keywords_matched:
${keywordsMatched.map(k => `  - ${k}`).join('\n')}
has_media: ${msg.hasMedia || false}
priority: ${priority}
requires_action: true
---

# WhatsApp Message — Requires Action

**From**: ${fromDisplay} (\`${fromJid}\`)
**Time**: ${timestampIso}
**Keywords**: ${keywordsMatched.join(', ')}

## Message

${body}

## Required Action

Review and respond. For outbound reply, the AI will create an approval
file in \`Vault/Pending_Approval/\`.
`;

  await fs.ensureDir(path.join(VAULT_PATH, 'Inbox'));
  await fs.writeFile(dest, content, 'utf-8');
  console.log(`[whatsapp-watcher] Wrote ${filename}`);
  return dest;
}

// ---------------------------------------------------------------------------
// WhatsApp client — T033
// ---------------------------------------------------------------------------

const client = new Client({
  authStrategy: new LocalAuth({
    dataPath: SESSION_DATA_PATH,
  }),
  puppeteer: {
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
    ],
  },
});

client.on('qr', (qr) => {
  console.log('\n[whatsapp-watcher] Scan this QR code with WhatsApp:');
  qrcode.generate(qr, { small: true });
  console.log('\nWhatsApp → Settings → Linked Devices → Link a Device\n');
});

client.on('ready', () => {
  console.log('[whatsapp-watcher] Client is ready!');
});

client.on('authenticated', () => {
  console.log('[whatsapp-watcher] Authenticated — session saved.');
});

// Message handler — T034, T035
client.on('message', async (msg) => {
  try {
    const body = msg.body || '';
    const fromJid = msg.from || '';

    // Filter group messages unless explicitly allowed — T034
    if (!ALLOW_GROUPS && fromJid.includes('@g.us')) {
      return;
    }

    // Keyword filter — T034
    const matches = body.match(new RegExp(
      KEYWORD_PATTERN.source,
      KEYWORD_PATTERN.flags + 'g'
    ));
    if (!matches || matches.length === 0) {
      return;
    }
    const keywordsMatched = [...new Set(matches.map(m => m.toLowerCase()))];

    // Dedup check — T036
    const msgId = msg.id._serialized || msg.id.id || String(msg.timestamp);
    if (isProcessed(msgId)) {
      return;
    }

    // Write inbox file — T035
    await writeInboxFile(msg, keywordsMatched);
    markProcessed(msgId);
    await saveState();

  } catch (err) {
    console.error('[whatsapp-watcher] Message handler error:', err.message);
  }
});

// Disconnection handling — T037
client.on('disconnected', async (reason) => {
  console.warn(`[whatsapp-watcher] Disconnected: ${reason}`);

  if (reason === 'UNPAIRED' || reason === 'UNPAIRED_IDLE') {
    // Session expired — write alert to vault
    try {
      const alertFile = path.join(
        VAULT_PATH,
        'Needs_Action',
        `SYSTEM_whatsapp-session-expired_${Date.now()}.md`
      );
      await fs.ensureDir(path.join(VAULT_PATH, 'Needs_Action'));
      await fs.writeFile(alertFile, `---
type: system_alert
source: fte-whatsapp-watcher
status: unprocessed
alert: whatsapp_session_expired
created_at: "${new Date().toISOString()}"
---

# WhatsApp Session Expired

The WhatsApp session has been unpaired. Run the watcher interactively to re-scan the QR code.

    node src/fte/whatsapp/watcher.js
`, 'utf-8');
      console.log('[whatsapp-watcher] Session expired alert written to Needs_Action/');
    } catch (alertErr) {
      console.error('[whatsapp-watcher] Failed to write alert:', alertErr.message);
    }
  } else if (reason === 'CONFLICT' || reason === 'UNLAUNCHED') {
    // Re-initialise on conflict
    console.log('[whatsapp-watcher] Reinitialising...');
    try {
      await client.initialize();
    } catch (initErr) {
      console.error('[whatsapp-watcher] Reinitialise failed:', initErr.message);
    }
  }
});

// ---------------------------------------------------------------------------
// IPC HTTP bridge on localhost:8766 — T039
// ---------------------------------------------------------------------------

const ipcServer = http.createServer(async (req, res) => {
  if (req.method !== 'POST' || req.url !== '/send') {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Not found' }));
    return;
  }

  let body = '';
  req.on('data', chunk => { body += chunk; });
  req.on('end', async () => {
    try {
      const { to_jid, message } = JSON.parse(body);

      if (!to_jid || !message) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'to_jid and message are required' }));
        return;
      }

      await client.sendMessage(to_jid, message);
      console.log(`[whatsapp-ipc] Sent message to ${to_jid}`);

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'sent' }));

    } catch (err) {
      console.error('[whatsapp-ipc] Send error:', err.message);
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: err.message }));
    }
  });
});

// Bind to localhost only (not 0.0.0.0) for security
ipcServer.listen(IPC_PORT, '127.0.0.1', () => {
  console.log(`[whatsapp-watcher] IPC bridge listening on http://127.0.0.1:${IPC_PORT}`);
});

// ---------------------------------------------------------------------------
// Startup
// ---------------------------------------------------------------------------

async function main() {
  await fs.ensureDir(SESSION_DATA_PATH);
  await loadState();
  console.log(`[whatsapp-watcher] Starting... vault=${VAULT_PATH}`);
  console.log(`[whatsapp-watcher] Keywords: ${KEYWORD_LIST.join(', ')}`);
  await client.initialize();
}

main().catch(err => {
  console.error('[whatsapp-watcher] Fatal error:', err.message);
  process.exit(1);
});
