# ⚡ Quick Start Guide

## 🚀 Get Started in 5 Minutes

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Environment
```bash
cp env.example .env
nano .env  # Add your API keys
```

### 3. Configure API Keys

**Required:**
- `BINANCE_TESTNET_API_KEY` - Get from [testnet.binancefuture.com](https://testnet.binancefuture.com)
- `BINANCE_TESTNET_API_SECRET` - Same as above
- `DEEPSEEK_API_KEY` - Get from [platform.deepseek.com](https://platform.deepseek.com)

### 4. Test Connection
```bash
python -c "from data_pipeline import DataPipeline; DataPipeline().test_connection()"
```

### 5. Run Bot
```bash
python run_with_restart.py
```

---

## 📊 Quick Commands

```bash
# Run with auto-restart (recommended)
python run_with_restart.py

# Run directly (for testing)
python main.py

# Run tests
pytest tests/ -v

# Check logs
tail -f logs/performance.jsonl

# View errors
tail -f logs/errors.jsonl
```

---

## 🛑 Stop the Bot

Press `Ctrl+C` - The bot will:
1. Close all open positions
2. Generate final report
3. Save all logs
4. Shutdown gracefully

---

## 📈 Monitor Performance

Status updates print every hour. Check:
- Portfolio value
- Total return %
- Current drawdown
- Win rate
- Sharpe ratio

---

## ⚠️ Important Notes

1. **Never interrupt** during first 2 hours (building positions)
2. **Monitor logs** but don't intervene manually
3. **Trust the system** - circuit breakers protect you
4. **Stable internet** required for 14 days
5. **One violation** = instant disqualification

---

## 🆘 Quick Troubleshooting

| Error | Solution |
|-------|----------|
| `Invalid API Key` | Check API keys in `.env` |
| `Module not found` | Run `pip install -r requirements.txt` |
| `Insufficient margin` | Request more testnet funds |
| `Connection timeout` | Check internet connection |

---

## 📞 Need Help?

1. Check `README.md` for detailed docs
2. Review `logs/errors.jsonl` for specific errors
3. Run tests: `pytest tests/ -v`

---

**Ready to compete? Let's go! 🚀**

