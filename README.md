# 🤖 Autonomous AI Trading Bot for Binance Futures

**A fully autonomous trading bot powered by Groq LLM for 14-day trading competitions**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Overview

This is a sophisticated, fully autonomous AI trading bot designed to compete in 14-day Binance Futures trading competitions. It uses Groq's hosted LLMs for intelligent decision-making, combined with advanced technical analysis, risk management, and self-healing capabilities.

### Key Features

- **🧠 AI-Powered Decisions**: Uses Groq LLM for intelligent trade analysis
- **🛡️ Advanced Risk Management**: Multi-level circuit breakers and dynamic position sizing
- **🔄 Self-Healing**: Automatic error recovery and crash resistance
- **📊 Technical Analysis**: 15+ indicators across multiple timeframes
- **📈 Real-Time Monitoring**: Comprehensive logging and performance tracking
- **⚡ Fully Autonomous**: Runs for 14 days without manual intervention

### Performance Targets

- **Minimum Viable**: +50% returns, <30% drawdown
- **Competitive**: +100-150% returns, <25% drawdown
- **Top Tier**: +200%+ returns, <20% drawdown

---

## 🏗️ Architecture

### Module Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         MAIN ORCHESTRATOR                        │
│                          (main.py)                               │
└─────────────────────────────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
┌───────▼────────┐      ┌────────▼────────┐      ┌────────▼────────┐
│ Data Pipeline  │      │ Market Analyzer │      │ Groq Agent      │
│ • Real-time    │      │ • Trade Setups  │      │ • AI Decisions  │
│ • Indicators   │      │ • Confidence    │      │ • Validation    │
└───────┬────────┘      └────────┬────────┘      └────────┬────────┘
        │                        │                         │
        └────────────────────────┼─────────────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
        ┌───────▼────────┐  ┌───▼────────┐  ┌──▼──────────┐
        │ Risk Manager   │  │  Executor  │  │   Logger    │
        │ • Drawdown     │  │ • Orders   │  │ • Reports   │
        │ • Circuit Br.  │  │ • Positions│  │ • Metrics   │
        └───────┬────────┘  └───┬────────┘  └──┬──────────┘
                │               │               │
                └───────────────┼───────────────┘
                                │
                        ┌───────▼────────┐
                        │ Health Monitor │
                        │ • Auto-Heal    │
                        │ • Recovery     │
                        └────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Binance Futures Testnet account
- Groq API key
- Stable internet connection

### 1. Clone/Download the Repository

```bash
cd /path/to/your/directory
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example environment file
cp env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Required Configuration:**

```bash
# Binance Futures Testnet
BINANCE_TESTNET_API_KEY=your_binance_testnet_api_key
BINANCE_TESTNET_API_SECRET=your_binance_testnet_api_secret

# Groq API
GROQ_API_KEY=your_groq_api_key

