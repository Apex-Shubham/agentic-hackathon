"""
Configuration module for the trading bot
Loads environment variables and provides configuration constants
"""
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
BINANCE_API_KEY = os.getenv('BINANCE_TESTNET_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_TESTNET_API_SECRET')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# Competition Settings - FIXED: Use current date if not set
COMPETITION_START_DATE = os.getenv('COMPETITION_START_DATE', datetime.now(timezone.utc).isoformat())
COMPETITION_DURATION_DAYS = float(os.getenv('COMPETITION_DURATION_DAYS', 14))
CHECK_INTERVAL_SECONDS = int(os.getenv('CHECK_INTERVAL_SECONDS', 30))
MIN_CONFIDENCE = int(os.getenv('MIN_CONFIDENCE', 60))

# IMPORTANT: Initial capital will be fetched from Binance at runtime
# This is just a fallback/default
INITIAL_CAPITAL = float(os.getenv('INITIAL_CAPITAL', 5000))

# Forced initial trade (for bootstrapping/testing)
FORCE_INITIAL_TRADE = os.getenv('FORCE_INITIAL_TRADE', 'false').lower() == 'true'
INITIAL_TRADE_SYMBOL = os.getenv('INITIAL_TRADE_SYMBOL', 'BTCUSDT')
INITIAL_TRADE_SIDE = os.getenv('INITIAL_TRADE_SIDE', 'LONG')  # LONG or SHORT
INITIAL_TRADE_SIZE_PCT = float(os.getenv('INITIAL_TRADE_SIZE_PCT', 0.05))  # 5%
INITIAL_TRADE_LEVERAGE = int(os.getenv('INITIAL_TRADE_LEVERAGE', 2))

# Risk Limits - FIXED: Adjusted thresholds to match competition rules
MAX_DRAWDOWN = 0.40  # 40% = disqualification (6000/10000)
MAX_LEVERAGE = int(os.getenv('MAX_LEVERAGE', 5))
MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', 0.10))
MAX_OPEN_POSITIONS = int(os.getenv('MAX_OPEN_POSITIONS', 5))

# Portfolio limits
MAX_POSITIONS_PER_SYMBOL = int(os.getenv('MAX_POSITIONS_PER_SYMBOL', 2))  # Allow pyramiding (max 2 per symbol)
MAX_CORRELATED_POSITIONS = int(os.getenv('MAX_CORRELATED_POSITIONS', 3))  # Max 3 crypto positions (BTC/ETH/SOL correlate)
MAX_PORTFOLIO_RISK = float(os.getenv('MAX_PORTFOLIO_RISK', 0.15))  # Total risk capped at 15%

# Position sizing (12% base = $600 on $5000)
POSITION_SIZE_PERCENT = float(os.getenv('POSITION_SIZE_PERCENT', 0.12))
HIGH_CONFIDENCE_SIZE = float(os.getenv('HIGH_CONFIDENCE_SIZE', 0.15))    # $750 for 85%+ confidence
MEDIUM_CONFIDENCE_SIZE = float(os.getenv('MEDIUM_CONFIDENCE_SIZE', 0.12))  # $600 for 75-84% confidence
LOW_CONFIDENCE_SIZE = float(os.getenv('LOW_CONFIDENCE_SIZE', 0.08))     # $400 for 70-74% confidence

# Leverage by confidence
HIGH_CONFIDENCE_LEVERAGE = int(os.getenv('HIGH_CONFIDENCE_LEVERAGE', 3))
BASE_LEVERAGE = int(os.getenv('BASE_LEVERAGE', 2))
LEVERAGE_THRESHOLD = int(os.getenv('LEVERAGE_THRESHOLD', 80))  # Use 3x above this confidence

