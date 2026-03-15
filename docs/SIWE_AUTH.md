# SIWE Auth — Sovereign Entry Protocol Backend

Backend signature verification, replay protection (nonce DB), JWT issuance, on-chain role verification, contract event listener.

**Two backends:** Python (`/api/auth/siwe`) or Bridge Auth Node service (`bridge-auth/`, port 3030) for full ladder: short JWT + refresh rotation, WebSocket events.

---

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/auth/siwe` | Verify signature, check nonce, optionally verify on-chain role, issue JWT |

---

## Request

```json
{
  "message": "Bridge AI OS Login\nDomain: localhost:3020\nAddress: 0x...\nNonce: 1234567890",
  "signature": "0x..."
}
```

---

## Response (success)

```json
{
  "ok": true,
  "data": {
    "token": "eyJ...",
    "address": "0x...",
    "auth": "economic"
  }
}
```

Use `token` as `authToken` in API requests (e.g. `/api/state`, `/api/marketplace/*`).

---

## Environment

| Variable | Description | Default |
|----------|-------------|---------|
| `BRIDGE_SIWE_JWT_SECRET` | JWT signing secret | `change-me-in-production` |
| `BRIDGE_SIWE_JWT_EXPIRY` | JWT expiry (seconds) | `86400` (24h) |
| `BRIDGE_SIWE_ALLOWED_DOMAINS` | Comma-separated domains | `localhost,localhost:3020,...` |
| `BRIDGE_SIWE_REQUIRE_ROLE` | Require on-chain role | `0` |
| `BRIDGE_SIWE_ROLE_CONTRACT` | AccessControl contract address | `` |
| `BRIDGE_SIWE_ROLE_HASH` | Role bytes32 (e.g. MEMBER) | `0x00...` |
| `BRIDGE_SIWE_RPC_URL` | RPC for role check | `https://rpc.linea.build` |
| `BRIDGE_CONTRACT_LISTENER` | Enable event listener | `0` |
| `BRIDGE_CONTRACT_ADDRESS` | Contract for events | `` |
| `BRIDGE_CONTRACT_RPC_URL` | RPC for listener | `https://rpc.linea.build` |
| `BRIDGE_CONTRACT_POLL_INTERVAL` | Poll interval (sec) | `30` |

---

## Flow

1. Gateway: user signs message (domain, address, nonce)
2. Gateway: POST to `/api/auth/siwe`
3. Backend: parse message, verify domain in allowlist
4. Backend: `eth_account.recover_message` → recover address
5. Backend: check nonce not used (Redis `siwe:nonce:{addr}:{nonce}`)
6. Backend: optionally call `hasRole(role, address)` on contract
7. Backend: store nonce, issue JWT
8. Gateway: store JWT in `localStorage.bridge_siwe_jwt`
9. App: pass JWT as `authToken` in API calls

---

## Cortex Integration

`auth_class_from_token` accepts JWT: verifies signature, maps to `AuthorityClass.ECONOMIC`.

---

## Contract Event Listener

When `BRIDGE_CONTRACT_LISTENER=1` and `BRIDGE_CONTRACT_ADDRESS` set:

- Background task polls `get_logs` every `BRIDGE_CONTRACT_POLL_INTERVAL` sec
- Events appended to Redis `contract:events`
- Physics emits `contract_event` for telemetry

---

## On-Chain Role Verification

Set `BRIDGE_SIWE_REQUIRE_ROLE=1`, `BRIDGE_SIWE_ROLE_CONTRACT`, `BRIDGE_SIWE_ROLE_HASH` (bytes32).

Calls `hasRole(roleHash, address)` before issuing JWT. Rejects if false.
