# ☁️ Free Cloud Deployment Guide

Deploy your trading bot to run 24/7 for free, even when your laptop is off.

## 🎯 Best Free Options (2024)

### Option 1: **Railway.app** ⭐ RECOMMENDED
- ✅ **Free**: $5 credit/month (500 hours free)
- ✅ Simple setup (GitHub integration)
- ✅ Auto-restarts on crash
- ✅ Persistent logs

### Option 2: **Render.com**
- ✅ **Free**: Unlimited (with restrictions)
- ✅ Simple deployment
- ⚠️ Spins down after 15min inactivity (wakes on HTTP)
- ✅ Good for testing

### Option 3: **PythonAnywhere**
- ✅ **Free**: Always-on task allowed
- ✅ Web-based console
- ✅ Perfect for Python bots

### Option 4: **Oracle Cloud Free Tier** (Best for 24/7)
- ✅ **Free**: Always-free ARM instances
- ✅ Full VPS (4 CPU cores, 24GB RAM)
- ✅ No time limits
- ⚠️ Requires credit card (not charged)

---

## 🚀 Quick Start: Railway.app (Recommended)

### Step 1: Prepare Repository

```bash
# Make sure code is committed
cd /Users/shubhamrathod/Desktop/123
git init  # if not already
git add .
git commit -m "Trading bot ready for deployment"
```

Create `.railwayignore`:
```
venv/
__pycache__/
*.pyc
logs/
.DS_Store
.env
```

### Step 2: Create Railway Account

1. Go to https://railway.app
2. Sign up with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Connect your repository

### Step 3: Add Environment Variables

In Railway dashboard → Variables tab, add:

```bash
BINANCE_TESTNET_API_KEY=your_key
BINANCE_TESTNET_API_SECRET=your_secret
OPENROUTER_API_KEY=your_key
COMPETITION_START_DATE=2025-10-29T00:00:00+00:00
COMPETITION_DURATION_DAYS=14
INITIAL_CAPITAL=5000
TRADING_ASSETS=BTCUSDT,SOLUSDT
# ... (copy all from your .env file)
```

### Step 4: Configure Build & Start

Railway will auto-detect Python, but create `Procfile`:

```bash
worker: python run_with_restart.py
```

Railway will auto-detect and run this!

### Step 5: Deploy

- Railway auto-deploys on git push
- Or click "Deploy" in dashboard
- View logs in Railway dashboard

---

## 🌐 Quick Start: Render.com (Simple Alternative)

### Step 1: Create `render.yaml`:

```yaml
services:
  - type: worker
    name: trading-bot
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python run_with_restart.py
    envVars:
      - key: BINANCE_TESTNET_API_KEY
        sync: false
      - key: BINANCE_TESTNET_API_SECRET
        sync: false
      - key: OPENROUTER_API_KEY
        sync: false
      # ... add all your env vars
```

### Step 2: Deploy

1. Go to https://render.com
2. Sign up
3. New → Blueprint (or Web Service)
4. Connect GitHub repo
5. Add environment variables
6. Deploy

**Note**: Free tier spins down after inactivity. Add a health check ping if needed.

---

## 🖥️ Quick Start: PythonAnywhere (Easiest)

### Step 1: Create Account

1. Go to https://www.pythonanywhere.com
2. Sign up for free account

### Step 2: Upload Code

```bash
# In your local terminal
cd /Users/shubhamrathod/Desktop/123
tar -czf bot.tar.gz *.py analytics/ config.py requirements.txt

# Upload via PythonAnywhere dashboard → Files
```

### Step 3: Set Up Always-On Task

1. PythonAnywhere → Tasks
2. Create new "Always-on task"
3. Command: `python3 /home/yourusername/bot/run_with_restart.py`
4. Click "Start"

### Step 4: Add Environment Variables

1. Files → `.env`
2. Paste your environment variables

### Step 5: Install Dependencies

PythonAnywhere → Bash console:
```bash
pip3.10 install --user -r requirements.txt
```

