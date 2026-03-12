#!/bin/bash
set -e

echo "=== P/L Analytics — Deploy ==="

REPO_DIR="/opt/pnl"

# Pull latest code
cd "$REPO_DIR"
echo "Pulling latest..."
git pull

# Install/update Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt --break-system-packages -q 2>/dev/null || \
pip3 install -r requirements.txt -q

# Build frontend
echo "Building frontend..."
cd frontend
npm install --silent 2>/dev/null
npm run build
cd ..

# Create/update systemd service
cat > /etc/systemd/system/pnl.service << 'UNIT'
[Unit]
Description=P/L Analytics (FastAPI + React)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/pnl
ExecStart=/usr/bin/python3 api.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable pnl
systemctl restart pnl

echo ""
echo "=== Deployed! ==="
echo "App running on http://$(hostname -I | awk '{print $1}'):8505"
echo "Manage: systemctl {start|stop|restart|status} pnl"
echo "Logs:   journalctl -u pnl -f"
