"""
DeepSeek LLM Agent
Integrates with DeepSeek API for AI-powered trading decisions
"""
import json
import time
from typing import Dict, Optional
import requests
from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL,
    DEEPSEEK_TEMPERATURE, DEEPSEEK_MAX_TOKENS, DEEPSEEK_TIMEOUT,
    SYSTEM_PROMPT, MAX_API_RETRIES, RETRY_BACKOFF_MULTIPLIER
)


class DeepSeekAgent:
    """AI agent using DeepSeek LLM for trading decisions"""
    
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.api_url = DEEPSEEK_API_URL
        self.model = DEEPSEEK_MODEL
        self.decision_cache = {}  # Cache similar decisions to reduce API calls
        self.total_api_calls = 0
        self.failed_api_calls = 0
    
    def get_decision(
        self, 
        market_data: Dict, 
        portfolio: Dict, 
        day_number: int,
        context_override: str = None
    ) -> Dict:
        """
        Get trading decision from DeepSeek LLM
        Returns: Decision dictionary with action, confidence, position size, etc.
        """
        try:
            # Build context for LLM
            from market_analyzer import get_analyzer
            analyzer = get_analyzer()
            
            if context_override:
                context = context_override
            else:
                context = analyzer.build_llm_context(market_data, portfolio, day_number)
            
            # Query DeepSeek
            response_text = self._query_deepseek(context)
            
            # Parse response
            decision = self.parse_json_response(response_text)
            
            # Validate decision
            if not self.validate_decision(decision):
                # Return safe HOLD decision if validation fails
                return self._get_hold_decision("Invalid LLM response - validation failed")
            
            return decision
            
        except Exception as e:
            print(f"Error getting LLM decision: {e}")
            self.failed_api_calls += 1
            return self._get_hold_decision(f"Error: {str(e)}")
    
    def _query_deepseek(self, prompt: str) -> str:
        """Query DeepSeek API with retry logic"""
        self.total_api_calls += 1
        
        for attempt in range(MAX_API_RETRIES):
            try:
                response = requests.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": DEEPSEEK_TEMPERATURE,
                        "max_tokens": DEEPSEEK_MAX_TOKENS,
                        "response_format": {"type": "json_object"}
                    },
                    timeout=DEEPSEEK_TIMEOUT
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content']
                else:
                    error_msg = f"DeepSeek API error: {response.status_code} - {response.text}"
                    print(error_msg)
                    
                    if attempt < MAX_API_RETRIES - 1:
                        wait_time = RETRY_BACKOFF_MULTIPLIER ** attempt
                        print(f"Retrying in {wait_time}s... (attempt {attempt + 1}/{MAX_API_RETRIES})")
                        time.sleep(wait_time)
                    else:
                        raise Exception(error_msg)
                        
            except requests.exceptions.Timeout:
                print(f"DeepSeek API timeout (attempt {attempt + 1}/{MAX_API_RETRIES})")
                if attempt < MAX_API_RETRIES - 1:
                    time.sleep(RETRY_BACKOFF_MULTIPLIER ** attempt)
                else:
                    raise
                    
            except Exception as e:
                print(f"Error querying DeepSeek: {e}")
                if attempt < MAX_API_RETRIES - 1:
                    time.sleep(RETRY_BACKOFF_MULTIPLIER ** attempt)
                else:
                    raise
        
        raise Exception("Max retries exceeded for DeepSeek API")
    
    def parse_json_response(self, response_text: str) -> Dict:
        """
        Parse JSON response from LLM
        Handles various formats and extracts the decision JSON
        """
        try:
            # Try direct JSON parse
            decision = json.loads(response_text)
            return decision
            
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
                return json.loads(json_str)
            
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
                return json.loads(json_str)
            
            # Try to find JSON object in text
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
            
            # If all else fails, return HOLD
            print(f"Failed to parse LLM response: {response_text[:200]}")
            return self._get_hold_decision("Could not parse LLM response")
    
    def validate_decision(self, decision: Dict) -> bool:
        """
        Validate that the decision contains all required fields and valid values
        """
        # Check required fields
        required_fields = [
            'action', 'confidence', 'position_size_percent',
            'leverage', 'entry_reason', 'stop_loss_percent',
            'take_profit_percent', 'urgency'
        ]
        
        for field in required_fields:
            if field not in decision:
                print(f"Missing required field: {field}")
                return False
        
        # Validate action
        valid_actions = ['LONG', 'SHORT', 'CLOSE', 'HOLD']
        if decision['action'] not in valid_actions:
            print(f"Invalid action: {decision['action']}")
            return False
        
        # Validate confidence (0-100)
        try:
            confidence = float(decision['confidence'])
            if not 0 <= confidence <= 100:
                print(f"Confidence out of range: {confidence}")
                return False
        except (ValueError, TypeError):
            print(f"Invalid confidence value: {decision['confidence']}")
            return False
        
        # Validate position size (0-10%)
        try:
            position_size = float(decision['position_size_percent'])
            if not 0 <= position_size <= 10:
                print(f"Position size out of range: {position_size}")
                return False
        except (ValueError, TypeError):
            print(f"Invalid position size: {decision['position_size_percent']}")
            return False
        
        # Validate leverage (1-5)
        try:
            leverage = int(decision['leverage'])
            if not 1 <= leverage <= 5:
                print(f"Leverage out of range: {leverage}")
                return False
        except (ValueError, TypeError):
            print(f"Invalid leverage: {decision['leverage']}")
            return False
        
        # Validate stop loss (2-8%)
        try:
            stop_loss = float(decision['stop_loss_percent'])
            if not 2 <= stop_loss <= 8:
                print(f"Stop loss out of range: {stop_loss}")
                return False
        except (ValueError, TypeError):
            print(f"Invalid stop loss: {decision['stop_loss_percent']}")
            return False
        
        # Validate take profit (5-30%)
        try:
            take_profit = float(decision['take_profit_percent'])
            if not 5 <= take_profit <= 30:
                print(f"Take profit out of range: {take_profit}")
                return False
        except (ValueError, TypeError):
            print(f"Invalid take profit: {decision['take_profit_percent']}")
            return False
        
        # Validate urgency
        valid_urgency = ['LOW', 'MEDIUM', 'HIGH']
        if decision['urgency'] not in valid_urgency:
            print(f"Invalid urgency: {decision['urgency']}")
            return False
        
        # All validations passed
        return True
    
    def _get_hold_decision(self, reason: str) -> Dict:
        """Return a safe HOLD decision"""
        return {
            'action': 'HOLD',
            'confidence': 0,
            'position_size_percent': 0,
            'leverage': 1,
            'entry_reason': reason,
            'stop_loss_percent': 3,
            'take_profit_percent': 10,
            'urgency': 'LOW'
        }
    
    def get_fallback_decision(self, market_data: Dict, portfolio: Dict) -> Dict:
        """
        Fallback logic when DeepSeek API is unavailable
        Uses simple rule-based decision making
        """
        print("⚠️ Using fallback decision logic (API unavailable)")
        
        # Check if we have open positions - if so, consider closing risky ones
        positions = portfolio.get('positions', [])
        
        for pos in positions:
            # Close positions that are deep underwater
            if pos.get('pnl_percent', 0) < -5:
                return {
                    'action': 'CLOSE',
                    'confidence': 80,
                    'position_size_percent': 0,
                    'leverage': 1,
                    'entry_reason': 'Fallback: Closing losing position',
                    'stop_loss_percent': 3,
                    'take_profit_percent': 10,
                    'urgency': 'HIGH'
                }
        
        # Otherwise, hold
        return self._get_hold_decision("Fallback: API unavailable, avoiding new positions")
    
    def get_stats(self) -> Dict:
        """Get API usage statistics"""
        success_rate = ((self.total_api_calls - self.failed_api_calls) / self.total_api_calls * 100) if self.total_api_calls > 0 else 0
        
        return {
            'total_api_calls': self.total_api_calls,
            'failed_api_calls': self.failed_api_calls,
            'success_rate': round(success_rate, 2)
        }


# Global DeepSeek agent instance
_agent_instance = None

def get_deepseek_agent() -> DeepSeekAgent:
    """Get or create DeepSeek agent instance"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = DeepSeekAgent()
    return _agent_instance

