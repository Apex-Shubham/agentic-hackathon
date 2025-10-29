#!/bin/bash
###############################################################################
# Deploy Trading Bot as Systemd Service (Linux)
# Creates a systemd service for continuous operation
###############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "⚠️  This script is for Linux only (systemd)"
    echo "ℹ️  For macOS, use start_bot.sh instead"
    exit 1
fi

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Get current user (the one who ran sudo)
REAL_USER="${SUDO_USER:-$USER}"

# Get absolute path
BOT_DIR="$SCRIPT_DIR"
PYTHON_PATH="$BOT_DIR/venv/bin/python3"

# Check if venv exists
if [ ! -f "$PYTHON_PATH" ]; then
    echo "❌ Virtual environment not found at $PYTHON_PATH"
    echo "💡 Run ./deploy.sh first to set up the environment"
    exit 1
fi

echo "📋 Creating systemd service..."
echo "   Bot directory: $BOT_DIR"
echo "   Python: $PYTHON_PATH"
echo "   User: $REAL_USER"
echo ""

# Create systemd service file
SERVICE_FILE="/etc/systemd/system/binance-trading-bot.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Binance Futures Trading Bot (14-Day Competition)
After=network.target

[Service]
Type=simple
User=$REAL_USER
WorkingDirectory=$BOT_DIR
Environment=PATH=$BOT_DIR/venv/bin
ExecStart=$PYTHON_PATH $BOT_DIR/run_with_restart.py
Restart=always
RestartSec=10
StandardOutput=append:$BOT_DIR/logs/bot_service.log
StandardError=append:$BOT_DIR/logs/bot_service_error.log

# Resource limits
LimitNOFILE=65536
MemoryMax=2G

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created: $SERVICE_FILE"
echo ""

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload

echo ""
echo "✅ Service installed!"
echo ""
echo "📋 Management commands:"
echo ""
echo "  Start bot:   sudo systemctl start binance-trading-bot"
echo "  Stop bot:    sudo systemctl stop binance-trading-bot"
echo "  Restart bot: sudo systemctl restart binance-trading-bot"
echo "  Status:      sudo systemctl status binance-trading-bot"
echo "  Enable:      sudo systemctl enable binance-trading-bot  # Auto-start on boot"
echo "  View logs:   sudo journalctl -u binance-trading-bot -f"
echo ""
echo "💡 Recommended: Enable auto-start on boot"
echo "   sudo systemctl enable binance-trading-bot"
echo ""

