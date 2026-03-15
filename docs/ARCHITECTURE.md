# Bridge AI OS — System Architecture

**One organism. Sovereign authentication. Coordination layer.**

---

## Evolution Ladder

```
QR → Wallet → Signature → Role Check → Session Token → Live Contract Sync → Governance
 │      │         │            │              │                │               │
 │      │         │            │              │                │               └─ Snapshot, proposals, treasury
 │      │         │            │              │                └─ WebSocket push, real-time events
 │      │         │            │              └─ Short JWT + refresh rotation
 │      │         │            └─ hasRole, NFT, balance, staking
 │      │         └─ SIWE message, backend verify
 │      └─ MetaMask, chain enforcement
 └─ /gateway
```

---

## Component Map

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Gateway (HTML)          │  Digital Twin (Vite)     │  Marketplace               │
│  • Wallet connect        │  • 3D / AR               │  • Tasks, UBI, trades       │
│  • Chain switch          │  • Speech, mission       │  • Uses authToken          │
│  • Sign message          │  • Uses authToken        │                            │
│  • Copy contract         │                          │                            │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         IDENTITY & AUTHORITY LAYER                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Bridge Auth (Node/Express) 3030                                                  │
│  • POST /auth/siwe     → verify signature, nonce, role → JWT + refresh            │
│  • POST /auth/refresh  → consume refresh, rotate → new JWT + refresh              │
│  • GET  /auth/verify   → validate Bearer token                                    │
│  • WS   /ws/events     → push contract events to clients                          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│  Redis                │   │  Linea RPC              │   │  Smart Contract      │
│  • siwe:nonce:*       │   │  • getLogs              │   │  • hasRole(role, addr)│
│  • bridge:refresh:*   │   │  • getBlockNumber      │   │  • owner()            │
│  • contract:events    │   │  • Contract events     │   │  • Marketplace events │
└───────────────────────┘   └───────────────────────┘   └───────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER (Python FastAPI) 8000                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Cortex → Reducers → State → Scheduler → Expression                               │
│  • /api/state        (authToken: JWT or internal)                                │
│  • /api/marketplace  (tasks, accept, complete)                                  │
│  • /api/twin/*       (decide, simulate, evolve)                                 │
│  • /api/ubi, /api/speech, /api/health, ...                                       │
│  • WS /ws/{channel}  (real-time, heartbeat)                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND SERVER (Node) 3020                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│  • Serves /gateway, /, /#marketplace                                             │
│  • Proxies /api/* → Python backend                                               │
│  • Proxies /ws/*   → Python backend                                              │
│  • Optional: proxy /auth/* → Bridge Auth (3030)                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Mermaid: Data Flow

```mermaid
flowchart TB
    subgraph Client
        QR[QR Code]
        GW[Gateway]
        DT[Digital Twin]
        MKT[Marketplace]
    end

    subgraph Auth["Bridge Auth :3030"]
        SIWE[POST /auth/siwe]
        REF[POST /auth/refresh]
        WS_EV[WS /ws/events]
    end

    subgraph Backend["Python API :8000"]
        CORTEX[Cortex]
        API[/api/*]
    end

    subgraph External
        REDIS[(Redis)]
        RPC[Linea RPC]
        CONTRACT[Smart Contract]
    end

    QR --> GW
    GW -->|sign message| SIWE
    SIWE -->|verify| RPC
    SIWE -->|nonce| REDIS
    SIWE -->|role check| CONTRACT
    SIWE -->|JWT + refresh| GW
    GW -->|authToken| DT
    GW -->|authToken| MKT
    DT -->|Bearer JWT| API
    MKT -->|Bearer JWT| API
    REF -->|rotate| REDIS
    RPC -->|getLogs| WS_EV
    WS_EV -->|push| DT
    WS_EV -->|push| MKT
```

---

## Trust Reduction

| Assumption | Mitigation |
|------------|------------|
| User controls wallet | Signature verification (ecrecover) |
| No replay | Nonce stored in Redis, single-use |
| User has permission | On-chain `hasRole` before JWT |
| Session validity | Short-lived JWT (15 min), refresh rotation |
| Event authenticity | Events from chain, not backend invention |

**Security is achieved by reducing trust assumptions.**

---

## Deployment Topology

```
                    ┌─────────────┐
                    │   CDN /     │
                    │   Static    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Frontend   │  :3020
                    │  (gateway,  │
                    │   app)      │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐      ┌─────▼─────┐     ┌────▼────┐
    │ Bridge  │      │  Python   │     │  Redis  │
    │ Auth    │      │  API     │     │         │
    │ :3030   │      │  :8000   │     │  :6379  │
    └────┬────┘      └─────┬─────┘     └────┬────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Linea     │
                    │  RPC       │
                    └────────────┘
```

---

## Run Order

1. Redis
2. Bridge Auth: `cd bridge-auth && npm i && npm start`
3. Python API: `cd backend && uvicorn app.main:app`
4. Frontend: `cd frontend && npm start`

**Gateway points to `/gateway`. Auth can be at `/auth/*` (proxy) or `http://localhost:3030` (direct).**
