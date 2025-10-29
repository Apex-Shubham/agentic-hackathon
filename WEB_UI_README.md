# Trading Bot Web UI

A modern web dashboard to monitor your trading bot's performance, trades, and status in real-time.

## Features

- **Real-time Portfolio Monitoring**: View portfolio value, returns, drawdown, and available balance
- **Performance Charts**: Interactive charts showing portfolio performance over time
- **Open Positions**: Track all open positions with PnL, leverage, and entry prices
- **Trade History**: View recent trades with detailed execution information
- **Decision Log**: See all AI trading decisions with confidence scores and reasoning
- **Trading Statistics**: Win rate, Sharpe ratio, profit factor, and more
- **Health Status**: Monitor bot health and circuit breaker status
- **Auto-refresh**: Dashboard updates every 5 seconds automatically

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install Flask and all other dependencies.

### 2. Start the Web UI

```bash
python start_web_ui.py
```

Or directly:

```bash
python web_ui.py
```

### 3. Access the Dashboard

Open your browser and navigate to:

```
http://localhost:5000
```

The dashboard will automatically connect to your bot's data (logs and executor) and display real-time information.

## Running Alongside the Bot

The web UI can run independently or alongside the main trading bot:

**Option 1: Run separately (Recommended)**
```bash
# Terminal 1: Start the trading bot
python main.py

# Terminal 2: Start the web UI
python start_web_ui.py
```

**Option 2: Run together (Single terminal)**
```bash
# In background
python main.py &
python start_web_ui.py
```

## API Endpoints

The web UI exposes several REST API endpoints:

- `GET /` - Main dashboard page
- `GET /api/portfolio` - Current portfolio status
- `GET /api/metrics` - Performance metrics
- `GET /api/trades?limit=50` - Recent trades
- `GET /api/decisions?limit=50` - Recent decisions
- `GET /api/performance?hours=24` - Performance history for charts
- `GET /api/errors?limit=20` - Recent errors
- `GET /api/performance-by-strategy` - Performance breakdown by strategy
- `GET /api/health` - Bot health status

## Configuration

The web UI uses the same configuration as the trading bot (from `.env` and `config.py`). It reads from:

- Log files in the `logs/` directory
- Executor instance for current portfolio status
- Logger instance for metrics calculation

## Troubleshooting

### Port Already in Use

If port 5000 is already in use, edit `web_ui.py` or `start_web_ui.py`:

```python
app.run(host='0.0.0.0', port=5001, debug=False)  # Change 5000 to 5001
```

### No Data Showing

- Ensure the trading bot has been running and generating logs
- Check that log files exist in the `logs/` directory
- Verify API keys are configured correctly

### Import Errors

If you get import errors, ensure:
- All dependencies are installed: `pip install -r requirements.txt`
- You're running from the project root directory
- The bot's configuration is set up correctly

## Features in Detail

### Portfolio Overview

- **Portfolio Value**: Current total portfolio value (balance + unrealized PnL)
- **Total Return**: Percentage return since competition start
- **Drawdown**: Current drawdown percentage with risk indicators
- **Available Balance**: Available margin for new trades
- **Unrealized PnL**: Profit/loss on open positions

### Performance Chart

Interactive line chart showing:
- Portfolio value over time (green line)
- Initial capital baseline (dashed gray line)
- Updates every 5 seconds with latest 24 hours of data

### Open Positions Table

Shows for each position:
- Symbol (e.g., BTCUSDT)
- Side (LONG/SHORT)
- Entry price
- Current price
- Quantity
- Leverage
- PnL (absolute and percentage)
- Color-coded: Green for profit, Red for loss

### Trading Statistics

- **Total Trades**: Number of completed trades
- **Win Rate**: Percentage of profitable trades
- **Sharpe Ratio**: Risk-adjusted returns measure
- **Profit Factor**: Gross profit / Gross loss
- **Average Win**: Average profit per winning trade

### Recent Decisions

Log of all AI trading decisions showing:
- Timestamp
- Asset
- Action (LONG/SHORT/CLOSE/HOLD)
- Confidence score (0-100%)
- Position size percentage
- Leverage
- Entry reason
- Market regime

### Circuit Breaker Alerts

When circuit breakers are active, a red alert banner appears at the top-right showing the current circuit breaker level.

## Browser Compatibility

The dashboard works best in modern browsers:
- Chrome/Edge (recommended)
- Firefox
- Safari

## Security Note

⚠️ **Important**: The web UI runs on `0.0.0.0:5000` by default, making it accessible on your local network. For production use, consider:

- Running on `127.0.0.1` instead (localhost only)
- Adding authentication
- Using a reverse proxy (nginx) with SSL

For local development and monitoring, the current setup is fine.

## Updates

The dashboard auto-refreshes every 5 seconds to show the latest data. No manual refresh needed!

