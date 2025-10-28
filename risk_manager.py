"""
Risk Management System
Handles position sizing, circuit breakers, drawdown monitoring, and risk limits
"""
from typing import Dict, Tuple
from datetime import datetime, timedelta, timezone
from config import (
    INITIAL_CAPITAL, MAX_DRAWDOWN, MAX_LEVERAGE, MAX_POSITION_SIZE,
    MAX_OPEN_POSITIONS, CIRCUIT_BREAKERS, MIN_CONFIDENCE
)


class RiskManager:
    """Manages all risk parameters and enforces trading limits"""
    
    def __init__(self, initial_capital: float = INITIAL_CAPITAL):
        self.initial_capital = initial_capital
        self.peak_value = initial_capital
        self.current_drawdown = 0.0
        self.daily_start_value = initial_capital
        self.daily_loss_limit = 0.15  # 15% daily loss limit
        self.circuit_breaker_level = None
        self.circuit_breaker_until = None
        self.total_trades_today = 0
        self.last_reset_date = datetime.now(timezone.utc).date()
    
    def check_circuit_breakers(self) -> Tuple[bool, str]:
        """
        Check if any circuit breakers are triggered
        Returns: (can_trade, reason)
        """
        # Check if we're in a circuit breaker pause period
        if self.circuit_breaker_until and datetime.now(timezone.utc) < self.circuit_breaker_until:
            remaining = (self.circuit_breaker_until - datetime.now(timezone.utc)).total_seconds() / 3600
            return False, f"Circuit breaker active for {remaining:.1f} more hours"
        
        # Level 4: Emergency stop (38% drawdown)
        if self.current_drawdown >= CIRCUIT_BREAKERS['LEVEL_4']['drawdown']:
            self.circuit_breaker_level = 'LEVEL_4'
            return False, "EMERGENCY STOP: Drawdown ≥38% - Trading halted to prevent disqualification"
        
        # Level 3: Critical mode (35% drawdown)
        if self.current_drawdown >= CIRCUIT_BREAKERS['LEVEL_3']['drawdown']:
            self.circuit_breaker_level = 'LEVEL_3'
            if self.circuit_breaker_until is None:
                self.circuit_breaker_until = datetime.now(timezone.utc) + timedelta(hours=24)
                return False, "CRITICAL: Drawdown ≥35% - 24h trading pause initiated"
            return True, "CRITICAL MODE: Extreme caution required"
        
        # Level 2: Defensive mode (30% drawdown)
        if self.current_drawdown >= CIRCUIT_BREAKERS['LEVEL_2']['drawdown']:
            self.circuit_breaker_level = 'LEVEL_2'
            if self.circuit_breaker_until is None:
                self.circuit_breaker_until = datetime.now(timezone.utc) + timedelta(hours=12)
                return False, "DEFENSIVE MODE: Drawdown ≥30% - 12h trading pause"
            return True, "DEFENSIVE MODE: Reduced risk only"
        
        # Level 1: Warning mode (25% drawdown)
        if self.current_drawdown >= CIRCUIT_BREAKERS['LEVEL_1']['drawdown']:
            self.circuit_breaker_level = 'LEVEL_1'
            return True, "WARNING: Drawdown ≥25% - Risk reduction active"
        
        # Check daily loss limit
        daily_loss = ((self.current_value - self.daily_start_value) / self.daily_start_value)
        if daily_loss < -self.daily_loss_limit:
            return False, f"Daily loss limit reached ({abs(daily_loss)*100:.1f}%)"
        
        # All clear
        self.circuit_breaker_level = None
        return True, "All systems operational"
    
    def calculate_position_size(
        self, 
        confidence: float, 
        regime: str, 
        day_number: int, 
        current_drawdown: float
    ) -> float:
        """
        Calculate optimal position size based on multiple factors
        Returns: position size as decimal (e.g., 0.08 for 8%)
        """
        base_size = 0.08  # 8% base position size
        
        # Confidence multiplier (0.5 to 1.5)
        conf_mult = 0.5 + (confidence / 100)
        
        # Regime multiplier
        regime_multipliers = {
            'STRONG_TREND_UP': 1.3,
            'STRONG_TREND_DOWN': 1.3,
            'BREAKOUT_UP': 1.4,
            'BREAKOUT_DOWN': 1.4,
            'MOMENTUM': 1.2,
            'RANGING': 0.7,
            'VOLATILE': 0.8,
            'NEUTRAL': 0.9,
            'UNKNOWN': 0.5
        }
        regime_mult = regime_multipliers.get(regime, 0.9)
        
        # Time pressure multiplier (increase aggression as competition progresses)
        if day_number <= 5:
            time_mult = 1.0  # Conservative early on
        elif day_number <= 10:
            time_mult = 1.15  # Moderate aggression
        else:
            time_mult = 1.25  # Final push
        
        # Drawdown protection multiplier
        if current_drawdown < 0.15:
            dd_mult = 1.0  # No drawdown issues
        elif current_drawdown < 0.25:
            dd_mult = 0.8  # Slight reduction
        elif current_drawdown < 0.30:
            dd_mult = 0.5  # Significant reduction
        elif current_drawdown < 0.35:
            dd_mult = 0.3  # Extreme caution
        else:
            dd_mult = 0.2  # Minimal sizing
        
        # Circuit breaker adjustments
        if self.circuit_breaker_level == 'LEVEL_1':
            dd_mult *= 0.6  # Further reduce at Level 1
        elif self.circuit_breaker_level == 'LEVEL_2':
            dd_mult *= 0.4  # Minimal at Level 2
        elif self.circuit_breaker_level == 'LEVEL_3':
            dd_mult *= 0.25  # Tiny positions only at Level 3
        
        # Calculate final position size
        position_size = base_size * conf_mult * regime_mult * time_mult * dd_mult
        
        # Apply hard limit
        position_size = min(position_size, MAX_POSITION_SIZE)
        
        # Minimum viable size check
        if position_size < 0.01:  # Less than 1%
            position_size = 0.0  # Don't trade if too small
        
        return round(position_size, 4)
    
    def calculate_optimal_leverage(self, confidence: float, regime: str) -> int:
        """
        Calculate optimal leverage based on confidence and market regime
        Returns: leverage (1-5)
        """
        # Base leverage from confidence
        if confidence >= 90:
            base_leverage = 5
        elif confidence >= 85:
            base_leverage = 4
        elif confidence >= 80:
            base_leverage = 3
        elif confidence >= 75:
            base_leverage = 3
        else:
            base_leverage = 2
        
        # Adjust for regime
        regime_leverage = {
            'STRONG_TREND_UP': 0,
            'STRONG_TREND_DOWN': 0,
            'BREAKOUT_UP': 0,
            'BREAKOUT_DOWN': 0,
            'MOMENTUM': -1,
            'RANGING': -2,
            'VOLATILE': -2,
            'NEUTRAL': -1,
            'UNKNOWN': -3
        }
        
        leverage = base_leverage + regime_leverage.get(regime, -1)
        
        # Apply circuit breaker limits
        if self.circuit_breaker_level:
            max_cb_leverage = CIRCUIT_BREAKERS[self.circuit_breaker_level]['max_leverage']
            leverage = min(leverage, max_cb_leverage)
        
        # Enforce hard limits
        leverage = max(1, min(leverage, MAX_LEVERAGE))
        
        return leverage
    
    def update_portfolio_metrics(self, current_portfolio_value: float):
        """Update risk metrics based on current portfolio value"""
        self.current_value = current_portfolio_value
        
        # Update peak value
        if current_portfolio_value > self.peak_value:
            self.peak_value = current_portfolio_value
        
        # Calculate drawdown
        self.current_drawdown = (self.peak_value - current_portfolio_value) / self.peak_value
        
        # Reset daily metrics if new day
        current_date = datetime.now(timezone.utc).date()
        if current_date > self.last_reset_date:
            self.daily_start_value = current_portfolio_value
            self.total_trades_today = 0
            self.last_reset_date = current_date
            print(f"📅 New trading day started. Portfolio: ${current_portfolio_value:,.2f}")
    
    def check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit has been exceeded"""
        daily_loss = (self.current_value - self.daily_start_value) / self.daily_start_value
        return daily_loss > -self.daily_loss_limit
    
    def validate_trade(
        self, 
        decision: Dict, 
        portfolio: Dict, 
        position_size: float,
        leverage: int
    ) -> Tuple[bool, str]:
        """
        Validate a trade before execution
        Returns: (is_valid, reason)
        """
        # Check circuit breakers
        can_trade, reason = self.check_circuit_breakers()
        if not can_trade:
            return False, reason
        
        # Check position size
        if position_size > MAX_POSITION_SIZE:
            return False, f"Position size {position_size:.1%} exceeds limit {MAX_POSITION_SIZE:.1%}"
        
        # Check leverage
        if leverage > MAX_LEVERAGE:
            return False, f"Leverage {leverage}x exceeds limit {MAX_LEVERAGE}x"
        
        # Check max positions
        open_positions = len(portfolio.get('positions', []))
        if open_positions >= MAX_OPEN_POSITIONS and decision['action'] in ['LONG', 'SHORT']:
            return False, f"Max positions ({MAX_OPEN_POSITIONS}) already open"
        
        # Check confidence threshold
        if decision['confidence'] < MIN_CONFIDENCE:
            return False, f"Confidence {decision['confidence']}% below minimum threshold ({MIN_CONFIDENCE}%)"
        
        # Check available margin
        available_balance = portfolio.get('available_balance', 0)
        portfolio_value = portfolio.get('total_value', INITIAL_CAPITAL)
        required_margin = (portfolio_value * position_size) / leverage
        
        if required_margin > available_balance:
            return False, f"Insufficient margin (need ${required_margin:,.2f}, have ${available_balance:,.2f})"
        
        # Check stop loss
        if decision.get('stop_loss_percent', 0) < 2 or decision.get('stop_loss_percent', 0) > 8:
            return False, f"Stop loss {decision.get('stop_loss_percent')}% outside valid range (2-8%)"
        
        # Check take profit
        if decision.get('take_profit_percent', 0) < 5:
            return False, f"Take profit {decision.get('take_profit_percent')}% too low (min 5%)"
        
        # All validations passed
        return True, "Trade validated"
    
    def emergency_shutdown(self):
        """Emergency shutdown - close all positions and halt trading"""
        self.circuit_breaker_level = 'LEVEL_4'
        self.circuit_breaker_until = datetime.now(timezone.utc) + timedelta(days=365)  # Effectively permanent
        print("🚨 EMERGENCY SHUTDOWN ACTIVATED 🚨")
        print("   Drawdown approaching maximum allowed limit")
        print("   All trading halted to prevent disqualification")
    
    def get_risk_summary(self) -> Dict:
        """Get current risk status summary"""
        return {
            'current_drawdown': round(self.current_drawdown * 100, 2),
            'peak_value': round(self.peak_value, 2),
            'current_value': round(self.current_value, 2),
            'circuit_breaker_level': self.circuit_breaker_level,
            'circuit_breaker_active': self.circuit_breaker_until is not None and datetime.now(timezone.utc) < self.circuit_breaker_until,
            'daily_pnl': round(((self.current_value - self.daily_start_value) / self.daily_start_value) * 100, 2),
            'trades_today': self.total_trades_today
        }


# Global risk manager instance
_risk_manager_instance = None

def get_risk_manager() -> RiskManager:
    """Get or create risk manager instance"""
    global _risk_manager_instance
    if _risk_manager_instance is None:
        _risk_manager_instance = RiskManager()
    return _risk_manager_instance

