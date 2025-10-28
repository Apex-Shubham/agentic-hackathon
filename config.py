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
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Competition Settings
INITIAL_CAPITAL = float(os.getenv('INITIAL_CAPITAL', 100000))
COMPETITION_START_DATE = os.getenv('COMPETITION_START_DATE', '2024-11-01T00:00:00Z')
COMPETITION_DURATION_DAYS = float(os.getenv('COMPETITION_DURATION_DAYS', 14))
CHECK_INTERVAL_SECONDS = int(os.getenv('CHECK_INTERVAL_SECONDS', 30))
MIN_CONFIDENCE = int(os.getenv('MIN_CONFIDENCE', 60))

# Forced initial trade (for bootstrapping/testing)
FORCE_INITIAL_TRADE = os.getenv('FORCE_INITIAL_TRADE', 'false').lower() == 'true'
INITIAL_TRADE_SYMBOL = os.getenv('INITIAL_TRADE_SYMBOL', 'BTCUSDT')
INITIAL_TRADE_SIDE = os.getenv('INITIAL_TRADE_SIDE', 'LONG')  # LONG or SHORT
INITIAL_TRADE_SIZE_PCT = float(os.getenv('INITIAL_TRADE_SIZE_PCT', 0.05))  # 5%
INITIAL_TRADE_LEVERAGE = int(os.getenv('INITIAL_TRADE_LEVERAGE', 2))

# Risk Limits
MAX_DRAWDOWN = float(os.getenv('MAX_DRAWDOWN', 0.40))
MAX_LEVERAGE = int(os.getenv('MAX_LEVERAGE', 5))
MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', 0.10))
MAX_OPEN_POSITIONS = int(os.getenv('MAX_OPEN_POSITIONS', 3))

# Trading Assets
TRADING_ASSETS = os.getenv('TRADING_ASSETS', 'BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT').split(',')

# Alert Settings
ALERT_WEBHOOK_URL = os.getenv('ALERT_WEBHOOK_URL', '')

# Technical Indicator Settings (Binance-supported intervals)
# Faster cycles for testing
TIMEFRAMES = ['5m', '15m', '1h', '4h']
KLINE_LIMIT = int(os.getenv('KLINE_LIMIT', 200))  # Faster warm-up for tests

# Fast exit/management settings
STALE_POSITION_MINUTES = int(os.getenv('STALE_POSITION_MINUTES', 20))
STALE_PNL_BAND = float(os.getenv('STALE_PNL_BAND', 0.3))  # +/- % band considered "no progress"

# Risk Manager Settings
CIRCUIT_BREAKERS = {
    'LEVEL_1': {'drawdown': 0.25, 'max_position_size': 0.05, 'max_leverage': 2},
    'LEVEL_2': {'drawdown': 0.30, 'max_position_size': 0.03, 'max_leverage': 2},
    'LEVEL_3': {'drawdown': 0.35, 'max_position_size': 0.02, 'max_leverage': 2},
    'LEVEL_4': {'drawdown': 0.38, 'max_position_size': 0.00, 'max_leverage': 1}
}

# Position Management
TRAILING_STOP_ACTIVATION = 0.05  # Activate trailing stop at 5% profit
SCALED_TP_LEVELS = [0.5, 0.3, 0.2]  # 50% at TP1, 30% at TP2, 20% trailing

# Groq Settings
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_TEMPERATURE = 0.3
GROQ_MAX_TOKENS = 500
GROQ_TIMEOUT = 30

# Logging Settings
LOG_DIR = 'logs'
DECISION_LOG_FILE = f'{LOG_DIR}/decisions.jsonl'
TRADE_LOG_FILE = f'{LOG_DIR}/trades.jsonl'
PERFORMANCE_LOG_FILE = f'{LOG_DIR}/performance.jsonl'
ERROR_LOG_FILE = f'{LOG_DIR}/errors.jsonl'

# Health Monitor Settings
HEALTH_CHECK_INTERVAL = 60  # seconds
MAX_API_RETRIES = 3
RETRY_BACKOFF_MULTIPLIER = 2
API_TIMEOUT = 30

# Binance Settings
BINANCE_TESTNET_URL = 'https://testnet.binancefuture.com'

# System Prompt for DeepSeek
SYSTEM_PROMPT = """You are an elite crypto trader managing a $5,000 portfolio in a 14-day high-stakes trading competition on Binance Futures.

CRITICAL CONSTRAINTS (VIOLATION = INSTANT DISQUALIFICATION):
- Maximum drawdown: 40% (if breached, you are disqualified)
- Maximum leverage: 5x per trade
- Maximum position size: 10% of capital per trade
- No manual intervention allowed - all decisions must be autonomous

OBJECTIVE: Maximize total returns while maintaining risk-adjusted performance (Sharpe ratio)

SCORING:
- Total Returns: 60% of final score
- Risk-Adjusted Returns (Sharpe Ratio): 40% of final score

STRATEGY GUIDELINES:
1. Be aggressive but calculated - this is a competition, not long-term investing
2. Only take high-probability setups (>70% confidence)
3. Use leverage strategically: 3-5x on high conviction trades
4. Cut losses fast: 3-5% stop loss on every trade
5. Let winners run: 15-25% take profit targets
6. Compound gains daily to accelerate growth
7. Increase aggression as days pass (time pressure)
8. Scale position sizes based on market regime and confidence

MARKET REGIMES:
- STRONG_TREND: Large directional moves, use higher leverage (4-5x)
- BREAKOUT: Price breaking key levels, aggressive entries (4x)
- RANGING: Choppy sideways action, reduce size or avoid
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
- Only output LONG or SHORT if confidence >= 60
- Higher confidence = larger position size
- If unsure or confidence < 70, output HOLD
- CLOSE if existing position should be exited
- Always set stop_loss_percent (mandatory risk management)
- take_profit_percent should be realistic based on market conditions
- urgency reflects how time-sensitive the setup is
"""

def validate_config():
    """Validate that all required configuration is present"""
    errors = []
    
    if not BINANCE_API_KEY:
        errors.append("BINANCE_TESTNET_API_KEY not set")
    if not BINANCE_API_SECRET:
        errors.append("BINANCE_TESTNET_API_SECRET not set")
    if not GROQ_API_KEY:
        errors.append("GROQ_API_KEY not set")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True

# Create logs directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