# Competition Settings
COMPETITION_START_DATE=2024-11-01T00:00:00Z
COMPETITION_DURATION_DAYS=14
INITIAL_CAPITAL=100000
```

### 4. Get API Keys

#### **Binance Futures Testnet**

1. Go to [Binance Futures Testnet](https://testnet.binancefuture.com/)
2. Create account or login
3. Generate API keys from account settings
4. Save API Key and Secret Key

#### **Groq API**

1. Visit [Groq Cloud](https://console.groq.com/)
2. Create an API key
3. Save the key securely

### 5. Run Tests (Optional but Recommended)

```bash
pytest tests/ -v
```

### 6. Start the Bot

**Option A: Direct Run (for testing)**
```bash
python main.py
```

**Option B: With Auto-Restart (Recommended for competition)**
```bash
python run_with_restart.py
```

---

## 📋 Detailed Setup Guide

### Binance Futures Testnet Setup

1. **Create Account**: Visit [testnet.binancefuture.com](https://testnet.binancefuture.com)
2. **Generate Test Funds**: 
   - Click on your profile
   - Request test USDT (usually 100,000 USDT)
3. **Create API Keys**:
   - Go to API Management
   - Create New Key
   - **Important**: Enable "Futures" permissions
   - Save both API Key and Secret Key
4. **Verify Connection**:
   ```bash
   python -c "from data_pipeline import DataPipeline; dp = DataPipeline(); dp.test_connection()"
   ```

### Groq API Setup

1. **Register**: Create account at [platform.deepseek.com](https://platform.deepseek.com)
2. **Get Credits**: New users typically get free credits
3. **Generate Key**: Navigate to API Keys section
4. **Test API**:
   ```bash
   python -c "from deepseek_agent import get_deepseek_agent; agent = get_deepseek_agent(); print('API OK')"
   ```

---

## ⚙️ Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BINANCE_TESTNET_API_KEY` | Binance API key | - | ✅ |
| `BINANCE_TESTNET_API_SECRET` | Binance API secret | - | ✅ |
| `GROQ_API_KEY` | Groq API key | - | ✅ |
| `INITIAL_CAPITAL` | Starting capital | 100000 | ✅ |
| `COMPETITION_START_DATE` | Start date (ISO format) | - | ✅ |
| `COMPETITION_DURATION_DAYS` | Duration in days | 14 | ✅ |
| `CHECK_INTERVAL_SECONDS` | Loop interval | 300 | ❌ |
| `TRADING_ASSETS` | Comma-separated symbols | BTC,ETH,SOL,BNB | ❌ |
| `MAX_DRAWDOWN` | Max allowed drawdown | 0.40 | ❌ |
| `MAX_LEVERAGE` | Max leverage per trade | 5 | ❌ |
| `MAX_POSITION_SIZE` | Max position as % | 0.10 | ❌ |
| `ALERT_WEBHOOK_URL` | Optional alert webhook | - | ❌ |

### Competition Rules

The bot automatically enforces these rules:

- ✅ **Max Drawdown**: 40% (instant disqualification if exceeded)
- ✅ **Max Leverage**: 5x per trade
- ✅ **Max Position Size**: 10% of capital per trade
- ✅ **No Manual Intervention**: Fully autonomous operation

---

## 🛡️ Risk Management

### Circuit Breaker System

The bot implements a 4-level circuit breaker system:

#### Level 1: Warning (25% Drawdown)
- Position sizes reduced to 5%
- Max leverage reduced to 2x
- Alert sent to monitoring

#### Level 2: Defensive (30% Drawdown)
- All positions closed
- Trading paused for 12 hours
- Max 3% position sizes when resumed
- Only high-confidence trades (>80%)

#### Level 3: Critical (35% Drawdown)
- All positions closed immediately
- Trading paused for 24 hours
- Max 2% position sizes when resumed
- Max 2x leverage only

#### Level 4: Emergency (38% Drawdown)
- Trading permanently halted
- All positions closed
- Competition mode: Safe shutdown

### Dynamic Position Sizing

Position sizes are calculated based on:

1. **Confidence Score** (70-100%): Higher confidence = larger size
2. **Market Regime**: Trending markets get larger positions
3. **Competition Day**: Increases aggression in final week
4. **Current Drawdown**: Reduces size as drawdown increases

Formula:
```python
position_size = base_size × confidence_mult × regime_mult × time_mult × drawdown_mult
```

---

## 📊 Monitoring & Logging

### Log Files

All logs are stored in the `logs/` directory:

- `decisions.jsonl`: Every LLM decision with context
- `trades.jsonl`: All trade executions and closures
- `performance.jsonl`: Portfolio snapshots every 5 minutes
- `errors.jsonl`: All errors with stack traces

### Real-Time Monitoring

The bot prints status updates every hour:

