#!/bin/bash
###############################################################################
# Stop Trading Bot
# Gracefully stops the running bot
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🛑 Stopping trading bot..."

# Find and kill bot processes
BOT_PIDS=$(pgrep -f "run_with_restart.py\|main.py" || true)

if [ -z "$BOT_PIDS" ]; then
    echo "ℹ️  No bot process found running"
    exit 0
fi

echo "📋 Found bot processes: $BOT_PIDS"

# Try graceful shutdown first (SIGTERM)
for pid in $BOT_PIDS; do
    echo "Sending SIGTERM to PID $pid..."
    kill -TERM $pid 2>/dev/null || true
done

# Wait a bit for graceful shutdown
sleep 5

# Check if processes are still running
REMAINING=$(pgrep -f "run_with_restart.py\|main.py" || true)

if [ ! -z "$REMAINING" ]; then
    echo "⚠️  Some processes didn't stop gracefully. Force killing..."
    for pid in $REMAINING; do
        echo "Sending SIGKILL to PID $pid..."
        kill -9 $pid 2>/dev/null || true
    done
fi

# Final check
sleep 1
if pgrep -f "run_with_restart.py\|main.py" > /dev/null; then
    echo "❌ Failed to stop all bot processes"
    exit 1
else
    echo "✅ Bot stopped successfully"
fi

