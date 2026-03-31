# BridgeAI VPS Deployment Checklist

**Project**: BridgeAI Digital Twin Platform
**Target**: 102.208.228.44 (Ubuntu 22.04.5 LTS)
**Release**: Phase 2.2 + 2.3 + Security Hardening
**Commit**: `6105fc0` - "Phase 2.2 + 2.3: Orchestration & Memory Intelligence + CSRF Security"
**Status**: Ready for deployment ✅

---

## Pre-Deployment Verification ✅

### Code Status
- [x] All files committed to `win-for-twin` branch
- [x] Code pushed to GitHub: https://github.com/bridgeaios/refactored-bridgeai.git
- [x] Commit hash verified: `6105fc0`
- [x] All Phase 2.2 modules integrated:
  - [x] tool_registry.py (Tool abstraction)
  - [x] planner.py (Goal decomposition)
  - [x] execution_loop.py (Execution with retry logic)
  - [x] orchestrator.py (Main EHSA service)
  - [x] cortex_integration.py (Authority enforcement)
- [x] All Phase 2.3 modules integrated:
  - [x] models.py (Data structures)
  - [x] pattern_extraction.py (Pattern learning)
  - [x] prediction_engine.py (Action forecasting)
  - [x] learning_system.py (Learning orchestration)
  - [x] ehsa_enhanced.py (Enhanced EHSA)
- [x] Security hardening complete:
  - [x] CSRF protection (constant-time token validation)
  - [x] XSS prevention (httpOnly cookies)
  - [x] CSP headers configured
  - [x] Rate limiting on auth endpoints

### Deployment Artifacts
- [x] vps-deploy.sh - Automated deployment script
- [x] SINGLE-COMMAND-DEPLOY.sh - Copy-paste deployment
- [x] VPS-DEPLOYMENT-GUIDE.md - Comprehensive manual guide
- [x] PHASE-2.2-COMPLETION.md - Architecture documentation
- [x] PHASE-2.3-COMPLETION.md - Memory system documentation

---

## Deployment Execution

### Choose One Method:

#### Method 1: Automated Script (Recommended)
**If you have SSH access (with key passphrase or password):**

```bash
# From your local machine
cd /e/BridgeAI/BridgeLiveWall

# Option A: SSH with key (provide passphrase when prompted)
scp vps-deploy.sh root@102.208.228.44:/tmp/
ssh root@102.208.228.44 'bash /tmp/vps-deploy.sh'

# Option B: SSH with password
sshpass -p "YOUR_VPS_ROOT_PASSWORD" scp vps-deploy.sh root@102.208.228.44:/tmp/
sshpass -p "YOUR_VPS_ROOT_PASSWORD" ssh root@102.208.228.44 'bash /tmp/vps-deploy.sh'
```

#### Method 2: Single Command (Easiest)
**SSH into VPS and copy-paste entire block:**

```bash
# Step 1: SSH into VPS
ssh root@102.208.228.44
# Or: ssh -i ~/.ssh/id_ed25519 root@102.208.228.44

# Step 2: Copy and paste the contents of SINGLE-COMMAND-DEPLOY.sh
# This will execute the entire deployment automatically
```

#### Method 3: Manual Steps
**For maximum control, follow VPS-DEPLOYMENT-GUIDE.md:**

1. SSH into VPS
2. Execute steps 1-6 manually
3. Verify each step

---

## Post-Deployment Verification

### Phase 1: Service Status
```bash
# Check service is running
sudo systemctl status bridgeai

# View recent logs
sudo journalctl -u bridgeai -n 20

# Should see: "Started UvicornServer"
```

### Phase 2: API Health
```bash
# Test from VPS
curl -s http://localhost:8000/health | jq .

# Expected response:
# { "status": "ok" }
```

### Phase 3: CSRF Protection
```bash
# Get CSRF token
curl -i -X OPTIONS http://102.208.228.44:8000/api/auth/login

# Response should include header:
# X-CSRF-Token: [32-character-token]
```

### Phase 4: Memory System
```bash
# Check if learning module initialized
curl -s http://102.208.228.44:8000/api/memory/test/insights | jq .

# Should return learning status or 404 (before first execution)
```

---

## Configuration Steps

### Step 1: Environment Variables
**File**: `/opt/bridgeai/backend/.env`