# Volatility Trading Settings (kept for backwards compatibility)
ENABLE_VOLATILITY_TRADING = os.getenv('ENABLE_VOLATILITY_TRADING', 'true').lower() == 'true'
VOLATILITY_MIN_ATR_RATIO = float(os.getenv('VOLATILITY_MIN_ATR_RATIO', 0.01))  # ATR > 1% of price
SCALP_MODE_THRESHOLD = float(os.getenv('SCALP_MODE_THRESHOLD', 0.03))  # 24h range > 3%
MIN_CONFIDENCE_VOLATILE = int(os.getenv('MIN_CONFIDENCE_VOLATILE', 60))
SCALP_POSITION_SIZE = float(os.getenv('SCALP_POSITION_SIZE', 0.05))
SCALP_STOP_LOSS = float(os.getenv('SCALP_STOP_LOSS', 0.02))
SCALP_TAKE_PROFIT = float(os.getenv('SCALP_TAKE_PROFIT', 0.04))

# Trading Assets
TRADING_ASSETS = os.getenv('TRADING_ASSETS', 'BTCUSDT,SOLUSDT').split(',')

# Alert Settings
ALERT_WEBHOOK_URL = os.getenv('ALERT_WEBHOOK_URL', '')

# Technical Indicator Settings (Binance-supported intervals)
TIMEFRAMES = ['5m', '15m', '1h', '4h']
KLINE_LIMIT = int(os.getenv('KLINE_LIMIT', 200))

# Fast exit/management settings
STALE_POSITION_MINUTES = int(os.getenv('STALE_POSITION_MINUTES', 20))
STALE_PNL_BAND = float(os.getenv('STALE_PNL_BAND', 0.3))

# Risk Manager Settings - FIXED: Only halt at true 40% drawdown
CIRCUIT_BREAKERS = {
    'LEVEL_1': {'drawdown': 0.20, 'max_position_size': 0.08, 'max_leverage': 3},
    'LEVEL_2': {'drawdown': 0.30, 'max_position_size': 0.05, 'max_leverage': 2},
    'LEVEL_3': {'drawdown': 0.35, 'max_position_size': 0.03, 'max_leverage': 2},
    'LEVEL_4': {'drawdown': 0.40, 'max_position_size': 0.00, 'max_leverage': 1}  # Disqualification
}

# Position Management
TRAILING_STOP_ACTIVATION = 0.05
SCALED_TP_LEVELS = [0.5, 0.3, 0.2]

# OpenRouter Settings
OPENROUTER_API_URL = os.getenv('OPENROUTER_API_URL', 'https://openrouter.ai/api/v1/chat/completions')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'meta-llama/llama-3.1-8b-instruct:free')
OPENROUTER_TEMPERATURE = float(os.getenv('OPENROUTER_TEMPERATURE', 0.3))
OPENROUTER_MAX_TOKENS = int(os.getenv('OPENROUTER_MAX_TOKENS', 500))
OPENROUTER_TIMEOUT = int(os.getenv('OPENROUTER_TIMEOUT', 30))

# Logging Settings
LOG_DIR = 'logs'
DECISION_LOG_FILE = f'{LOG_DIR}/decisions.jsonl'
TRADE_LOG_FILE = f'{LOG_DIR}/trades.jsonl'
PERFORMANCE_LOG_FILE = f'{LOG_DIR}/performance.jsonl'
ERROR_LOG_FILE = f'{LOG_DIR}/errors.jsonl'
ASSESSMENT_LOG_FILE = f'{LOG_DIR}/assessments.jsonl'

# Health Monitor Settings
HEALTH_CHECK_INTERVAL = 60
MAX_API_RETRIES = 3
RETRY_BACKOFF_MULTIPLIER = 2
API_TIMEOUT = 30

# Binance Settings
BINANCE_TESTNET_URL = 'https://testnet.binancefuture.com'

