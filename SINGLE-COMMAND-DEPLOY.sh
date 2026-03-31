#!/bin/bash
# One-command deployment for VPS
# Copy and paste the entire section below into your VPS terminal as root

# ============================================================================
# PASTE THIS ENTIRE SECTION INTO VPS TERMINAL (as root)
# ============================================================================

sudo bash << 'DEPLOY_EOF'
#!/bin/bash
set -e

echo "=========================================="
echo "BridgeAI VPS Deployment"
echo "=========================================="
echo ""

# Determine system
SYSTEM_OS=$(uname -s)
if [[ "$SYSTEM_OS" == "Linux" ]]; then
  echo "✓ Detected: Linux"
  DISTRO=$(lsb_release -si 2>/dev/null || echo "Unknown")
  echo "✓ Distribution: $DISTRO"
else
  echo "✗ ERROR: This script is for Linux systems only"
  exit 1
fi

# Step 1: Verify and prepare
echo ""
echo "[1/7] Preparing system..."

# Update package manager
if command -v apt-get &> /dev/null; then
  apt-get update
  apt-get install -y python3 python3-pip python3-venv git
elif command -v yum &> /dev/null; then
  yum update -y
  yum install -y python3 python3-pip git
fi

echo "✓ System ready"

# Step 2: Clone repository
echo ""
echo "[2/7] Cloning repository..."

DEPLOY_DIR="/opt/bridgeai"
mkdir -p "$DEPLOY_DIR"

# Use git clone with HTTPS (no SSH key needed)
git clone --depth 1 --branch win-for-twin \
  https://github.com/bridgeaios/refactored-bridgeai.git "$DEPLOY_DIR"

cd "$DEPLOY_DIR"

# Verify commit
COMMIT_HASH=$(git log --oneline -1 | awk '{print $1}')
echo "✓ Cloned to $DEPLOY_DIR"
echo "✓ Commit: $COMMIT_HASH"

# Step 3: Setup backend
echo ""
echo "[3/7] Setting up backend..."

cd backend

# Remove old venv if exists
[ -d "venv" ] && rm -rf venv

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo "✓ Backend environment ready"

# Step 4: Configure environment
echo ""
echo "[4/7] Configuring environment..."

if [ ! -f ".env" ]; then
  cat > .env <<'ENVEOF'
# Database Configuration
DATABASE_URL=postgresql://bridgeai:change_me_password@localhost:5432/bridgeai

# Redis Configuration (for short-term memory)
REDIS_URL=redis://localhost:6379

# Clerk Authentication
CLERK_SECRET_KEY=sk_test_change_me
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_change_me

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Vercel AI Gateway (optional)
VERCEL_OIDC_TOKEN=

# Logging
LOG_LEVEL=info
ENVEOF

  chmod 600 .env
  echo "✓ .env created with placeholders"
  echo "⚠ ACTION REQUIRED: Edit /opt/bridgeai/backend/.env with production values"
else
  echo "✓ .env already exists (not overwritten)"
fi

# Step 5: Setup systemd service
echo ""
echo "[5/7] Setting up systemd service..."

cat > /etc/systemd/system/bridgeai.service <<'SERVICEEOF'
[Unit]
Description=BridgeAI Backend API
After=network.target postgresql.service redis.service
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/bridgeai/backend
Environment="PATH=/opt/bridgeai/backend/venv/bin"
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/opt/bridgeai/backend/.env
ExecStart=/opt/bridgeai/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=on-failure
RestartSec=10
StartLimitBurst=3
StartLimitInterval=60
StandardOutput=journal
StandardError=journal
StandardInput=null

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload
systemctl enable bridgeai

echo "✓ systemd service configured"
echo "✓ Service will auto-start on boot"

# Step 6: Prepare service
echo ""
echo "[6/7] Preparing service..."

# Don't start yet - user needs to configure .env first
echo "⚠ Service created but not started (waiting for .env configuration)"

# Step 7: Verification
echo ""
echo "[7/7] Verifying deployment..."

# Check Python modules
venv/bin/python -c "import fastapi; import sqlalchemy; print('✓ Core dependencies available')" || exit 1

# Check directory structure
[ -f "app/main.py" ] && echo "✓ Main application found" || exit 1
[ -f ".env" ] && echo "✓ Environment file found" || exit 1
[ -f "requirements.txt" ] && echo "✓ Requirements file found" || exit 1

echo ""
echo "=========================================="
echo "DEPLOYMENT COMPLETE ✓"
echo "=========================================="
echo ""
echo "NEXT STEPS:"
echo "1. Edit configuration:"
echo "   nano /opt/bridgeai/backend/.env"
echo ""
echo "   Required values:"
echo "   - DATABASE_URL: PostgreSQL connection string"
echo "   - REDIS_URL: Redis connection string"
echo "   - CLERK_*: Authentication keys"
echo ""
echo "2. Setup database (if first time):"
echo "   # PostgreSQL setup documented in VPS-DEPLOYMENT-GUIDE.md"
echo ""
echo "3. Setup Redis (if first time):"
echo "   apt-get install -y redis-server"
echo "   systemctl enable redis-server && systemctl start redis-server"
echo ""
echo "4. Start service:"
echo "   systemctl start bridgeai"
echo ""
echo "5. Check status:"
echo "   systemctl status bridgeai"
echo ""
echo "6. View logs:"
echo "   journalctl -u bridgeai -f"
echo ""
echo "7. Test API:"
echo "   curl http://localhost:8000/docs"
echo ""
echo "=========================================="
echo ""

DEPLOY_EOF

# ============================================================================
# END OF DEPLOY SECTION
# ============================================================================
