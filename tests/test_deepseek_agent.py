"""
Unit tests for Groq-backed Agent (DeepSeekAgent class)
Tests LLM parsing and validation (offline)
"""
import pytest
import json
from deepseek_agent import DeepSeekAgent


class TestDeepSeekAgent:
    """Test suite for DeepSeekAgent class"""
    
    def test_initialization(self):
        """Test agent initializes correctly"""
        agent = DeepSeekAgent()
        assert agent.total_api_calls == 0
        assert agent.failed_api_calls == 0
    
    def test_parse_json_response_valid(self):
        """Test parsing valid JSON response"""
        agent = DeepSeekAgent()
        
        valid_json = '''
        {
            "action": "LONG",
            "confidence": 85,
            "position_size_percent": 8,
            "leverage": 4,
            "entry_reason": "Strong uptrend with high volume",
            "stop_loss_percent": 4,
            "take_profit_percent": 15,
            "urgency": "MEDIUM"
        }
        '''
        
        decision = agent.parse_json_response(valid_json)
        assert decision['action'] == 'LONG'
        assert decision['confidence'] == 85
        assert decision['leverage'] == 4
    
    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks"""
        agent = DeepSeekAgent()
        
        markdown_json = '''
        Here's my decision:
        ```json
        {
            "action": "SHORT",
            "confidence": 78,
            "position_size_percent": 6,
            "leverage": 3,
            "entry_reason": "Overbought RSI",
            "stop_loss_percent": 5,
            "take_profit_percent": 12,
            "urgency": "HIGH"
        }
        ```
        '''
        
        decision = agent.parse_json_response(markdown_json)
        assert decision['action'] == 'SHORT'
        assert decision['confidence'] == 78
    
    def test_validate_decision_all_fields(self):
        """Test decision validation checks all required fields"""
        agent = DeepSeekAgent()
        
        # Valid decision
        valid_decision = {
            'action': 'LONG',
            'confidence': 85,
            'position_size_percent': 8,
            'leverage': 4,
            'entry_reason': 'Test reason',
            'stop_loss_percent': 4,
            'take_profit_percent': 15,
            'urgency': 'MEDIUM'
        }
        
        assert agent.validate_decision(valid_decision) == True
        
        # Missing field
        incomplete = valid_decision.copy()
        del incomplete['leverage']
        assert agent.validate_decision(incomplete) == False
    
    def test_validate_decision_ranges(self):
        """Test validation checks value ranges"""
        agent = DeepSeekAgent()
        
        base_decision = {
            'action': 'LONG',
            'confidence': 85,
            'position_size_percent': 8,
            'leverage': 4,
            'entry_reason': 'Test',
            'stop_loss_percent': 4,
            'take_profit_percent': 15,
            'urgency': 'MEDIUM'
        }
        
        # Test confidence range (0-100)
        invalid = base_decision.copy()
        invalid['confidence'] = 150
        assert agent.validate_decision(invalid) == False
        
        # Test position size range (0-10)
        invalid = base_decision.copy()
        invalid['position_size_percent'] = 15
        assert agent.validate_decision(invalid) == False
        
        # Test leverage range (1-5)
        invalid = base_decision.copy()
        invalid['leverage'] = 7
        assert agent.validate_decision(invalid) == False
        
        # Test stop loss range (2-8)
        invalid = base_decision.copy()
        invalid['stop_loss_percent'] = 10
        assert agent.validate_decision(invalid) == False
    
    def test_validate_decision_action_types(self):
        """Test validation of action types"""
        agent = DeepSeekAgent()
        
        base = {
            'action': 'LONG',
            'confidence': 85,
            'position_size_percent': 8,
            'leverage': 4,
            'entry_reason': 'Test',
            'stop_loss_percent': 4,
            'take_profit_percent': 15,
            'urgency': 'MEDIUM'
        }
        
        # Valid actions
        for action in ['LONG', 'SHORT', 'CLOSE', 'HOLD']:
            decision = base.copy()
            decision['action'] = action
            assert agent.validate_decision(decision) == True, f"{action} should be valid"
        
        # Invalid action
        invalid = base.copy()
        invalid['action'] = 'BUY'  # Should be LONG
        assert agent.validate_decision(invalid) == False
    
    def test_get_hold_decision(self):
        """Test HOLD decision generation"""
        agent = DeepSeekAgent()
        
        hold = agent._get_hold_decision("Test reason")
        
        assert hold['action'] == 'HOLD'
        assert hold['confidence'] == 0
        assert hold['position_size_percent'] == 0
        assert 'Test reason' in hold['entry_reason']
        assert agent.validate_decision(hold) == True
    
    def test_fallback_decision(self):
        """Test fallback decision logic when API unavailable"""
        agent = DeepSeekAgent()
        
        market_data = {
            'symbol': 'BTCUSDT',
            'price': 50000,
            'regime': 'NEUTRAL'
        }
        
        portfolio = {
            'positions': [],
            'total_value': 100000
        }
        
        decision = agent.get_fallback_decision(market_data, portfolio)
        
        # Should return HOLD when no positions
        assert decision['action'] == 'HOLD'
        
        # Should return CLOSE when position is losing
        portfolio['positions'] = [{
            'symbol': 'BTCUSDT',
            'pnl_percent': -6
        }]
        
        decision = agent.get_fallback_decision(market_data, portfolio)
        assert decision['action'] == 'CLOSE'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

