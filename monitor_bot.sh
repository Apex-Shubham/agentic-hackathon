#!/bin/bash
###############################################################################
# Monitor Trading Bot Status
# Shows current bot status, recent logs, and health metrics
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📊 Trading Bot Status Monitor"
echo "=============================="
echo ""

# Check if bot is running
if pgrep -f "run_with_restart.py\|main.py" > /dev/null; then
    echo "✅ Bot Status: RUNNING"
    BOT_PID=$(pgrep -f "run_with_restart.py" | head -1)
    if [ ! -z "$BOT_PID" ]; then
        echo "   PID: $BOT_PID"
        # Show uptime
        START_TIME=$(ps -p $BOT_PID -o lstart= 2>/dev/null || echo "Unknown")
        echo "   Started: $START_TIME"
    fi
else
    echo "❌ Bot Status: NOT RUNNING"
fi

echo ""
echo "📈 Recent Performance"
echo "---------------------"

if [ -f "logs/performance.jsonl" ]; then
    # Get last 5 performance snapshots
    tail -5 logs/performance.jsonl | python3 -c "
import json
import sys
for line in sys.stdin:
    if line.strip():
        try:
            data = json.loads(line)
            value = data.get('portfolio_value', 0)
            return_pct = data.get('total_return_percent', 0)
            drawdown = data.get('drawdown_percent', 0)
            timestamp = data.get('timestamp', '')[:19].replace('T', ' ')
            print(f\"  {timestamp} | Value: \${value:,.2f} | Return: {return_pct:+.2f}% | Drawdown: {drawdown:.2f}%\")
        except:
            pass
" || echo "  (No valid data)"
else
    echo "  No performance data yet"
fi

echo ""
echo "📝 Recent Trades"
echo "----------------"

if [ -f "logs/trades.jsonl" ]; then
    tail -5 logs/trades.jsonl | python3 -c "
import json
import sys
for line in sys.stdin:
    if line.strip():
        try:
            data = json.loads(line)
            symbol = data.get('symbol', '?')
            side = data.get('side', '?')
            pnl = data.get('pnl_percent', 0)
            timestamp = data.get('timestamp', '')[:19].replace('T', ' ')
            print(f\"  {timestamp} | {symbol} {side} | PnL: {pnl:+.2f}%\")
        except:
            pass
" || echo "  (No trades yet)"
else
    echo "  No trades yet"
fi

echo ""
echo "⚠️  Recent Errors"
echo "-----------------"

if [ -f "logs/errors.jsonl" ]; then
    ERROR_COUNT=$(wc -l < logs/errors.jsonl 2>/dev/null || echo "0")
    if [ "$ERROR_COUNT" -gt 0 ]; then
        tail -3 logs/errors.jsonl | python3 -c "
import json
import sys
for line in sys.stdin:
    if line.strip():
        try:
            data = json.loads(line)
            err_type = data.get('error_type', '?')
            err_msg = data.get('error_message', '?')[:80]
            timestamp = data.get('timestamp', '')[:19].replace('T', ' ')
            print(f\"  {timestamp} | {err_type}: {err_msg}\")
        except:
            pass
" || echo "  (Unable to parse errors)"
    else
        echo "  ✅ No errors!"
    fi
else
    echo "  ✅ No errors!"
fi

echo ""
echo "📁 Log Files"
echo "------------"
echo "  Performance: logs/performance.jsonl"
echo "  Trades: logs/trades.jsonl"
echo "  Decisions: logs/decisions.jsonl"
echo "  Errors: logs/errors.jsonl"
echo "  Assessments: logs/assessments.jsonl"
echo ""
echo "💡 To view live logs:"
echo "  tail -f logs/performance.jsonl"
echo "  tail -f logs/trades.jsonl"
echo ""

