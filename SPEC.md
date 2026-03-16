# Bridge DeFi Platform - Specification

## 1. Project Overview

**Project Name**: Bridge DeFi Platform  
**Type**: Full-stack DeFi Web Application  
**Stack**: FastAPI + PostgreSQL + React/TypeScript + ethers.js  
**Core Functionality**: P2P lending, staking, DEX aggregation, treasury management

---

## 2. Technology Stack

### Backend
- **Framework**: FastAPI with async support
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Auth**: Google OAuth 2.0, JWT (15min access / 7day refresh)
- **API**: RESTful `/api/v1/` with OpenAPI/Swagger

### Frontend
- **Framework**: React 18 + TypeScript
- **Build**: Vite
- **Blockchain**: ethers.js for EVM interactions
- **Charts**: Recharts for portfolio visualization

---

## 3. User Tiers (RBAC)

| Tier | Daily Limit | Fee | Rate Limit |
|------|-------------|-----|------------|
| Basic | $1,000 | 0.5% | 60/min |
| Silver | $10,000 | 0.4% | 120/min |
| Gold | $50,000 | 0.25% | 300/min |
| Platinum | Unlimited | 0.1% | Unlimited |

**Auto-upgrade criteria**: Transaction volume, staking amount, subscription duration

---

## 4. Core Features

### Authentication
- Google OAuth 2.0 registration/login
- JWT access tokens (15min) + refresh tokens (7days)
- Token revocation endpoint
- Voucher code system for promotional credits

### P2P Lending
- Collateral ratios: 110% - 150%
- Liquidation bonus: 5% for liquidators
- Daily compound interest

### DEX Integration
- Uniswap + Sushiswap aggregation
- Default slippage: 0.5%
- Swap routing optimization

### Staking
- Lock periods: 30, 60, 90, 180 days
- Tiered APY rates
- Auto-compound weekly

### Yield Farming
- Auto-compound with weekly claims
- Reward distribution tracking

### Tax Reports
- FIFO method
- PDF + CSV export

---

## 5. Treasury System

### Revenue Distribution
- 40% UBI allocation
- 30% Treasury
- 20% Operations
- 10% Founder

### Payment Rails
- **Paystack**: African markets (ZAR/NGN)
- **PayPal**: Global payments
- **Crypto**: On-chain (BRDG/ETH/SOL)

### Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/treasury/collect` | Internal collection |
| GET | `/api/v1/treasury/status` | Breakdown by project/rail/currency |
| GET | `/api/v1/treasury/ledger` | Full transaction history |
| GET | `/api/v1/treasury/rails` | Payment methods status |
| POST | `/api/v1/treasury/disburse` | Bucket withdrawal (Zero Trust) |
| POST | `/api/v1/payments/webhook/{provider}` | Payment provider webhooks |

---

## 6. Risk Management

- Portfolio diversification pie chart
- Volatility indicators (green/yellow/red)
- Real-time risk score (0-100)
- Protocol audit status display
- Geo-restrictions for prohibited jurisdictions

---

## 7. Wallet Integration

- MetaMask
- WalletConnect
- Ledger hardware wallet
- Multi-chain support (EVM auto-switch)
- USDC/USDT stablecoin support

---

## 8. API Endpoints

All endpoints prefixed with `/api/v1/`

### Auth
- `POST /auth/google` - Google OAuth login
- `POST /auth/refresh` - Refresh access token
- `POST /auth/revoke` - Revoke token

### User
- `GET /user/me` - Current user profile
- `PATCH /user/tier` - Update tier

### Lending
- `POST /lending/borrow` - Borrow funds
- `POST /lending/repay` - Repay loan
- `POST /lending/liquidate` - Liquidate position

### Staking
- `POST /staking/stake` - Stake tokens
- `POST /staking/unstake` - Unstake
- `GET /staking/rewards` - View rewards

### DEX
- `POST /dex/swap` - Token swap
- `GET /dex/quote` - Get swap quote

### Treasury
- `POST /treasury/collect`
- `GET /treasury/status`
- `GET /treasury/ledger`
- `GET /treasury/rails`
- `POST /treasury/disburse`

---

## 9. Code Quality Requirements

- **Tests**: pytest with 80% coverage minimum
- **Linting**: ruff - all warnings fixed
- **Type Checking**: mypy - full coverage
- **Type Annotations**: All functions
- **Data Transfer**: Pydantic models
- **Internal Data**: dataclasses

---

## 10. Real-time Features

- WebSocket connections for price updates
- Portfolio metrics dashboard with Recharts
- Transaction history with filtering/sorting/CSV export
- Full fee breakdown before transaction signing
