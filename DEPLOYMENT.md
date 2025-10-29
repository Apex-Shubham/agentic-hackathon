# 🚀 Trading Bot Deployment Guide

This guide helps you deploy the bot for continuous 14-day operation.

## 📋 Pre-Deployment Checklist

- [ ] API keys configured in `.env` file
- [ ] Virtual environment created (`./deploy.sh`)
- [ ] Dependencies installed
- [ ] Configuration validated
- [ ] Test run successful (optional)

## 🔧 Quick Start

### Step 1: Initial Setup

```bash
# Run deployment script (one-time setup)
./deploy.sh
```

This will:
- Check Python version
- Create/activate virtual environment
- Install all dependencies
- Validate configuration
- Create necessary directories

### Step 2: Choose Deployment Method

## 🖥️ Deployment Options

### Option 1: Direct Run (Testing)

**Best for:** Testing, development, short runs

```bash
source venv/bin/activate
python3 main.py
```

### Option 2: Auto-Restart Script (Recommended)

**Best for:** macOS, local machines, simple deployment

```bash
# Start bot
./start_bot.sh

# Stop bot (in another terminal)
./stop_bot.sh

# Monitor status
./monitor_bot.sh
```

**Features:**
- ✅ Auto-restarts on crashes
- ✅ Exponential backoff on failures
- ✅ Up to 100 restart attempts
- ✅ Graceful shutdown on Ctrl+C

### Option 3: Background with nohup (Production)

**Best for:** Remote servers, long-term deployment

```bash
# Start in background
nohup ./start_bot.sh > logs/bot_output.log 2>&1 &

# Check if running
ps aux | grep run_with_restart.py

# View live logs
tail -f logs/bot_output.log

# Stop (find PID first)
./stop_bot.sh
```

### Option 4: Systemd Service (Linux Production)

**Best for:** Linux VPS, cloud servers, auto-start on boot

```bash
# Deploy as system service (requires sudo)
sudo ./deploy_as_service.sh

# Enable auto-start on boot
sudo systemctl enable binance-trading-bot

# Start the service
sudo systemctl start binance-trading-bot

# Check status
sudo systemctl status binance-trading-bot

# View logs
sudo journalctl -u binance-trading-bot -f

# Stop
sudo systemctl stop binance-trading-bot
```

**Benefits:**
- ✅ Auto-starts on server reboot
- ✅ Automatic restart on crashes
- ✅ Logs to system journal
- ✅ Resource limits (memory, file handles)
- ✅ Runs as your user (not root)

### Option 5: PM2 (Alternative Process Manager)

```bash
# Install PM2 globally
npm install -g pm2

# Start bot
pm2 start run_with_restart.py --name trading-bot --interpreter venv/bin/python3

# Auto-start on boot
pm2 startup
pm2 save

# Monitor
pm2 status
pm2 logs trading-bot
pm2 monit

# Stop
pm2 stop trading-bot
```

## 📊 Monitoring

### Quick Status Check

```bash
./monitor_bot.sh
```

Shows:
- Bot running status
- Recent performance metrics
- Recent trades
- Recent errors

### View Logs

```bash
# Performance metrics
tail -f logs/performance.jsonl

# All trades
tail -f logs/trades.jsonl

# Trading decisions
tail -f logs/decisions.jsonl

# Market assessments
tail -f logs/assessments.jsonl

# Errors only
tail -f logs/errors.jsonl
```

### Check Bot Process

```bash
# Find bot process
ps aux | grep run_with_restart.py

# Or
pgrep -f run_with_restart.py
```

## 🔒 Production Best Practices

### 1. Resource Monitoring

Monitor:
- **CPU usage** (should be < 10% when idle)
- **Memory usage** (should be stable, < 500MB)
- **Disk space** (logs grow ~10MB/day)

```bash
# Check resource usage
top -p $(pgrep -f run_with_restart.py)
```