```
======================================================================
📊 STATUS SUMMARY
======================================================================
Portfolio Value:        $125,432.50
Total Return:              +25.43%
Drawdown:                   12.30%
Open Positions:                  2
Total Trades:                   48
Win Rate:                    58.33%
Sharpe Ratio:                 2.15
======================================================================
```

### Daily Reports

Automatically generated at the start of each trading day:

```
╔══════════════════════════════════════════════════════════════╗
║               DAILY PERFORMANCE REPORT - DAY 7               ║
╚══════════════════════════════════════════════════════════════╝

📊 PERFORMANCE METRICS
  Total Return:            +87.45%
  Max Drawdown:             15.20%
  Sharpe Ratio:              2.34

📈 TRADING STATISTICS
  Total Trades:                42
  Win Rate:                 61.90%
  Avg Win:              $1,234.56
  Avg Loss:               $567.89
  Profit Factor:             2.18

✅ ON TRACK
```

---

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Suite

```bash
# Test risk management
pytest tests/test_risk_manager.py -v

# Test Groq agent
pytest tests/test_deepseek_agent.py -v

# Test data pipeline
pytest tests/test_data_pipeline.py -v
```

### Test Coverage

- ✅ Risk management validation
- ✅ Circuit breaker triggers
- ✅ Position sizing calculations
- ✅ LLM response parsing
- ✅ Decision validation
- ✅ Technical indicator calculations
- ✅ Market regime classification

---

## 🔧 Troubleshooting

### Common Issues

#### 1. **Binance Connection Failed**

```
❌ Failed to connect to Binance: Invalid API Key
```

**Solution:**
- Verify API keys in `.env` file
- Ensure you're using **Testnet** keys, not mainnet
- Check that "Futures" permission is enabled
- Test connection: `python -c "from data_pipeline import DataPipeline; DataPipeline().test_connection()"`

#### 2. **Groq API Errors**

```
⚠️ Groq API error: 401 Unauthorized
```

**Solution:**
- Verify `GROQ_API_KEY` in `.env`
- Check API credit balance
- Ensure API key has proper permissions
- Bot will use fallback logic if API is down

#### 3. **Module Import Errors**

```
ModuleNotFoundError: No module named 'ta'
```

**Solution:**
```bash
pip install -r requirements.txt --upgrade
```

#### 4. **Insufficient Margin Error**

```
⚠️ Trade validation failed: Insufficient margin
```

**Solution:**
- Check portfolio balance on Binance Testnet
- Request more test funds if needed
- Reduce position sizes in initial trades

#### 5. **Bot Keeps Restarting**

**Solution:**
- Check `logs/errors.jsonl` for root cause
- Verify API keys are valid
- Ensure stable internet connection
- Check system resources (RAM, CPU)

### Debug Mode