Required values to update:
```env
# Database (PostgreSQL)
DATABASE_URL=postgresql://bridgeai:YOUR_PASSWORD@localhost:5432/bridgeai

# Cache (Redis)
REDIS_URL=redis://localhost:6379

# Authentication (Clerk)
CLERK_SECRET_KEY=sk_test_YOUR_SECRET_KEY
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_PUBLIC_KEY

# Optional: AI Gateway
VERCEL_OIDC_TOKEN=YOUR_TOKEN_HERE
```

### Step 2: Database Setup
**If PostgreSQL is not installed:**
```bash
sudo apt-get install -y postgresql postgresql-contrib
sudo -u postgres psql

# Inside psql:
CREATE USER bridgeai WITH PASSWORD 'secure_password';
CREATE DATABASE bridgeai OWNER bridgeai;
GRANT ALL PRIVILEGES ON DATABASE bridgeai TO bridgeai;
\q
```

### Step 3: Redis Setup
**If Redis is not installed:**
```bash
sudo apt-get install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Verify
redis-cli ping
# Expected: PONG
```

### Step 4: SSL/TLS (Production)
**Configure domain and certificates:**
```bash
# Install Certbot for Let's Encrypt
sudo apt-get install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d your-domain.com

# Update nginx/reverse proxy to use certificate
```

### Step 5: Firewall Configuration
**Open necessary ports:**
```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw allow 8000/tcp # BridgeAI (internal)
sudo ufw enable
```

---

## Monitoring & Operations

### Real-time Monitoring
```bash
# Watch logs in real-time
sudo journalctl -u bridgeai -f --lines=50

# Monitor system resources
watch -n 1 'ps aux | grep uvicorn'

# Check open connections
sudo netstat -tuln | grep 8000
```

### Service Management
```bash
# Start/stop/restart
sudo systemctl start bridgeai
sudo systemctl stop bridgeai
sudo systemctl restart bridgeai

# Check status
sudo systemctl status bridgeai --full

# View last 100 log lines
sudo journalctl -u bridgeai -n 100
```

### Database Management
```bash
# Connect to database
psql -U bridgeai -d bridgeai

# List tables
\dt

# Check database size
SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) FROM pg_database;
```

### Redis Management
```bash
# Connect to Redis
redis-cli

# Check keys
KEYS *

# Get memory info
INFO memory

# Monitor in real-time
MONITOR
```

---

## Troubleshooting

### Service won't start
```bash
# Check detailed error
sudo systemctl status bridgeai -l --no-pager

# Test Python directly
cd /opt/bridgeai/backend
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Check if port is already in use
sudo lsof -i :8000
```

### Database connection error
```bash
# Test PostgreSQL connection
psql -U bridgeai -d bridgeai -h localhost

# Check DATABASE_URL format
cat /opt/bridgeai/backend/.env | grep DATABASE_URL

# Verify PostgreSQL is running
sudo systemctl status postgresql
```

### Redis connection error
```bash
# Test Redis connection
redis-cli ping

# Check REDIS_URL in .env
cat /opt/bridgeai/backend/.env | grep REDIS_URL

# Verify Redis is running
sudo systemctl status redis-server
```

### API returns 403 CSRF errors
```bash
# This is expected for POST/PUT/DELETE without CSRF token
# Verify CSRF flow is working

# Get token
CSRF_TOKEN=$(curl -s -X OPTIONS http://localhost:8000/api/auth/login | grep -oP 'X-CSRF-Token: \K[^ \n]+')

# Use token in request
curl -X POST http://localhost:8000/api/auth/login \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'
```

---

## Rollback Plan

If critical issues occur:

```bash
# Stop current version
sudo systemctl stop bridgeai

# Go back to main branch
cd /opt/bridgeai
git checkout main
git pull origin main

# Restart with previous version
sudo systemctl start bridgeai

# Verify
sudo systemctl status bridgeai
```

---

## Performance Benchmarks

Expected metrics after deployment:

| Metric | Expected | Notes |
|--------|----------|-------|
| API Startup | <5 seconds | Cold start with uvicorn |
| Health Check | <10ms | Simple endpoint |
| CSRF Token Gen | <1ms | Per request |
| Pattern Learning | <10ms | Per execution trace |
| Prediction | <5ms | Based on cached patterns |
| Database Query | <50ms | Simple queries |
| Redis Operation | <5ms | In-process cache |

