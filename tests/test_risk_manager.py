"""
Unit tests for Risk Manager
Tests critical risk management functionality
"""
import pytest
from risk_manager import RiskManager


class TestRiskManager:
    """Test suite for RiskManager class"""
    
    def test_initialization(self):
        """Test risk manager initializes correctly"""
        rm = RiskManager(100000)
        assert rm.initial_capital == 100000
        assert rm.current_drawdown == 0.0
        assert rm.peak_value == 100000
    
    def test_position_sizing_within_limits(self):
        """Test that position sizing never exceeds maximum"""
        rm = RiskManager(100000)
        
        # Test various scenarios
        test_cases = [
            (90, "STRONG_TREND_UP", 1, 0.0),  # High confidence, early, no drawdown
            (70, "RANGING", 14, 0.30),         # Low confidence, late, high drawdown
            (85, "BREAKOUT_UP", 7, 0.10),      # Medium scenario
        ]
        
        for confidence, regime, day, dd in test_cases:
            size = rm.calculate_position_size(confidence, regime, day, dd)
            assert 0 <= size <= 0.10, f"Position size {size} exceeds 10% limit"
    
    def test_leverage_within_limits(self):
        """Test that leverage never exceeds maximum"""
        rm = RiskManager(100000)
        
        test_cases = [
            (95, "STRONG_TREND_UP"),
            (70, "VOLATILE"),
            (80, "RANGING"),
        ]
        
        for confidence, regime in test_cases:
            leverage = rm.calculate_optimal_leverage(confidence, regime)
            assert 1 <= leverage <= 5, f"Leverage {leverage} outside 1-5 range"
    
    def test_circuit_breaker_level_1(self):
        """Test circuit breaker at 25% drawdown"""
        rm = RiskManager(100000)
        rm.current_value = 100000
        rm.update_portfolio_metrics(75000)  # 25% drawdown
        
        can_trade, reason = rm.check_circuit_breakers()
        assert "WARNING" in reason or "25%" in reason
    
    def test_circuit_breaker_level_4(self):
        """Test emergency stop at 38% drawdown"""
        rm = RiskManager(100000)
        rm.current_value = 100000
        rm.update_portfolio_metrics(62000)  # 38% drawdown
        
        can_trade, reason = rm.check_circuit_breakers()
        assert can_trade == False, "Should halt trading at 38% drawdown"
        assert "EMERGENCY" in reason or "38%" in reason
    
    def test_position_size_decreases_with_drawdown(self):
        """Test that position sizes decrease as drawdown increases"""
        rm = RiskManager(100000)
        
        # Calculate size at different drawdown levels
        size_0 = rm.calculate_position_size(85, "STRONG_TREND_UP", 5, 0.0)
        size_20 = rm.calculate_position_size(85, "STRONG_TREND_UP", 5, 0.20)
        size_30 = rm.calculate_position_size(85, "STRONG_TREND_UP", 5, 0.30)
        
        assert size_0 > size_20 > size_30, "Position size should decrease with drawdown"
    
    def test_validate_trade_checks(self):
        """Test trade validation catches violations"""
        rm = RiskManager(100000)
        
        # Valid decision
        valid_decision = {
            'action': 'LONG',
            'confidence': 85,
            'stop_loss_percent': 4,
            'take_profit_percent': 15
        }
        
        portfolio = {
            'total_value': 100000,
            'available_balance': 90000,
            'positions': []
        }
        
        is_valid, msg = rm.validate_trade(valid_decision, portfolio, 0.08, 3)
        assert is_valid == True, f"Valid trade rejected: {msg}"
        
        # Test invalid confidence
        invalid_decision = valid_decision.copy()
        invalid_decision['confidence'] = 65  # Below 70
        is_valid, msg = rm.validate_trade(invalid_decision, portfolio, 0.08, 3)
        assert is_valid == False, "Should reject low confidence"
        
        # Test excessive position size
        is_valid, msg = rm.validate_trade(valid_decision, portfolio, 0.15, 3)
        assert is_valid == False, "Should reject excessive position size"
        
        # Test excessive leverage
        is_valid, msg = rm.validate_trade(valid_decision, portfolio, 0.08, 7)
        assert is_valid == False, "Should reject excessive leverage"
    
    def test_drawdown_calculation(self):
        """Test drawdown calculation"""
        rm = RiskManager(100000)
        
        # Peak at 100k, drop to 70k = 30% drawdown
        rm.peak_value = 100000
        rm.current_value = 100000
        rm.update_portfolio_metrics(70000)
        
        assert abs(rm.current_drawdown - 0.30) < 0.01, "Drawdown calculation incorrect"
        
        # Recovery to 90k = 10% drawdown from peak
        rm.update_portfolio_metrics(90000)
        assert abs(rm.current_drawdown - 0.10) < 0.01, "Drawdown should be from peak"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