---

## 🏗️ Quick Start: Oracle Cloud Free Tier (Most Powerful)

### Step 1: Create Account

1. Go to https://www.oracle.com/cloud/free/
2. Sign up (requires credit card - won't be charged)
3. Create free ARM instance (Ampere A1)

### Step 2: SSH into Instance

```bash
ssh ubuntu@your-instance-ip
```

### Step 3: Install Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

### Step 4: Clone/Upload Bot

```bash
# Option A: If using git
git clone your-repo-url
cd your-repo

# Option B: Use SCP to upload
# (from your laptop)
scp -r /Users/shubhamrathod/Desktop/123 ubuntu@your-instance-ip:~/
```

### Step 5: Set Up Bot

```bash
cd ~/123
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
nano .env
# Paste your environment variables, save (Ctrl+X, Y, Enter)
```

### Step 6: Deploy as Systemd Service

```bash
# Run the deployment script
sudo ./deploy_as_service.sh

# Or manually create service (if script doesn't work)
sudo nano /etc/systemd/system/trading-bot.service
```

Paste:
```ini
[Unit]
Description=Binance Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/123
Environment="PATH=/home/ubuntu/123/venv/bin"
ExecStart=/home/ubuntu/123/venv/bin/python3 /home/ubuntu/123/run_with_restart.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
sudo systemctl status trading-bot
```

---

## ✅ Verification Checklist

After deployment, verify:

1. **Bot is running:**
   ```bash
   # Railway/Render: Check dashboard logs
   # PythonAnywhere: Check Tasks page
   # Oracle: ssh in and run: sudo systemctl status trading-bot
   ```

2. **Trades are executing:**
   - Check `logs/trades.jsonl` in dashboard/files
   - Monitor Binance testnet positions

3. **Logs are updating:**
   - View logs in dashboard/console

---

## 🎯 Recommended: Railway.app

**Why Railway?**
- ✅ Easiest setup
- ✅ Auto-deploys from Git
- ✅ Persistent storage
- ✅ Good free tier ($5/month = 500 hours)
- ✅ Reliable uptime

**Quick Railway Setup:**
```bash
# 1. Install Railway CLI (optional but helpful)
npm install -g @railway/cli

# 2. Login
railway login

# 3. Initialize project
railway init

# 4. Link to existing project or create new
railway link

# 5. Add environment variables
railway variables set BINANCE_TESTNET_API_KEY=your_key
railway variables set BINANCE_TESTNET_API_SECRET=your_secret
# ... add all others

# 6. Deploy
railway up
```

---

## 📊 Monitoring Cloud Deployment

### Railway:
- Dashboard → Project → Logs
- Real-time log streaming

### Render:
- Dashboard → Service → Logs
- Set up alerts

### PythonAnywhere:
- Dashboard → Tasks → View logs
- Files → `logs/` directory

### Oracle Cloud:
```bash
# SSH into instance
ssh ubuntu@your-ip

# View logs
sudo journalctl -u trading-bot -f

# Or view bot logs
tail -f ~/123/logs/trades.jsonl
```

---

## 🆘 Troubleshooting

**Bot not starting:**
- Check environment variables are set
- Verify Python version (3.10+)
- Check logs for errors

**Trades not executing:**
- Verify API keys are correct
- Check network connectivity
- Review `logs/errors.jsonl`

**Bot crashing:**
- Auto-restart wrapper should handle this
- Check logs for crash reasons
- Verify all dependencies installed

---

## 💰 Cost Summary

| Service | Free Tier | Limits |
|---------|-----------|--------|
| Railway | $5/month credit | 500 hours/month |
| Render | Unlimited | Spins down after inactivity |
| PythonAnywhere | Free | 1 always-on task |
| Oracle Cloud | Always free | 2 ARM instances forever |

**Best for 14-day competition:** Oracle Cloud (unlimited) or Railway ($5 credit = plenty for 14 days)

---

**Need help?** Check the deployment logs and error messages!

