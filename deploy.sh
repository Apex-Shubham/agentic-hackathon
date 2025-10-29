#!/bin/bash
###############################################################################
# Trading Bot Deployment Script
# Sets up the bot for continuous 14-day operation
###############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Trading Bot Deployment"
echo "=========================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python version: $PYTHON_VERSION"

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Creating .env from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "⚠️  Please edit .env and add your API keys before running again"
        exit 1
    else
        echo "❌ .env.example not found either"
        exit 1
    fi
fi

# Check virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

# Create logs directory if it doesn't exist
mkdir -p logs

# Validate configuration
echo "✅ Validating configuration..."
python3 -c "from config import validate_config; validate_config()" || {
    echo "❌ Configuration validation failed"
    exit 1
}

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo ""
echo "Option 1: Run with auto-restart wrapper (recommended)"
echo "  ./start_bot.sh"
echo ""
echo "Option 2: Run directly (for testing)"
echo "  source venv/bin/activate"
echo "  python3 main.py"
echo ""
echo "Option 3: Run in background with nohup"
echo "  nohup ./start_bot.sh > logs/bot_output.log 2>&1 &"
echo ""
echo "Option 4: Deploy as systemd service (Linux)"
echo "  sudo ./deploy_as_service.sh"
echo ""

