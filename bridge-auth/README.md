# Bridge Auth — Identity & Authority Layer

Node/Express service. SIWE verification, replay protection, short-lived JWT + refresh rotation, WebSocket contract events.

---

## Ladder

```
QR → Wallet → Signature → Role Check → Session Token → Live Contract Sync
```

---

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/auth/siwe` | Verify signature, check nonce/role → JWT + refresh |
| POST | `/auth/refresh` | Consume refresh token, rotate → new JWT + refresh |
| GET | `/auth/verify` | Validate Bearer token |
| WS | `/ws/events` | Subscribe to contract events (real-time push) |

---

## Env

| Variable | Default |
|----------|---------|
| `BRIDGE_AUTH_PORT` | 3030 |
| `REDIS_URL` | redis://localhost:6379/1 |
| `BRIDGE_SIWE_JWT_SECRET` | change-me-in-production |
| `BRIDGE_JWT_EXPIRY` | 900 (15 min) |
| `BRIDGE_REFRESH_EXPIRY` | 604800 (7 days) |
| `BRIDGE_SIWE_ALLOWED_DOMAINS` | localhost,localhost:3020,... |
| `BRIDGE_SIWE_RPC_URL` | https://rpc.linea.build |
| `BRIDGE_SIWE_ROLE_CONTRACT` | — |
| `BRIDGE_SIWE_ROLE_HASH` | 0x00... |
| `BRIDGE_SIWE_REQUIRE_ROLE` | 0 |
| `BRIDGE_CONTRACT_ADDRESS` | — |
| `BRIDGE_CONTRACT_POLL_INTERVAL` | 15 |

---

## Run

```bash
cd bridge-auth
npm install
npm start
```

---

## Gateway Integration

Point gateway `CONFIG.AUTH_URL` to `http://localhost:3030/auth/siwe` (or proxy `/auth/*` → 3030).