### 2. Network Connectivity

Ensure stable internet:
- Use wired connection when possible
- Monitor for disconnections
- Test API connectivity before deploying

```bash
# Test API connection
python3 check_balance.py
```

### 3. Log Rotation

Prevent log files from growing too large:

```bash
# Manual rotation
mv logs/performance.jsonl logs/performance.jsonl.old
touch logs/performance.jsonl
```

Or install `logrotate` (Linux):
```bash
# Create logrotate config
sudo nano /etc/logrotate.d/trading-bot
```

### 4. Backup Strategy

Backup important logs before competition ends:
- `logs/trades.jsonl` - Trade history
- `logs/performance.jsonl` - Performance metrics
- `logs/decisions.jsonl` - Decision log

### 5. Alerts & Notifications

Set up alerts for:
- Bot crashes (check logs/errors.jsonl)
- High drawdown (config threshold)
- API failures

```bash
# Simple email alert on crash (example)
echo "Bot crashed!" | mail -s "Trading Bot Alert" your@email.com
```

## 🛠️ Troubleshooting

### Bot Won't Start

1. Check configuration:
```bash
python3 -c "from config import validate_config; validate_config()"
```

2. Check API keys:
```bash
grep -E "BINANCE_TESTNET_API_KEY|OPENROUTER_API_KEY" .env
```

3. Check Python version:
```bash
python3 --version  # Should be 3.10+
```

### Bot Keeps Restarting

1. Check error logs:
```bash
tail -50 logs/errors.jsonl
```

2. Check if ports/APIs are accessible:
```bash
curl https://testnet.binancefuture.com/api/v3/ping
```

3. Verify environment:
```bash
source venv/bin/activate
python3 -c "import binance; import requests; print('OK')"
```

### High Memory Usage

1. Check for memory leaks:
```bash
ps aux | grep python | grep trading
```

2. Restart periodically:
```bash
./stop_bot.sh
sleep 10
./start_bot.sh
```

### Connection Issues

1. Test API connectivity:
```bash
python3 check_balance.py
```

2. Check network:
```bash
ping testnet.binancefuture.com
```

## 📅 14-Day Competition Checklist

### Day 1:
- [ ] Deploy bot
- [ ] Verify first trades
- [ ] Set up monitoring
- [ ] Test stop/start functionality

### Day 2-13:
- [ ] Daily status check (`./monitor_bot.sh`)
- [ ] Review logs for errors
- [ ] Monitor performance metrics
- [ ] Backup logs weekly

### Day 14:
- [ ] Final status check
- [ ] Generate final report
- [ ] Backup all logs
- [ ] Verify all trades executed
- [ ] Calculate final performance

## 🔄 Maintenance Commands

```bash
# View all processes
ps aux | grep python

# Stop bot
./stop_bot.sh

# Start bot
./start_bot.sh

# Monitor status
./monitor_bot.sh

# Check logs size
du -sh logs/

# View recent errors
tail -20 logs/errors.jsonl

# Count total trades
wc -l logs/trades.jsonl
```

## 📞 Support

If issues persist:
1. Check `logs/errors.jsonl` for errors
2. Review `logs/decisions.jsonl` for trading activity
3. Verify API keys are valid
4. Ensure network connectivity
5. Check system resources (CPU, memory, disk)

## 🎯 Recommended Deployment

**For 14-day competition, use:**

**Mac/Local:**
```bash
nohup ./start_bot.sh > logs/bot_output.log 2>&1 &
```

**Linux VPS:**
```bash
sudo ./deploy_as_service.sh
sudo systemctl enable binance-trading-bot
sudo systemctl start binance-trading-bot
```

Both ensure:
- ✅ Continuous operation
- ✅ Auto-restart on crashes
- ✅ Survives system reboots (systemd)
- ✅ Proper logging
- ✅ Easy monitoring

---

**Good luck with the competition! 🚀**

