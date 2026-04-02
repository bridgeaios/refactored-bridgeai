#!/bin/bash
# VPS Deployment Script for BridgeAI
# Deploys Phase 2.2 + 2.3 with CSRF security hardening
# Target VPS: Configure via environment variable or command-line argument

set -e
umask 077  # Ensure all created files/dirs have restrictive permissions (600/700)

echo "=== BridgeAI VPS Deployment Script ==="
echo "This script deploys the latest code to /opt/bridgeai"
echo "Requires sudo access"

# Step 1: Setup directory structure
echo "[1/7] Setting up directory structure..."
sudo mkdir -p /opt/bridgeai
# Note: Will set ownership to bridgeai user after service user creation

# Step 2: Clone repository (HTTPS, no SSH key needed)
echo "[2/7] Cloning repository..."
cd /tmp
if [ -d "BridgeLiveWall" ]; then
  rm -rf BridgeLiveWall
fi

# Clone from specific commit hash for integrity verification
# Replace COMMIT_HASH with the current validated commit
EXPECTED_COMMIT_HASH="9f9576c"  # feat: add control plane router with topology, metrics, and event stream endpoints
git clone --depth 1 --branch win-for-twin https://github.com/bridgeaios/refactored-bridgeai.git BridgeLiveWall
cd BridgeLiveWall

# Verify commit integrity
ACTUAL_COMMIT=$(git rev-parse HEAD | cut -c1-7)
if [ "$ACTUAL_COMMIT" != "$EXPECTED_COMMIT_HASH" ]; then
  echo "ERROR: Commit hash mismatch!"
  echo "Expected: $EXPECTED_COMMIT_HASH"
  echo "Got:      $ACTUAL_COMMIT"
  echo "Aborting deployment to prevent code injection attack."
  exit 1
fi
echo "✓ Commit verified: $ACTUAL_COMMIT"

# Step 3: Move to deployment directory
echo "[3/7] Deploying to /opt/bridgeai..."
sudo cp -r . /opt/bridgeai/
cd /opt/bridgeai

# Step 4: Setup Python environment
echo "[4/7] Setting up Python virtual environment..."
cd backend
if [ -d "venv" ]; then
  sudo rm -rf venv
fi
sudo python3 -m venv venv
sudo chown -R root:root venv

# Step 5: Install dependencies
echo "[5/7] Installing Python dependencies..."
sudo venv/bin/pip install --upgrade pip setuptools wheel
sudo venv/bin/pip install -r requirements.txt

# Step 6: Setup environment variables
echo "[6/7] Setting up environment variables..."
if [ ! -f ".env" ]; then
  echo "Creating .env file - PLEASE EDIT WITH PRODUCTION SECRETS:"
  echo ""
  echo "Required environment variables (edit /opt/bridgeai/backend/.env):"
  echo "  DATABASE_URL=postgresql://user:password@postgres-host:5432/bridgeai"
  echo "  REDIS_URL=redis://redis-host:6379"
  echo "  CLERK_SECRET_KEY=your-clerk-secret"
  echo "  NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your-clerk-publishable"
  echo ""

  sudo tee .env > /dev/null <<'EOF'
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

# Vercel AI Gateway (optional) — Get from Vercel Dashboard if using AI features
VERCEL_OIDC_TOKEN=CHANGE_ME_VERCEL_TOKEN

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# CSRF Security (REQUIRED: Generate securely offline)
# Generate with: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Then manually add to .env
CSRF_SECRET_KEY=CHANGE_ME_CSRF_SECRET
EOF

  sudo chmod 600 .env
  echo "WARNING: .env created with placeholder values. Update before starting service."
else
  echo ".env file exists, skipping creation"
fi

# Step 7: Create service user (for privilege isolation)
echo "[7/7] Creating service user..."
# Create dedicated user for the application (non-root)
if ! id "bridgeai" &>/dev/null; then
  sudo useradd -r -s /bin/false -d /var/lib/bridgeai bridgeai
  sudo mkdir -p /var/lib/bridgeai
  sudo chown -R bridgeai:bridgeai /var/lib/bridgeai
  sudo chmod 750 /var/lib/bridgeai
  echo "✓ Service user 'bridgeai' created"
else
  echo "✓ Service user 'bridgeai' already exists"
fi

# Set proper permissions
sudo chown -R bridgeai:bridgeai /opt/bridgeai
sudo chmod 750 /opt/bridgeai
sudo chmod 640 /opt/bridgeai/backend/.env

# Step 8: Setup systemd service
echo "[8/8] Setting up systemd service..."
sudo tee /etc/systemd/system/bridgeai.service > /dev/null <<'EOF'
[Unit]
Description=BridgeAI Backend Service
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

ExecStart=/opt/bridgeai/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=10
StartLimitBurst=2
StartLimitInterval=300
StandardOutput=journal
StandardError=journal
StandardInput=null

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable bridgeai
sudo systemctl restart bridgeai

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit environment variables: sudo nano /opt/bridgeai/backend/.env"
echo "2. Start service: sudo systemctl start bridgeai"
echo "3. Check status: sudo systemctl status bridgeai"
echo "4. View logs: sudo journalctl -u bridgeai -f"
echo "5. Test API: curl http://102.208.228.44:8000/docs"
echo ""
echo "Service is currently set to auto-start on reboot."
