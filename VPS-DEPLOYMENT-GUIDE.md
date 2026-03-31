# VPS Deployment Guide — BridgeAI Phase 2.2 + 2.3

**Status**: Code committed and pushed ✅
**Target**: 102.208.228.44 (Ubuntu 22.04.5 LTS)
**Branch**: `win-for-twin` (commit: 6105fc0)
**Latest**: Phase 2.2 Orchestration + Phase 2.3 Memory Intelligence + CSRF Security Hardening

---

## Deployment Status Summary

| Component | Status | Location |
|-----------|--------|----------|
| Code Commit | ✅ Complete | Hash: `6105fc0` |
| Branch Push | ✅ Complete | `win-for-twin` pushed to origin |
| CSRF Security | ✅ Hardened | Constant-time token validation |
| Automated Script | ✅ Ready | `vps-deploy.sh` in repository root |
| VPS Access | ⚠️ Auth Pending | SSH key passphrase required or password auth |

---

## Prerequisites

On VPS (102.208.228.44):
- [ ] Ubuntu 22.04+ (LTS)
- [ ] Python 3.10+
- [ ] Git installed
- [ ] Root or sudo access
- [ ] PostgreSQL 14+ (for long-term memory database)
- [ ] Redis 7+ (for short-term memory cache)

---

## Deployment Option A: Automated Script

**Requirements**: SSH access with either:
- SSH key (run from local machine)
- Password authentication (via sshpass)

**Steps**:

### Option A1: Via SSH key (if passphrase is available)

```bash
# On local machine
cd /e/BridgeAI/BridgeLiveWall

# Copy script to VPS and execute
scp vps-deploy.sh root@102.208.228.44:/tmp/
ssh root@102.208.228.44 'bash /tmp/vps-deploy.sh'
```

### Option A2: Via sshpass (password authentication)

```bash
# On local machine
cd /e/BridgeAI/BridgeLiveWall

# Transfer script
sshpass -p "YOUR_ROOT_PASSWORD" scp vps-deploy.sh root@102.208.228.44:/tmp/

# Execute script
sshpass -p "YOUR_ROOT_PASSWORD" ssh root@102.208.228.44 'bash /tmp/vps-deploy.sh'
```

---

## Deployment Option B: Manual Steps

**For manual deployment, execute these commands on the VPS**:

### 1. Verify System

```bash
whoami  # Should output: root
pwd     # Should output: /root
lsb_release -a  # Verify Ubuntu 22.04 LTS
```

### 2. Clone Repository

```bash
# Create deployment directory
sudo mkdir -p /opt/bridgeai
cd /opt/bridgeai

# Clone latest code (HTTPS, no SSH key needed)
sudo git clone --depth 1 --branch win-for-twin \
  https://github.com/bridgeaios/refactored-bridgeai.git .

# Verify commit hash
git log --oneline -1  # Should show: 6105fc0
```

### 3. Setup Python Environment

```bash
cd /opt/bridgeai/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Verify Python version
python --version  # Should be 3.10+

# Upgrade pip and install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Create .env file with placeholders
nano /opt/bridgeai/backend/.env
```

**Minimum .env configuration**:

```env
# Database
DATABASE_URL=postgresql://bridgeai:password@localhost:5432/bridgeai

# Redis
REDIS_URL=redis://localhost:6379

# Clerk Auth
CLERK_SECRET_KEY=sk_test_your_key
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_key

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Vercel AI Gateway (optional)
VERCEL_OIDC_TOKEN=your_token_here
```

### 5. Setup systemd Service

```bash
# Create systemd service file
sudo tee /etc/systemd/system/bridgeai.service > /dev/null <<'EOF'
[Unit]
Description=BridgeAI Backend Service
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/bridgeai/backend
Environment="PATH=/opt/bridgeai/backend/venv/bin"
EnvironmentFile=/opt/bridgeai/backend/.env
ExecStart=/opt/bridgeai/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable bridgeai
sudo systemctl restart bridgeai
```

### 6. Verify Deployment

```bash
# Check service status
sudo systemctl status bridgeai

# View logs
sudo journalctl -u bridgeai -f

# Test API
curl http://localhost:8000/docs

# Test from external (from local machine)
curl http://102.208.228.44:8000/docs
```

---

## Security Hardening (Already Applied)

The deployment includes:

✅ **CSRF Protection**
- Token generation: `secrets.token_urlsafe(32)` (256-bit entropy)
- Token validation: `hmac.compare_digest()` (constant-time, prevents timing attacks)
- Token transport: `X-CSRF-Token` header or form field
- Cookie flags: `secure=True, httponly=True, samesite="Strict"`

✅ **XSS Prevention**
- Removed `localStorage.setItem()`
- Token stored in httpOnly cookie (JavaScript cannot access)
- CSRF token fetched via header extraction only

✅ **Content Security Policy**
- `default-src 'none'` (deny all by default)
- `script-src 'self'` (no inline scripts)
- `style-src 'self'` (no inline styles)
- Strict frame options, clickjacking protection

✅ **Authentication**
- Clerk OAuth 2.0 integration
- Rate limiting: 5 req/min on auth endpoints
- Session-based auth with httpOnly cookies

---

## Post-Deployment Verification

### API Health Check

```bash
# On VPS
curl -s http://localhost:8000/health | jq .

# From local
curl -s http://102.208.228.44:8000/health | jq .
```