Enable verbose logging by modifying `main.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 📈 Strategy Overview

### Market Analysis

The bot analyzes markets using:

1. **Technical Indicators**:
   - EMAs (9, 21, 50, 200)
   - RSI (14 period)
   - MACD
   - Bollinger Bands
   - ATR (volatility)
   - Volume analysis

2. **Market Regime Classification**:
   - Strong Trend (Up/Down)
   - Breakout (Up/Down)
   - Ranging
   - Volatile
   - Neutral

3. **Trade Setup Identification**:
   - Trend Following
   - Breakout Trading
   - Mean Reversion
   - Momentum Plays

### Decision Making

For each asset, the bot:

1. Fetches real-time market data
2. Calculates technical indicators
3. Identifies trade setups
4. Builds context for LLM
5. Queries Groq for decision
6. Validates decision against rules
7. Calculates position size and leverage
8. Executes trade if all checks pass

### Execution

Every trade includes:

- ✅ Market entry order
- ✅ Stop-loss order (mandatory)
- ✅ Multiple take-profit levels (50%, 75%, 100%)
- ✅ Trailing stop (activated at +5% profit)

---

## 🎯 Competition Strategy

### Week 1 (Days 1-7): Foundation Building

**Goal**: +30-50% returns

- Conservative position sizes (6-8%)
- Moderate leverage (2-3x)
- Focus on high-probability setups
- Build consistent win rate (>60%)

### Week 2 (Days 8-14): Aggressive Compounding

**Goal**: +80-150% total returns

- Larger position sizes (8-10%)
- Higher leverage on conviction (4-5x)
- Capitalize on momentum
- Final push in days 12-14

### Key Tactics

1. **Momentum Stacking**: Layer positions in strong trends
2. **Volatility Plays**: Trade breakouts during high-volume periods
3. **Funding Rate Arbitrage**: Use funding rates as sentiment indicator
4. **Correlation Trading**: Trade multiple correlated assets

---

## 📊 Performance Metrics

### Calculation Methods

#### Sharpe Ratio
```python
sharpe = (mean_return / std_return) × √(periods_per_year)
```

#### Max Drawdown
```python
drawdown = (peak_value - current_value) / peak_value × 100
```

#### Win Rate
```python
win_rate = winning_trades / total_trades × 100
```

#### Profit Factor
```python
profit_factor = total_wins / total_losses
```

---

## 🔒 Security Best Practices

1. **Never commit `.env` file** - Contains sensitive API keys
2. **Use Testnet only** - Never use mainnet keys for testing
3. **Rotate API keys** - After competition, revoke keys
4. **Monitor access logs** - Check for unauthorized access
5. **Secure your machine** - Use firewall and antivirus
6. **Backup logs** - Keep records for audit trail

---

## 🛠️ Advanced Configuration

### Custom Trading Assets

Edit `.env`:
```bash
TRADING_ASSETS=BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,ADAUSDT
```

### Adjust Check Interval

```bash
CHECK_INTERVAL_SECONDS=180  # Check every 3 minutes
```

### Custom Circuit Breakers

Edit `config.py`:
```python
CIRCUIT_BREAKERS = {
    'LEVEL_1': {'drawdown': 0.20, 'max_position_size': 0.05, 'max_leverage': 2},
    'LEVEL_2': {'drawdown': 0.25, 'max_position_size': 0.03, 'max_leverage': 2},
    ...
}
```

---

## 📝 Maintenance

### During Competition

- ✅ **Do NOT stop** the bot unless critical error
- ✅ **Monitor logs** periodically
- ✅ **Check portfolio** on Binance dashboard
- ❌ **Do NOT** manually place trades
- ❌ **Do NOT** modify running bot

### After Competition

1. Let bot complete gracefully (closes all positions)
2. Review `logs/final_report.txt`
3. Analyze decision logs for improvements
4. Revoke API keys if not reusing

---

## 🤝 Support & Resources

### Documentation

- [Binance Futures API](https://binance-docs.github.io/apidocs/futures/en/)
- [Groq API Docs](https://console.groq.com/docs)
- [Technical Analysis Library](https://technical-analysis-library-in-python.readthedocs.io/)

### Common Commands

```bash
# Start bot with auto-restart
python run_with_restart.py

# Run tests
pytest tests/ -v

# Check logs
tail -f logs/errors.jsonl

# View final report
cat logs/final_report.txt
```

---

## ⚠️ Disclaimer

**This bot is for educational and competition purposes only.**

- Use at your own risk
- No guarantees of profitability
- Past performance ≠ future results
- Always use testnet for development
- Never risk more than you can afford to lose

---

## 📜 License

MIT License - see LICENSE file for details

---

## 🎉 Good Luck!

Your bot is now ready to compete! Remember:

1. ✅ Test thoroughly on testnet first
2. ✅ Monitor regularly but don't intervene
3. ✅ Trust the risk management system
4. ✅ Keep stable internet connection
5. ✅ Have fun and learn!

**May your Sharpe ratio be high and your drawdowns be low! 🚀**

---

*Last Updated: 2024-10-28*

