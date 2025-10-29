# 🐳 Dockploy Deployment Guide

Complete guide to deploy your trading bot on Dockploy using Docker.

## 📋 Prerequisites

- ✅ Dockerfile created (✅ Done)
- ✅ .dockerignore created (✅ Done)
- ✅ Code pushed to GitHub (✅ Done)

---

## 🚀 Step-by-Step Deployment

### Step 1: Create Dockploy Account

1. Go to **https://dockploy.com** (or search for official Dockploy site)
2. Click **"Sign Up"** or **"Get Started"**
3. Sign up with GitHub (easiest method)
4. Authorize Dockploy to access your GitHub

### Step 2: Create New Project

1. In Dockploy dashboard → Click **"New Project"** or **"Create App"**
2. Select **"Deploy from GitHub"**
3. Find and select your repository: `Apex-Shubham/agentic-hackathon`
4. Click **"Connect"** or **"Select"**

### Step 3: Configure Docker Build

Dockploy should auto-detect your Dockerfile, but verify:

- **Dockerfile Path**: `Dockerfile` (root directory)
- **Build Context**: `.` (current directory)
- **Service Type**: **Worker** or **Background Job** (not Web Service)

### Step 4: Add Environment Variables

**CRITICAL**: Your bot won't work without these!

In Dockploy dashboard → **Environment Variables** or **Config** tab:

Add all variables from your `.env` file:

```bash
BINANCE_TESTNET_API_KEY=your_api_key_here
BINANCE_TESTNET_API_SECRET=your_api_secret_here
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=Qwen/Qwen2.5 72B Instruct
OPENROUTER_API_URL=https://openrouter.ai/api/v1/chat/completions
OPENROUTER_TEMPERATURE=0.7
OPENROUTER_MAX_TOKENS=2000
OPENROUTER_TIMEOUT=30
COMPETITION_START_DATE=2025-10-29T00:00:00+00:00
COMPETITION_DURATION_DAYS=14
CHECK_INTERVAL_SECONDS=60
INITIAL_CAPITAL=5000
TRADING_ASSETS=BTCUSDT,SOLUSDT
MIN_CONFIDENCE=70
MIN_CONFIDENCE_VOLATILE=60
MAX_OPEN_POSITIONS=5
MAX_POSITIONS_PER_SYMBOL=2
MAX_LEVERAGE=5
BASE_LEVERAGE=2
HIGH_CONFIDENCE_LEVERAGE=3
# ... add ALL other variables from your .env
```

**To get all your env vars at once:**
```bash
cd /Users/shubhamrathod/Desktop/123
cat .env | grep -v "^#" | grep "=" | grep -v "^$"
```

### Step 5: Deploy

1. Click **"Deploy"** or **"Build & Deploy"**
2. Monitor build logs:
   - Building Docker image
   - Installing dependencies
   - Starting container
3. Wait for deployment to complete

### Step 6: Verify Deployment

**Check Logs Tab:**
You should see:
```
🤖 ENHANCED AUTONOMOUS AI TRADING BOT - INITIALIZING
✅ Configuration validated
💰 Fetched Balance from Binance: $X,XXX.XX
🚀 STARTING ENHANCED AUTONOMOUS TRADING
```

**Verify Bot is Trading:**
- Logs update every 60 seconds (CHECK_INTERVAL_SECONDS)
- Look for "EXECUTING LONG/SHORT" messages
- Check Binance testnet: https://testnet.binancefuture.com
- Verify positions are opening

---

## 🔧 Dockploy Configuration

### Resource Limits (Free Tier)
- Check Dockploy free tier limits
- Adjust if needed (CPU, Memory, Storage)

### Auto-Restart
- Enable auto-restart on crashes
- Your `run_with_restart.py` provides extra protection

### Health Checks
- Not needed for worker services
- Bot runs continuously

---

## 📊 Monitoring on Dockploy

### Logs Tab
- Real-time log streaming
- Filter by log level
- Download logs

### Metrics Tab
- CPU usage
- Memory usage
- Network traffic

### Settings Tab
- Environment variables
- Resource limits
- Auto-scaling (if available)

---

## 🔄 Updates & Redeployment

### Automatic (if enabled):
- Push to GitHub → Auto-redeploy

### Manual:
1. Dockploy dashboard → Your project
2. Click **"Redeploy"** or **"Rebuild"**
3. Or push new commit to trigger redeployment

---

## 🆘 Troubleshooting

### Build Fails:
- Check Dockerfile syntax
- Verify requirements.txt is valid
- Check build logs for specific errors

### Bot Not Starting:
- Verify all environment variables are set
- Check logs for configuration errors
- Ensure API keys are correct

### Container Crashes:
- Check logs for crash reason
- Verify dependencies installed correctly
- Check resource limits

### No Trades Executing:
- Verify API keys are correct
- Check confidence thresholds
- Look for rejection messages in logs
- Verify CHECK_INTERVAL_SECONDS is reasonable

---

## ✅ Checklist

- [ ] Dockploy account created
- [ ] GitHub repository connected
- [ ] Docker build configured
- [ ] All environment variables added
- [ ] Deployment successful
- [ ] Bot shows in logs
- [ ] Trades executing on Binance testnet

---

## 💡 Tips

1. **Free Tier**: Check Dockploy's free tier limits
2. **Logs**: Keep logs tab open to monitor bot
3. **Backups**: Regularly check Binance testnet positions
4. **Updates**: Push code updates to trigger auto-redeploy

**Your bot will now run 24/7 on Dockploy! 🚀**

