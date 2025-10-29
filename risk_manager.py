"""
Risk Management System
Handles position sizing, circuit breakers, drawdown monitoring, and risk limits
"""
from typing import Dict, Tuple
from datetime import datetime, timedelta, timezone
from config import (
    INITIAL_CAPITAL, MAX_DRAWDOWN, MAX_LEVERAGE, MAX_POSITION_SIZE,
    MAX_OPEN_POSITIONS, CIRCUIT_BREAKERS, MIN_CONFIDENCE,
    ENABLE_VOLATILITY_TRADING, SCALP_POSITION_SIZE,
    BASE_LEVERAGE, HIGH_CONFIDENCE_LEVERAGE, LEVERAGE_THRESHOLD,
    MAX_POSITIONS_PER_SYMBOL, MAX_CORRELATED_POSITIONS, MAX_PORTFOLIO_RISK,
    HIGH_CONFIDENCE_SIZE, MEDIUM_CONFIDENCE_SIZE, LOW_CONFIDENCE_SIZE
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
        balance: float,
        confidence: float, 
        market_data: Dict = None
    ) -> Dict:
        """
        Calculate optimal position size based on confidence
        Returns: dict with 'size' (dollar amount), 'leverage', and 'size_percent'
        """
        from config import (
            HIGH_CONFIDENCE_LEVERAGE, 
            BASE_LEVERAGE,
            HIGH_CONFIDENCE_POSITION_SIZE, 
            MEDIUM_CONFIDENCE_POSITION_SIZE, 
            LOW_CONFIDENCE_POSITION_SIZE
        )
        
        # Fixed dollar amounts based on confidence
        if confidence >= 75:
            position_size_dollars = HIGH_CONFIDENCE_POSITION_SIZE  # $1200 for 75%+ confidence
            leverage = HIGH_CONFIDENCE_LEVERAGE
        elif confidence >= 70:
            position_size_dollars = MEDIUM_CONFIDENCE_POSITION_SIZE  # $1000 for 70-74% confidence
            leverage = BASE_LEVERAGE
        else:
            # Below 70% - use smaller fixed amount
            position_size_dollars = LOW_CONFIDENCE_POSITION_SIZE  # $800 for <70% confidence
            leverage = BASE_LEVERAGE
        
        # Calculate percentage for reporting/validation purposes
        size_percent = position_size_dollars / balance if balance > 0 else 0
        
        # Cap position size to available balance
        if position_size_dollars > balance:
            position_size_dollars = balance * 0.95  # Use 95% of balance max
            size_percent = 0.95
        
        return {
            'size': position_size_dollars,
            'leverage': leverage,
            'size_percent': size_percent * 100
        }
    
    def calculate_optimal_leverage(self, confidence: float, regime: str) -> int:
        """
        Dynamic leverage based on confidence only.
        - < LEVERAGE_THRESHOLD: BASE_LEVERAGE
        - >= LEVERAGE_THRESHOLD: HIGH_CONFIDENCE_LEVERAGE
        Applies circuit breaker and MAX_LEVERAGE caps.
        """
        leverage = HIGH_CONFIDENCE_LEVERAGE if confidence >= LEVERAGE_THRESHOLD else BASE_LEVERAGE
        
        # Apply circuit breaker limits if active
        if self.circuit_breaker_level:
            max_cb_leverage = CIRCUIT_BREAKERS[self.circuit_breaker_level]['max_leverage']
            leverage = min(leverage, max_cb_leverage)
        
        # Enforce global hard limit
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
        leverage: int,
        symbol: str = None
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
        
        # Get symbol (from parameter or extract from decision/portfolio)
        if not symbol:
            # Try to extract from decision or portfolio positions
            symbol = decision.get('symbol') or portfolio.get('positions', [{}])[0].get('symbol') if portfolio.get('positions') else None
        
        # Portfolio risk validation (only for new LONG/SHORT trades)
        if decision['action'] in ['LONG', 'SHORT'] and symbol:
            positions = portfolio.get('positions', [])
            
            # Check 1: No pyramiding (max 1 position per symbol)
            existing_symbol_positions = [p for p in positions if p.get('symbol') == symbol]
            if len(existing_symbol_positions) >= MAX_POSITIONS_PER_SYMBOL:
                return False, f"Symbol {symbol} already has {len(existing_symbol_positions)} position(s) (max {MAX_POSITIONS_PER_SYMBOL})"
            
            # Check 2: Correlation limits (max 3 correlated crypto positions)
            crypto_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
            crypto_positions = [p for p in positions if p.get('symbol') in crypto_symbols]
            if symbol in crypto_symbols and len(crypto_positions) >= MAX_CORRELATED_POSITIONS:
                return False, f"Max correlated crypto positions ({MAX_CORRELATED_POSITIONS}) already open"
            
            # Check 3: Total portfolio risk
            # Risk = position size as % of total portfolio value
            portfolio_value = portfolio.get('total_value', INITIAL_CAPITAL)
            new_trade_risk = position_size  # position_size is already a decimal (0.05 = 5%)
            
            # Calculate total risk from existing positions
            # Risk for each position = (position_value / portfolio_value)
            total_risk = 0.0
            for p in positions:
                pos_quantity = abs(p.get('quantity', 0))
                pos_price = p.get('entry_price') or p.get('current_price', 0)
                if pos_price > 0:
                    position_value = pos_quantity * pos_price
                    position_risk = position_value / max(portfolio_value, 1)
                    total_risk += position_risk
            
            # Add new trade risk (new position_size as % of portfolio)
            total_risk_with_new = total_risk + new_trade_risk
            
            if total_risk_with_new > MAX_PORTFOLIO_RISK:
                return False, f"Total portfolio risk {total_risk_with_new:.1%} exceeds limit {MAX_PORTFOLIO_RISK:.1%} (current: {total_risk:.1%}, new trade: {new_trade_risk:.1%})"
        
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

def get_risk_manager(initial_capital: float = INITIAL_CAPITAL) -> RiskManager:
    """Get or create risk manager instance. Optionally set initial capital on first create."""
    global _risk_manager_instance
    if _risk_manager_instance is None:
        _risk_manager_instance = RiskManager(initial_capital=initial_capital)
    return _risk_manager_instance