### CSRF Token Flow

```bash
# Step 1: Get CSRF token via OPTIONS request
curl -i -X OPTIONS http://102.208.228.44:8000/api/auth/login

# Should include response header: X-CSRF-Token: [token_value]

# Step 2: Use token in POST request
CSRF_TOKEN="[token from step 1]"
curl -X POST http://102.208.228.44:8000/api/auth/login \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'
```

### Learning System Status

```bash
# Check if memory module is initialized
curl http://102.208.228.44:8000/api/memory/user_123/insights
```

---

## Troubleshooting

### Service fails to start

```bash
# Check detailed logs
sudo journalctl -u bridgeai -n 50

# Verify Python path
sudo systemctl show bridgeai -p ExecStart

# Test Python directly
cd /opt/bridgeai/backend
./venv/bin/python -c "import app; print('Import successful')"
```

### Database connection error

```bash
# Verify PostgreSQL is running
sudo systemctl status postgresql

# Check DATABASE_URL format
grep DATABASE_URL /opt/bridgeai/backend/.env

# Test connection
psql "postgresql://bridgeai:password@localhost:5432/bridgeai"
```

### Redis connection error

```bash
# Verify Redis is running
sudo systemctl status redis-server

# Test Redis connectivity
redis-cli ping  # Should return: PONG
```

### Port 8000 already in use

```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill process (if safe)
sudo kill -9 [PID]

# Or change port in .env
sed -i 's/API_PORT=8000/API_PORT=8001/g' .env
```

---

## Database Setup

If PostgreSQL is not yet configured:

```bash
# Install PostgreSQL (if not present)
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib

# Create BridgeAI database
sudo sudo -u postgres psql <<'EOF'
CREATE USER bridgeai WITH PASSWORD 'secure_password_here';
CREATE DATABASE bridgeai OWNER bridgeai;
GRANT ALL PRIVILEGES ON DATABASE bridgeai TO bridgeai;
EOF

# Update DATABASE_URL in .env with the password
```

---

## Redis Setup

If Redis is not yet configured:

```bash
# Install Redis (if not present)
sudo apt-get update
sudo apt-get install -y redis-server

# Start and enable Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Verify
redis-cli ping  # Should return: PONG
```

---

## Monitoring

### Real-time logs

```bash
sudo journalctl -u bridgeai -f --lines=50
```

### Performance metrics

```bash
# CPU/Memory usage
ps aux | grep "python -m uvicorn"

# Check file descriptors
lsof -p [PID]

# Monitor learning system activity
curl http://102.208.228.44:8000/api/memory/stats
```

### Alert setup (recommended)

Configure systemd watchdog for automatic restart:

```ini
[Service]
WatchdogSec=30s
Restart=on-failure
RestartSec=5
StartLimitBurst=3
StartLimitIntervalSec=60
```

---

## Rollback Plan

If deployment has issues:

```bash
# Stop service
sudo systemctl stop bridgeai

# Previous commit is on main branch
cd /opt/bridgeai
git checkout main

# Restart with previous version
sudo systemctl start bridgeai

# Verify
sudo systemctl status bridgeai
```

---

## Architecture Deployed

### Phase 2.2: Orchestration Intelligence
- Tool Registry abstraction for service discovery
- Dynamic goal decomposition and planning
- Execution loop with retry logic (max 2 retries)
- Fallback mechanisms for error recovery
- Cortex authority integration (PUBLIC/ECONOMIC/INTERNAL/ORCHESTRATOR)
- Unified execution tracing

### Phase 2.3: Memory Intelligence
- ExecutionTrace collection from every EHSA execution
- PatternExtractor: high-confidence pattern learning (>0.7 confidence, ≥5 observations)
- PredictionEngine: forecasts next actions based on historical patterns
- LearningSystem: orchestrates all learning components
- EnhancedEHSA: 7-phase execution with learning integration
- 5-layer memory hierarchy (short-term Redis + long-term database)

### Security Hardening
- CSRF protection with secure token handling
- Constant-time token validation (prevents timing attacks)
- httpOnly secure cookies (prevents XSS)
- Content Security Policy headers
- Rate limiting on auth endpoints
- Authority-based access control

---

## Next Steps

After deployment:

1. **Configure Monitoring**
   - Set up Grafana dashboards
   - Configure alerting for service failures
   - Track learning system readiness metrics

2. **Load Testing**
   - Verify CSRF protection under load
   - Test pattern learning with synthetic workloads
   - Measure API response times

3. **Production Checklist**
   - [ ] All environment variables configured
   - [ ] Database backups scheduled
   - [ ] Redis persistence enabled
   - [ ] SSL/TLS certificates installed
   - [ ] Domain DNS configured
   - [ ] Firewall rules configured
   - [ ] Log aggregation setup
   - [ ] Monitoring alerts active

---

## Support

For issues or questions during deployment:

1. Check logs: `sudo journalctl -u bridgeai -f`
2. Verify environment: `cat /opt/bridgeai/backend/.env`
3. Test connectivity: `curl http://102.208.228.44:8000/health`
4. Review architecture: See PHASE-2.2-COMPLETION.md and PHASE-2.3-COMPLETION.md

---

**Deployment Guide Version**: 1.0
**Last Updated**: 2026-03-31
**Repository**: https://github.com/bridgeaios/refactored-bridgeai.git
**Branch**: win-for-twin (commit 6105fc0)
