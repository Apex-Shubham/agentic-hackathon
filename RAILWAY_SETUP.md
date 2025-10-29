# 🚂 Railway Deployment - Step by Step

## ✅ Step 1: Push to GitHub (Already Done!)

Your code is committed. Push to GitHub:

```bash
git push origin main
```

Or if you haven't set up the remote yet:
```bash
# Create repo on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/trading-bot.git
git push -u origin main
```

---

## ✅ Step 2: Deploy to Railway

### 2a. Create Railway Account
1. Go to https://railway.app
2. Click "Login" → "Start a New Project"
3. Sign up with **GitHub** (easiest method)

### 2b. Connect Your Repository
1. Click **"Deploy from GitHub repo"**
2. Authorize Railway to access your GitHub
3. Select your **trading-bot** repository
4. Click **"Deploy Now"**

Railway will automatically:
- Detect it's a Python project
- Install dependencies from `requirements.txt`
- Run your `Procfile` (which runs `run_with_restart.py`)

---

## ✅ Step 3: Add Environment Variables

**CRITICAL**: Without these, your bot won't work!

### In Railway Dashboard:
1. Click on your project
2. Go to **"Variables"** tab
3. Click **"+ New Variable"** for each:

```
BINANCE_TESTNET_API_KEY=your_api_key_here
BINANCE_TESTNET_API_SECRET=your_api_secret_here
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=Qwen/Qwen2.5 72B Instruct
COMPETITION_START_DATE=2025-10-29T00:00:00+00:00
COMPETITION_DURATION_DAYS=14
INITIAL_CAPITAL=5000
TRADING_ASSETS=BTCUSDT,SOLUSDT
CHECK_INTERVAL_SECONDS=60
MIN_CONFIDENCE=70
MIN_CONFIDENCE_VOLATILE=60
```

**Copy all variables from your `.env` file** and add them to Railway!

### Quick Copy Script:
```bash
# On your Mac, run this to see all your env vars:
cd /Users/shubhamrathod/Desktop/123
cat .env | grep -v "^#" | grep "="
```

Copy the output and paste each line into Railway Variables.

---

## ✅ Step 4: Verify Deployment

### Check Logs:
1. In Railway dashboard → Click your service
2. Go to **"Logs"** tab
3. You should see:
   ```
   🤖 ENHANCED AUTONOMOUS AI TRADING BOT - INITIALIZING
   ✅ Configuration validated
   💰 Fetched Balance from Binance: $X,XXX.XX
   🚀 STARTING ENHANCED AUTONOMOUS TRADING
   ```

### Check Bot is Running:
- Logs should update every 60 seconds (CHECK_INTERVAL_SECONDS)
- Look for trade execution messages
- Check Binance testnet for new positions

---

## ✅ Step 5: Monitor Your Bot

### Railway Dashboard:
- **Logs Tab**: Real-time streaming logs
- **Metrics Tab**: CPU, Memory usage
- **Settings Tab**: Environment variables

### Via Binance Testnet:
1. Login to https://testnet.binancefuture.com
2. Check Futures positions
3. Verify trades are executing

---

## 🔧 Troubleshooting

### Bot Not Starting:
1. **Check Logs** → Look for error messages
2. **Verify Environment Variables** → All required vars set?
3. **Check Python Version** → Railway should auto-detect 3.10+

### No Trades Executing:
1. Check **logs/errors.jsonl** in Railway (if accessible)
2. Verify API keys are correct
3. Check confidence thresholds aren't too high
4. Verify `CHECK_INTERVAL_SECONDS` is reasonable (60s recommended)

### Bot Keeps Restarting:
1. Check crash logs in Railway
2. Look for specific error messages
3. Auto-restart wrapper should handle crashes, but check root cause

### Environment Variables Not Working:
- Make sure no spaces around `=` in Railway variables
- Check variable names match exactly (case-sensitive)
- Redeploy after adding variables (Railway auto-restarts)

---

## 💰 Railway Free Tier

**What You Get:**
- $5 credit/month (free forever)
- ~500 hours of runtime/month
- Perfect for 14-day competition

**14-day competition = ~336 hours** ✅ Fits in free tier!

**If you need more:**
- Upgrade temporarily for ~$5/month
- Or switch to Oracle Cloud (completely free)

---

## 📊 Useful Railway Commands (CLI Optional)

```bash
# Install Railway CLI (optional)
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# View logs
railway logs

# Check status
railway status

# Add variable
railway variables set BINANCE_TESTNET_API_KEY=your_key
```

---

## ✅ Next Steps

1. ✅ Push code to GitHub
2. ✅ Create Railway account & connect GitHub
3. ✅ Deploy repository
4. ✅ Add all environment variables
5. ✅ Monitor logs and verify bot is trading
6. ✅ Check Binance testnet for positions

**Your bot will now run 24/7 even when your laptop is off!** 🚀

---

## 🎯 Quick Checklist

- [ ] Code pushed to GitHub
- [ ] Railway account created
- [ ] Repository connected
- [ ] Deployment successful
- [ ] All environment variables added
- [ ] Bot showing in logs
- [ ] Trades executing on Binance testnet

**Need help?** Check Railway logs for specific error messages!

