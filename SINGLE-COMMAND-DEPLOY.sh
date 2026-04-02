#!/bin/bash
# One-command deployment for VPS
# Copy and paste the entire section below into your VPS terminal as root

# ============================================================================
# PASTE THIS ENTIRE SECTION INTO VPS TERMINAL (as root)
# ============================================================================

sudo bash << 'DEPLOY_EOF'
#!/bin/bash
set -e
umask 077  # Ensure all created files/dirs have restrictive permissions (600/700)

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
# Verify against expected commit hash
EXPECTED_COMMIT_HASH="9f9576c"  # feat: add control plane router with topology, metrics, and event stream endpoints
git clone --depth 1 --branch win-for-twin \
  https://github.com/bridgeaios/refactored-bridgeai.git "$DEPLOY_DIR"

cd "$DEPLOY_DIR"

# Verify commit integrity (prevent supply chain attacks)
ACTUAL_COMMIT=$(git rev-parse HEAD | cut -c1-7)
if [ "$ACTUAL_COMMIT" != "$EXPECTED_COMMIT_HASH" ]; then
  echo "✗ ERROR: Commit hash mismatch!"
  echo "  Expected: $EXPECTED_COMMIT_HASH"
  echo "  Got:      $ACTUAL_COMMIT"
  echo "  Aborting deployment to prevent code injection attack."
  exit 1
fi
echo "✓ Cloned to $DEPLOY_DIR"
echo "✓ Commit verified: $ACTUAL_COMMIT"

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
# ⚠️ REQUIRED: Update all values below with your production secrets
# DO NOT commit this file with real credentials to version control

# Database — PostgreSQL connection string
# Format: postgresql://username:password@hostname:port/database
# Example: postgresql://bridgeai:YourSecurePassword123@db.example.com:5432/bridgeai
DATABASE_URL=postgresql://bridgeai:CHANGE_ME_STRONG_PASSWORD@localhost:5432/bridgeai

# Redis cache — Connection string with optional password
# Without password: redis://localhost:6379
# With password: redis://:password@localhost:6379
REDIS_URL=redis://:CHANGE_ME_REDIS_PASSWORD@localhost:6379

# Clerk Authentication — Get from Clerk Dashboard
# Secret key (must be kept private)
CLERK_SECRET_KEY=CHANGE_ME_CLERK_SECRET_KEY

# Clerk public key (safe to expose)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=CHANGE_ME_CLERK_PUBLIC_KEY

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Vercel AI Gateway (optional) — Get from Vercel Dashboard if using AI features
VERCEL_OIDC_TOKEN=CHANGE_ME_VERCEL_TOKEN

# CSRF Security (REQUIRED: Generate securely offline)
# Generate with: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Then manually add to .env
CSRF_SECRET_KEY=CHANGE_ME_CSRF_SECRET

# Logging
LOG_LEVEL=info
ENVEOF

  chmod 600 .env
  echo "✓ .env created with placeholders"
  echo "⚠ ACTION REQUIRED: Edit /opt/bridgeai/backend/.env with production values"
else
  echo "✓ .env already exists (not overwritten)"
fi

# Step 5: Create service user (for privilege isolation)
echo ""
echo "[5/7] Creating service user..."

# Create dedicated user for the application (non-root)
if ! id "bridgeai" &>/dev/null; then
  useradd -r -s /bin/false -d /var/lib/bridgeai bridgeai
  mkdir -p /var/lib/bridgeai
  chown -R bridgeai:bridgeai /var/lib/bridgeai
  chmod 750 /var/lib/bridgeai
  echo "✓ Service user 'bridgeai' created"
else
  echo "✓ Service user 'bridgeai' already exists"
fi

# Set proper permissions
chown -R bridgeai:bridgeai /opt/bridgeai
chmod 750 /opt/bridgeai
chmod 640 /opt/bridgeai/backend/.env

# Step 6: Setup systemd service
echo ""
echo "[6/7] Setting up systemd service..."

cat > /etc/systemd/system/bridgeai.service <<'SERVICEEOF'
[Unit]
Description=BridgeAI Backend API
After=network.target postgresql.service redis.service
Wants=network-online.target

[Service]
Type=simple
User=bridgeai
Group=bridgeai
WorkingDirectory=/opt/bridgeai/backend
Environment="PATH=/opt/bridgeai/backend/venv/bin"
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/opt/bridgeai/backend/.env

# Security hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/bridgeai/backend

ExecStart=/opt/bridgeai/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=on-failure
RestartSec=10
StartLimitBurst=2
StartLimitInterval=300
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

# Step 7: Prepare service
echo ""
echo "[7/8] Preparing service..."

# Don't start yet - user needs to configure .env first
echo "⚠ Service created but not started (waiting for .env configuration)"

# Step 8: Verification
echo ""
echo "[8/8] Verifying deployment..."

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
