# ⚡ Quick Deployment Guide

## 🚀 Start Bot in 3 Steps

### 1. One-time Setup
```bash
./deploy.sh
```

### 2. Start Bot (choose one method)

**Option A: Simple Start (foreground)**
```bash
./start_bot.sh
```

**Option B: Background Start (recommended)**
```bash
nohup ./start_bot.sh > logs/bot_output.log 2>&1 &
```

**Option C: Systemd Service (Linux only)**
```bash
sudo ./deploy_as_service.sh
sudo systemctl enable binance-trading-bot
sudo systemctl start binance-trading-bot
```

### 3. Monitor Status
```bash
./monitor_bot.sh
```

## 🛑 Stop Bot
```bash
./stop_bot.sh
```

## 📊 Quick Commands

```bash
# Check if running
ps aux | grep run_with_restart.py

# View live logs
tail -f logs/performance.jsonl
tail -f logs/trades.jsonl

# View errors
tail -20 logs/errors.jsonl

# Full status
./monitor_bot.sh
```

## ✅ Verify Deployment

1. Check bot is running:
   ```bash
   pgrep -f run_with_restart.py
   ```

2. Check recent trades:
   ```bash
   tail -5 logs/trades.jsonl
   ```

3. Check for errors:
   ```bash
   wc -l logs/errors.jsonl  # Should be low
   ```

## 📝 Full Documentation

See `DEPLOYMENT.md` for detailed instructions.

