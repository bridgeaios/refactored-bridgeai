#!/bin/bash
# VPS Deployment Script for BridgeAI
# Target: 102.208.228.44
# Deploys Phase 2.2 + 2.3 with CSRF security hardening

set -e

echo "=== BridgeAI VPS Deployment Script ==="
echo "This script deploys the latest code to /opt/bridgeai"
echo "Requires sudo access"

# Step 1: Setup directory structure
echo "[1/7] Setting up directory structure..."
sudo mkdir -p /opt/bridgeai
sudo chown -R root:root /opt/bridgeai

# Step 2: Clone repository (HTTPS, no SSH key needed)
echo "[2/7] Cloning repository..."
cd /tmp
if [ -d "BridgeLiveWall" ]; then
  rm -rf BridgeLiveWall
fi
git clone --depth 1 --branch win-for-twin https://github.com/bridgeaios/refactored-bridgeai.git BridgeLiveWall
cd BridgeLiveWall

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
# Database
DATABASE_URL=postgresql://bridgeai:change-me@localhost:5432/bridgeai

# Redis (for short-term memory)
REDIS_URL=redis://localhost:6379

# Clerk Authentication
CLERK_SECRET_KEY=sk_test_change_me
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_change_me

# Vercel AI Gateway (if using)
VERCEL_OIDC_TOKEN=change_me

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
EOF

  sudo chmod 600 .env
  echo "WARNING: .env created with placeholder values. Update before starting service."
else
  echo ".env file exists, skipping creation"
fi

# Step 7: Setup systemd service
echo "[7/7] Setting up systemd service..."
sudo tee /etc/systemd/system/bridgeai.service > /dev/null <<'EOF'
[Unit]
Description=BridgeAI Backend Service
After=network.target

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
