# Bridge AI OS — Sovereign Web3 Entry Protocol

**Purpose:** Single QR entry point. Wallet, chain enforcement, contract verification, owner read, live gas/block, SIWE-style signature.

---

## Route

| Path | Purpose |
|------|---------|
| `/gateway` | Sovereign Gateway (point QR here) |

---

## Configuration

Edit `frontend/public/gateway/index.html` and set in the `CONFIG` object:

| Key | Description |
|-----|-------------|
| `CONTRACT_ADDRESS` | Immutable contract address (Linea Mainnet) |
| `AUDIT_HASH` | SHA256 of published audit PDF (must match public artifact) |
| `EXPECTED_CHAIN_ID` | 59144 (Linea Mainnet) |
| `RPC_URL` | Linea RPC (for `wallet_addEthereumChain`) |

---

## Features

- **Wallet detection** — `window.ethereum`
- **Automatic chain switch** — enforces Linea Mainnet; adds chain if missing (4902)
- **Live gas price** — `provider.getFeeData()`
- **Real-time block height** — polled every 10s
- **On-chain contract check** — `provider.getCode()`
- **Contract owner read** — `owner()` (Ownable pattern)
- **Audit hash display** — static visible verification
- **Copy contract address** — immutable, no ambiguity
- **SIWE-style signature** — message signing (domain, address, nonce)

---

## SIWE Caveat

Client-side signature alone is **cosmetic authentication**. For real SIWE:

1. Send signed message to backend
2. Verify signature server-side
3. Issue JWT session token
4. Store nonce server-side (replay protection)

**Next evolution:** Backend signature verification, nonce DB, contract event listener, on-chain role verification.

---

## Trust Model

Real validation requires:
1. Third-party contract audit
2. Published audit PDF
3. Displayed SHA256 matches public artifact

**Bridges that last are audited, not advertised.**