# System Prompt for Qwen3
SYSTEM_PROMPT = """You are an elite crypto futures trader managing a portfolio in a 14-day Binance Futures trading competition.

CRITICAL CONSTRAINTS (VIOLATION = INSTANT DISQUALIFICATION):
- Maximum drawdown: 40% (if balance drops below 60% of starting capital, you are disqualified)
- Maximum leverage: 5x per trade
- Maximum position size: 10% of capital per trade
- No manual intervention allowed - all decisions must be autonomous

OBJECTIVE: Maximize total returns while managing risk effectively.

SCORING:
- Total Returns: 60% of final score
- Risk-Adjusted Returns (Sharpe Ratio): 40% of final score

STRATEGY GUIDELINES:
1. Only take high-probability setups (>70% confidence)
2. Use leverage strategically: 2-5x on high conviction trades
3. Cut losses fast: 3-5% stop loss on every trade
4. Let winners run: 10-25% take profit targets
5. Scale position sizes based on confidence and market conditions
6. Avoid overtrading - quality over quantity
7. PYRAMIDING ALLOWED: You can add positions to existing trades if setup is profitable
   - Maximum 2 positions per symbol (BTCUSDT or SOLUSDT)
   - Evaluate existing position PnL before pyramiding
   - Only pyramid if new setup is strong and existing position is profitable or near breakeven
   - Avoid pyramiding into losing positions unless strong reversal signal

MARKET REGIMES:
- STRONG_TREND: Clear directional moves, use higher leverage (4-5x)
- BREAKOUT: Price breaking key levels, aggressive entries (3-4x)
- RANGING: Sideways action, reduce size or avoid
- VOLATILE: High uncertainty, lower leverage (2-3x)

OUTPUT FORMAT (STRICT JSON - NO ADDITIONAL TEXT):
{
  "action": "LONG|SHORT|CLOSE|HOLD",
  "confidence": 0-100,
  "position_size_percent": 1-10,
  "leverage": 1-5,
  "entry_reason": "concise 1-2 sentence explanation",
  "stop_loss_percent": 3-6,
  "take_profit_percent": 10-25,
  "urgency": "LOW|MEDIUM|HIGH"
}

DECISION RULES:
- Only output LONG or SHORT if confidence >= 70
- Higher confidence = larger position size
- If unsure or confidence < 70, output HOLD
- CLOSE if existing position should be exited
- Always set stop_loss_percent (mandatory risk management)
- take_profit_percent should be realistic based on market conditions
- urgency reflects how time-sensitive the setup is

Remember: Preservation of capital is priority #1. Never risk more than you can afford to lose.
"""

def get_binance_balance():
    """Fetch actual USDT balance from Binance testnet"""
    try:
        from binance.client import Client
        client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=True)
        balance = client.futures_account_balance()
        usdt_balance = next((float(b['balance']) for b in balance if b['asset'] == 'USDT'), 0)
        return usdt_balance
    except Exception as e:
        print(f"⚠️  Could not fetch Binance balance: {e}")
        print(f"⚠️  Using fallback INITIAL_CAPITAL: ${INITIAL_CAPITAL:,.2f}")
        return INITIAL_CAPITAL

def validate_config():
    """Validate that all required configuration is present"""
    errors = []
    
    if not BINANCE_API_KEY:
        errors.append("BINANCE_TESTNET_API_KEY not set")
    if not BINANCE_API_SECRET:
        errors.append("BINANCE_TESTNET_API_SECRET not set")
    if not OPENROUTER_API_KEY:
        errors.append("OPENROUTER_API_KEY not set")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True

# Create logs directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

def get_adaptive_min_confidence() -> int:
    """Get MIN_CONFIDENCE adjusted based on recent trade performance"""
    base_confidence = int(os.getenv('MIN_CONFIDENCE', 60))
    
    try:
        from analytics.performance_tracker import get_performance_tracker
        tracker = get_performance_tracker()
        adjustment = tracker.suggest_confidence_adjustment()
        adaptive_confidence = base_confidence + adjustment
        
        # Clamp to reasonable range
        return max(50, min(adaptive_confidence, 85))
    except Exception:
        # If tracker fails, return base value
        return base_confidence

# Use adaptive confidence as default (can be overridden by env)
MIN_CONFIDENCE = get_adaptive_min_confidence()