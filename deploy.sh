#!/bin/bash
set -e

echo "=== P/L Analytics — Deploy ==="

apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv python3.12-venv 2>/dev/null || \
apt-get install -y -qq python3 python3-pip python3-venv

REPO_DIR="/opt/pnl"
if [ -d "$REPO_DIR" ]; then
    echo "Updating repo..."
    cd "$REPO_DIR" && git pull
else
    echo "Cloning repo..."
    git clone https://github.com/arozenfelds-hash/pnl.git "$REPO_DIR"
    cd "$REPO_DIR"
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "Setting up systemd service..."
cat > /etc/systemd/system/pnl.service << 'UNIT'
[Unit]
Description=P/L Analytics (Streamlit)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/pnl
ExecStart=/opt/pnl/venv/bin/streamlit run app.py --server.port 8504 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable pnl
systemctl restart pnl

echo ""
echo "=== Deployed! ==="
echo "App running on http://$(hostname -I | awk '{print $1}'):8504"
echo "Manage: systemctl {start|stop|restart|status} pnl"
echo "Logs:   journalctl -u pnl -f"
