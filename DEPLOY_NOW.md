# 🚀 Quick Deployment Guide - Dockploy

## ✅ Prerequisites (Already Done!)
- ✅ Code pushed to GitHub
- ✅ Dockerfile created
- ✅ .dockerignore configured
- ✅ All dependencies in requirements.txt

---

## Step-by-Step Deployment

### Step 1: Create Dockploy Account
1. Go to **https://dockploy.com** (or search "Dockploy" for official site)
2. Click **"Sign Up"** or **"Get Started"**
3. Sign up with **GitHub** (easiest - connects to your repo)

### Step 2: Connect Your Repository
1. After login, click **"New Project"** or **"Deploy"**
2. Select **"Deploy from GitHub"**
3. Authorize Dockploy to access your GitHub
4. Find and select: **`Apex-Shubham/agentic-hackathon`**
5. Click **"Connect"** or **"Select"**

### Step 3: Configure Docker Build
Dockploy should auto-detect your Dockerfile. Verify:
- **Dockerfile Path**: `Dockerfile` (root directory)
- **Build Context**: `.` (current directory)
- **Service Type**: **Worker** or **Background Job** (not Web Service)

### Step 4: Add Environment Variables ⚠️ **CRITICAL**

In Dockploy dashboard → **Environment Variables** or **Config** tab:

Add ALL these variables (copy from your `.env` file):

```bash
# Binance API
BINANCE_TESTNET_API_KEY=your_api_key_here
BINANCE_TESTNET_API_SECRET=your_api_secret_here

# OpenRouter API
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=Qwen/Qwen2.5 72B Instruct
OPENROUTER_API_URL=https://openrouter.ai/api/v1/chat/completions
OPENROUTER_TEMPERATURE=0.7
OPENROUTER_MAX_TOKENS=2000
OPENROUTER_TIMEOUT=30
OPENROUTER_REFERER=http://localhost
OPENROUTER_TITLE=AI Trading Bot

# Competition Settings
COMPETITION_START_DATE=2025-10-29T00:00:00+00:00
COMPETITION_DURATION_DAYS=14
CHECK_INTERVAL_SECONDS=60

# Trading Configuration
INITIAL_CAPITAL=5000
TRADING_ASSETS=BTCUSDT,SOLUSDT
MIN_CONFIDENCE=70
MIN_CONFIDENCE_VOLATILE=60

# Position Sizing (Fixed Dollar Amounts)
HIGH_CONFIDENCE_POSITION_SIZE=1200.0
MEDIUM_CONFIDENCE_POSITION_SIZE=1000.0
LOW_CONFIDENCE_POSITION_SIZE=800.0
MAX_POSITION_SIZE=0.30

# Risk Limits
MAX_OPEN_POSITIONS=5
MAX_POSITIONS_PER_SYMBOL=2
MAX_CORRELATED_POSITIONS=3
MAX_PORTFOLIO_RISK=0.15
MAX_LEVERAGE=5
MAX_DRAWDOWN=0.40

# Leverage
BASE_LEVERAGE=2
HIGH_CONFIDENCE_LEVERAGE=3
LEVERAGE_THRESHOLD=80

# Volatility Trading
ENABLE_VOLATILITY_TRADING=true
VOLATILITY_MIN_ATR_RATIO=0.01
SCALP_MODE_THRESHOLD=0.03
SCALP_POSITION_SIZE=0.05
SCALP_STOP_LOSS=0.02
SCALP_TAKE_PROFIT=0.04

# Logging
LOG_DIR=logs
TRADE_LOG_FILE=logs/trades.jsonl
DECISION_LOG_FILE=logs/decisions.jsonl
PERFORMANCE_LOG_FILE=logs/performance.jsonl
ERROR_LOG_FILE=logs/errors.jsonl
ASSESSMENT_LOG_FILE=logs/assessments.jsonl
```

**Quick Copy Command** (on your Mac):
```bash
cd /Users/shubhamrathod/Desktop/123
cat .env | grep -v "^#" | grep "=" | grep -v "^$"
```

Copy each line and paste into Dockploy environment variables.

### Step 5: Deploy
1. Click **"Deploy"** or **"Build & Deploy"** in Dockploy
2. Monitor build logs:
   - Docker image building
   - Installing Python dependencies
   - Starting container
3. Wait for deployment to complete (usually 2-5 minutes)

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
- Logs update every 60 seconds
- Look for "EXECUTING LONG/SHORT" messages
- Check Binance testnet: https://testnet.binancefuture.com
- Verify positions are opening

---

## 🔧 Troubleshooting

### Build Fails?
- Check Dockerfile is in root directory
- Verify all files are pushed to GitHub
- Check build logs for specific errors

### Bot Not Starting?
- Verify ALL environment variables are set correctly
- Check logs for missing variables
- Ensure API keys are valid

### No Trades?
- Verify confidence thresholds are reasonable (70% minimum)
- Check API keys are correct
- Look for rejection messages in logs
- Verify `CHECK_INTERVAL_SECONDS` is set (60s recommended)

### Container Crashes?
- Check crash logs for specific errors
- Verify all dependencies installed (Flask, pandas, etc.)
- Check resource limits

---

## 📊 Monitoring

### Dockploy Dashboard:
- **Logs Tab**: Real-time log streaming
- **Metrics Tab**: CPU, Memory usage
- **Settings Tab**: Environment variables

### Binance Testnet:
- Login: https://testnet.binancefuture.com
- Check Futures positions
- Monitor portfolio value

---

## ✅ Checklist

- [ ] Dockploy account created
- [ ] GitHub repository connected
- [ ] Docker build configured
- [ ] ALL environment variables added
- [ ] Deployment successful
- [ ] Bot showing in logs
- [ ] Trades executing on Binance testnet

---

## 🔄 Updates

To update your bot:
1. Make changes locally
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```
3. Dockploy should auto-redeploy (if enabled)
   - Or manually click "Redeploy" in dashboard

---

## 💡 Tips

1. **Keep logs tab open** to monitor bot activity
2. **Double-check API keys** - incorrect keys = no trades
3. **Free tier limits** - Check Dockploy's free tier for any restrictions
4. **Monitor Binance** - Verify trades are actually executing

---

**Your bot will now run 24/7 on Dockploy! 🚀**

Need help? Check Dockploy logs for specific error messages!