---

## Security Verification Checklist

After deployment, verify:

- [ ] CSRF tokens are generated for every form (OPTIONS request)
- [ ] CSRF tokens are validated on POST/PUT/DELETE/PATCH
- [ ] Invalid CSRF tokens return 403 Forbidden
- [ ] CSRF token changes after each request
- [ ] Tokens are stored in httpOnly cookies (not localStorage)
- [ ] Tokens cannot be accessed via JavaScript
- [ ] rate limiting is active on /api/auth/* endpoints
- [ ] All API responses include Security Headers:
  - [ ] X-Content-Type-Options: nosniff
  - [ ] X-Frame-Options: DENY
  - [ ] X-XSS-Protection: 1; mode=block
  - [ ] Strict-Transport-Security (for HTTPS)
  - [ ] Content-Security-Policy header present

Verification command:
```bash
curl -i http://102.208.228.44:8000/docs | grep -E "X-Content-Type-Options|X-Frame-Options|X-XSS-Protection|Content-Security-Policy"
```

---

## Next Phase Operations

### Continuous Deployment
To automate future deployments:
```bash
# Setup GitHub Actions or similar
# Pull latest from win-for-twin
# Run tests
# Deploy to VPS
# Verify deployment
```

### Monitoring Setup
Configure monitoring for:
- Service health (systemd watchdog)
- API latency (Application Performance Monitoring)
- Database performance (PostgreSQL logs)
- Error rates (Application error tracking)
- Learning readiness metrics (Custom dashboard)

### Backup Strategy
Regular backups of:
- PostgreSQL database (daily)
- Redis snapshots (daily)
- Configuration files (.env, systemd)
- Code repository (GitHub)

---

## Deployment Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Code commit | <1 min | ✅ Complete |
| Code push | <1 min | ✅ Complete |
| Script transfer | <1 min | ⏳ Pending SSH |
| Script execution | ~5 min | ⏳ Pending SSH |
| Environment config | ~2 min | ⏳ After deploy |
| Service startup | ~1 min | ⏳ After config |
| Verification | ~2 min | ⏳ After startup |
| **Total Estimated** | **~12 min** | ⏳ Ready to start |

---

## Current Status

✅ **All code is committed and pushed to GitHub**
- Branch: `win-for-twin`
- Commit: `6105fc0`
- Repository: https://github.com/bridgeaios/refactored-bridgeai.git

✅ **All deployment scripts are ready**
- Automated script: vps-deploy.sh
- Manual guide: VPS-DEPLOYMENT-GUIDE.md
- Copy-paste script: SINGLE-COMMAND-DEPLOY.sh

⏳ **Deployment awaiting SSH access to VPS**
- Target: 102.208.228.44
- Required: SSH credentials (key with passphrase or password auth)

---

## Next Action

**To complete deployment, choose one of these options:**

### Option A: Use existing SSH setup
```bash
# If SSH key passphrase is available, use the automated script
cd /e/BridgeAI/BridgeLiveWall
scp vps-deploy.sh root@102.208.228.44:/tmp/
ssh root@102.208.228.44 'bash /tmp/vps-deploy.sh'
```

### Option B: Direct access to VPS
```bash
# SSH into VPS directly
ssh root@102.208.228.44

# Then run:
sudo bash << 'EOF'
git clone --depth 1 --branch win-for-twin https://github.com/bridgeaios/refactored-bridgeai.git /opt/bridgeai
cd /opt/bridgeai/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# ... [continue with steps in VPS-DEPLOYMENT-GUIDE.md]
EOF
```

### Option C: Provide SSH credentials
If SSH access needs to be re-established, provide either:
- VPS root password (for sshpass authentication)
- SSH key passphrase (for key-based authentication)

---

## Support & Documentation

For detailed information, see:
- **PHASE-2.2-COMPLETION.md** - Orchestration system architecture
- **PHASE-2.3-COMPLETION.md** - Memory intelligence system architecture
- **VPS-DEPLOYMENT-GUIDE.md** - Complete deployment instructions
- **ARCHITECTURE.md** - Technical reference for all systems

---

**Deployment Ready** ✅
**Status**: All code committed and pushed, awaiting VPS access
**Date**: 2026-03-31
**Last Updated**: 2026-03-31
