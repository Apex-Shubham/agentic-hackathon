#!/bin/bash
###############################################################################
# Start Trading Bot
# Starts the bot with auto-restart wrapper
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if already running
if pgrep -f "run_with_restart.py" > /dev/null; then
    echo "⚠️  Bot is already running!"
    echo "Use ./stop_bot.sh to stop it first"
    exit 1
fi

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run ./deploy.sh first"
    exit 1
fi

source venv/bin/activate

# Create logs directory
mkdir -p logs

echo "🚀 Starting trading bot..."
echo "📝 Logs will be written to logs/ directory"
echo "🛑 Press Ctrl+C to stop (or use ./stop_bot.sh)"
echo ""

# Run with auto-restart
python3 run_with_restart.py

