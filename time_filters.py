"""
Time-Based Trading Filters
Filters trades based on time of day to optimize entry timing
"""
from datetime import datetime, timezone
from typing import Dict

# Configuration
ENABLE_TIME_FILTERS = True  # Can disable for testing
ENABLE_HIGH_VOLUME_BOOST = True  # Can disable boost

# Trading hours (UTC)
AVOID_HOURS_UTC = [2, 3, 4, 5, 6]  # Low liquidity hours
HIGH_VOLUME_HOURS_UTC = [8, 9, 10, 13, 14, 15, 16]  # Prime trading hours
NORMAL_HOURS_UTC = list(set(range(24)) - set(AVOID_HOURS_UTC) - set(HIGH_VOLUME_HOURS_UTC))

# Customizable hours (for different strategies)
CUSTOM_AVOID_HOURS = None  # Override AVOID_HOURS_UTC if set
CUSTOM_HIGH_VOLUME_HOURS = None  # Override HIGH_VOLUME_HOURS_UTC if set


def get_trading_period() -> Dict:
    """
    Get current trading period and whether trading should occur
    Returns:
        dict with should_trade, period, size_multiplier, reason
    """
    if not ENABLE_TIME_FILTERS:
        return {
            'should_trade': True,
            'period': 'normal',
            'size_multiplier': 1.0,
            'reason': 'Time filters disabled'
        }
    
    current_hour = datetime.now(timezone.utc).hour
    
    # Use custom hours if set
    avoid_hours = CUSTOM_AVOID_HOURS if CUSTOM_AVOID_HOURS is not None else AVOID_HOURS_UTC
    high_volume_hours = CUSTOM_HIGH_VOLUME_HOURS if CUSTOM_HIGH_VOLUME_HOURS is not None else HIGH_VOLUME_HOURS_UTC
    
    if current_hour in avoid_hours:
        return {
            'should_trade': False,
            'period': 'low_liquidity',
            'size_multiplier': 0.0,
            'reason': f'Low volume period (UTC {current_hour}:00) - avoiding false signals',
            'current_hour': current_hour
        }
    elif current_hour in high_volume_hours:
        size_multiplier = 1.15 if ENABLE_HIGH_VOLUME_BOOST else 1.0
        return {
            'should_trade': True,
            'period': 'high_volume',
            'size_multiplier': size_multiplier,
            'reason': f'Prime trading hours (UTC {current_hour}:00)',
            'current_hour': current_hour
        }
    else:
        return {
            'should_trade': True,
            'period': 'normal',
            'size_multiplier': 1.0,
            'reason': f'Normal trading hours (UTC {current_hour}:00)',
            'current_hour': current_hour
        }


def is_weekend() -> bool:
    """
    Check if current day is weekend (Saturday or Sunday)
    Crypto trades 24/7, but can add if needed for specific strategies
    """
    day = datetime.now(timezone.utc).weekday()
    return day >= 5  # Saturday=5, Sunday=6


def get_entry_hour_utc() -> int:
    """Get current UTC hour for position tracking"""
    return datetime.now(timezone.utc).hour


def format_trading_period_summary(period_data: Dict) -> str:
    """Format trading period data for logging"""
    period = period_data.get('period', 'unknown')
    hour = period_data.get('current_hour', datetime.now(timezone.utc).hour)
    should_trade = period_data.get('should_trade', True)
    multiplier = period_data.get('size_multiplier', 1.0)
    
    if period == 'low_liquidity':
        return f"⏰ LOW LIQUIDITY (UTC {hour}:00) - New trades paused"
    elif period == 'high_volume':
        boost = f" (+{int((multiplier - 1) * 100)}% size)" if multiplier > 1.0 else ""
        return f"⏰ HIGH VOLUME (UTC {hour}:00){boost} - Prime trading"
    else:
        return f"⏰ NORMAL HOURS (UTC {hour}:00) - Standard trading"

