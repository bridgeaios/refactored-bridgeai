/**
 * Bridge Backend — Sovereign entry ladder
 * SIWE, SQLite nonce, JWT, on-chain role, WebSocket events.
 */
try { require('dotenv').config(); } catch (_) { /* optional */ }
const express = require('express');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json({ limit: '1mb' }));

app.get('/health', (_, res) => {
  res.json({ ok: true, service: 'bridge-backend' });
});

app.get('/', (_, res) => {
  res.json({
    service: 'Bridge Backend',
    version: '1.0.0',
    ladder: 'SIWE, SQLite nonce, JWT, on-chain role, WebSocket events',
  });
});

app.use((_req, res) => res.status(404).json({ ok: false, error: 'not_found' }));

const server = app.listen(PORT, () => {
  console.log(`Bridge Backend at http://localhost:${PORT}`);
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`Port ${PORT} is already in use.`);
    console.error('Stop the other process or run with: PORT=3002 npm run start');
    process.exit(1);
  }
  throw err;
});
