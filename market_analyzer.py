"""
Market Analysis Module
Identifies trade setups, calculates confidence scores, and builds LLM context
"""
from typing import Dict, List
import json


class MarketAnalyzer:
    """Analyzes market conditions and generates trade setups"""
    
    def __init__(self):
        self.setup_history = []
    
    def find_trade_setups(self, market_data: Dict) -> List[Dict]:
        """
        Identify high-probability trade setups based on market data
        Returns list of potential setups with confidence scores
        """
        setups = []
        
        if 'error' in market_data or not market_data.get('indicators'):
            return setups
        
        indicators = market_data['indicators']
        regime = market_data['regime']
        symbol = market_data['symbol']
        price = market_data['price']
        
        # Setup 1: Trend Following
        trend_setup = self._identify_trend_setup(indicators, regime, symbol, price)
        if trend_setup:
            setups.append(trend_setup)
        
        # Setup 2: Breakout Trading
        breakout_setup = self._identify_breakout_setup(indicators, regime, symbol, price, market_data)
        if breakout_setup:
            setups.append(breakout_setup)
        
        # Setup 3: RSI Reversal
        reversal_setup = self._identify_reversal_setup(indicators, regime, symbol, price)
        if reversal_setup:
            setups.append(reversal_setup)
        
        # Setup 4: Momentum Trade
        momentum_setup = self._identify_momentum_setup(indicators, regime, symbol, price, market_data)
        if momentum_setup:
            setups.append(momentum_setup)
        
        return setups
    
    def _identify_trend_setup(self, indicators: Dict, regime: str, symbol: str, price: float) -> Dict:
        """Identify trend-following opportunities"""
        confidence = 0
        direction = None
        reasons = []
        
        # Strong uptrend conditions
        if regime in ['STRONG_TREND_UP']:
            confidence += 30
            direction = 'LONG'
            reasons.append("Strong uptrend confirmed")
            
            # Additional confirmations
            if indicators['rsi'] > 50 and indicators['rsi'] < 70:
                confidence += 15
                reasons.append("RSI in bullish range")
            
            if indicators['macd_diff'] > 0:
                confidence += 15
                reasons.append("MACD bullish")
            
            if indicators['volume_ratio'] > 1.2:
                confidence += 10
                reasons.append("Above-average volume")
            
            if price > indicators['ema_9'] > indicators['ema_21']:
                confidence += 10
                reasons.append("Price above key EMAs")
        
        # Strong downtrend conditions
        elif regime in ['STRONG_TREND_DOWN']:
            confidence += 30
            direction = 'SHORT'
            reasons.append("Strong downtrend confirmed")
            
            if indicators['rsi'] < 50 and indicators['rsi'] > 30:
                confidence += 15
                reasons.append("RSI in bearish range")
            
            if indicators['macd_diff'] < 0:
                confidence += 15
                reasons.append("MACD bearish")
            
            if indicators['volume_ratio'] > 1.2:
                confidence += 10
                reasons.append("Above-average volume")
            
            if price < indicators['ema_9'] < indicators['ema_21']:
                confidence += 10
                reasons.append("Price below key EMAs")
        
        if confidence >= 60 and direction:
            return {
                'type': 'TREND_FOLLOWING',
                'symbol': symbol,
                'direction': direction,
                'confidence': min(confidence, 95),
                'entry_price': price,
                'reasons': reasons
            }
        
        return None
    
    def _identify_breakout_setup(self, indicators: Dict, regime: str, symbol: str, price: float, market_data: Dict) -> Dict:
        """Identify breakout opportunities"""
        confidence = 0
        direction = None
        reasons = []
        
        bb_position = indicators['bb_position']
        recent_high = indicators['recent_high']
        recent_low = indicators['recent_low']
        
        # Upward breakout
        if regime in ['BREAKOUT_UP'] or (bb_position > 85 and indicators['volume_ratio'] > 1.5):
            confidence += 35
            direction = 'LONG'
            reasons.append("Price breaking out above resistance")
            
            if price > recent_high * 0.999:  # Near or above recent high
                confidence += 20
                reasons.append("Breaking recent high")
            
            if indicators['rsi'] > 60:
                confidence += 15
                reasons.append("Strong momentum (RSI)")
            
            if market_data.get('price_change_24h', 0) > 3:
                confidence += 10
                reasons.append("Strong 24h performance")
        
        # Downward breakout
        elif regime in ['BREAKOUT_DOWN'] or (bb_position < 15 and indicators['volume_ratio'] > 1.5):
            confidence += 35
            direction = 'SHORT'
            reasons.append("Price breaking down below support")
            
            if price < recent_low * 1.001:  # Near or below recent low
                confidence += 20
                reasons.append("Breaking recent low")
            
            if indicators['rsi'] < 40:
                confidence += 15
                reasons.append("Strong bearish momentum")
            
            if market_data.get('price_change_24h', 0) < -3:
                confidence += 10
                reasons.append("Weak 24h performance")
        
        if confidence >= 65 and direction:
            return {
                'type': 'BREAKOUT',
                'symbol': symbol,
                'direction': direction,
                'confidence': min(confidence, 95),
                'entry_price': price,
                'reasons': reasons
            }
        
        return None
    
    def _identify_reversal_setup(self, indicators: Dict, regime: str, symbol: str, price: float) -> Dict:
        """Identify mean reversion opportunities"""
        confidence = 0
        direction = None
        reasons = []
        
        rsi = indicators['rsi']
        bb_position = indicators['bb_position']
        
        # Oversold reversal (buy)
        if rsi < 30 and bb_position < 20:
            confidence += 40
            direction = 'LONG'
            reasons.append("Oversold conditions (RSI + BB)")
            
            if indicators['macd_diff'] > 0:  # MACD turning up
                confidence += 20
                reasons.append("MACD showing bullish divergence")
            
            if regime not in ['STRONG_TREND_DOWN', 'BREAKOUT_DOWN']:
                confidence += 15
                reasons.append("Not in strong downtrend")
        
        # Overbought reversal (sell)
        elif rsi > 70 and bb_position > 80:
            confidence += 40
            direction = 'SHORT'
            reasons.append("Overbought conditions (RSI + BB)")
            
            if indicators['macd_diff'] < 0:  # MACD turning down
                confidence += 20
                reasons.append("MACD showing bearish divergence")
            
            if regime not in ['STRONG_TREND_UP', 'BREAKOUT_UP']:
                confidence += 15
                reasons.append("Not in strong uptrend")
        
        if confidence >= 60 and direction:
            return {
                'type': 'REVERSAL',
                'symbol': symbol,
                'direction': direction,
                'confidence': min(confidence, 90),
                'entry_price': price,
                'reasons': reasons
            }
        
        return None
    
    def _identify_momentum_setup(self, indicators: Dict, regime: str, symbol: str, price: float, market_data: Dict) -> Dict:
        """Identify strong momentum plays"""
        confidence = 0
        direction = None
        reasons = []
        
        price_change_4h = indicators.get('price_change_4h', 0)
        price_change_24h = indicators.get('price_change_24h', 0)
        
        # Strong upward momentum
        if price_change_4h > 4 and price_change_24h > 6:
            confidence += 35
            direction = 'LONG'
            reasons.append(f"Strong upward momentum ({price_change_24h:.1f}% in 24h)")
            
            if indicators['rsi'] > 55 and indicators['rsi'] < 75:
                confidence += 20
                reasons.append("RSI in momentum zone")
            
            if indicators['volume_ratio'] > 1.5:
                confidence += 15
                reasons.append("High volume confirmation")
            
            if regime in ['STRONG_TREND_UP', 'BREAKOUT_UP']:
                confidence += 10
                reasons.append("Aligned with trend")
        
        # Strong downward momentum
        elif price_change_4h < -4 and price_change_24h < -6:
            confidence += 35
            direction = 'SHORT'
            reasons.append(f"Strong downward momentum ({price_change_24h:.1f}% in 24h)")
            
            if indicators['rsi'] < 45 and indicators['rsi'] > 25:
                confidence += 20
                reasons.append("RSI in bearish momentum zone")
            
            if indicators['volume_ratio'] > 1.5:
                confidence += 15
                reasons.append("High volume confirmation")
            
            if regime in ['STRONG_TREND_DOWN', 'BREAKOUT_DOWN']:
                confidence += 10
                reasons.append("Aligned with trend")
        
        if confidence >= 65 and direction:
            return {
                'type': 'MOMENTUM',
                'symbol': symbol,
                'direction': direction,
                'confidence': min(confidence, 95),
                'entry_price': price,
                'reasons': reasons
            }
        
        return None
    
    def calculate_confidence_score(self, setup: Dict) -> float:
        """Calculate overall confidence score for a trade setup"""
        if not setup:
            return 0
        
        return setup.get('confidence', 0)
    
    def build_llm_context(self, market_data: Dict, portfolio: Dict, day_number: int) -> str:
        """
        Build comprehensive context string for LLM decision-making
        """
        symbol = market_data.get('symbol', 'UNKNOWN')
        price = market_data.get('price', 0)
        regime = market_data.get('regime', 'UNKNOWN')
        indicators = market_data.get('indicators', {})
        
        # Find best setups
        setups = self.find_trade_setups(market_data)
        best_setup = max(setups, key=lambda x: x['confidence']) if setups else None
        
        # Portfolio status
        portfolio_value = portfolio.get('total_value', 100000)
        available_balance = portfolio.get('available_balance', 100000)
        drawdown = portfolio.get('drawdown_percent', 0)
        open_positions = portfolio.get('positions', [])
        position_count = len(open_positions)
        
        # Check if we already have a position in this symbol
        existing_position = None
        for pos in open_positions:
            if pos.get('symbol') == symbol:
                existing_position = pos
                break
        
        # Build context
        context = f"""
TRADING DAY: {day_number}/14

ASSET: {symbol}
Current Price: ${price:,.2f}
24h Change: {market_data.get('price_change_24h', 0):+.2f}%
Market Regime: {regime}

TECHNICAL INDICATORS:
- RSI: {indicators.get('rsi', 0):.1f}
- MACD: {'Bullish' if indicators.get('macd_diff', 0) > 0 else 'Bearish'} (diff: {indicators.get('macd_diff', 0):.2f})
- EMA Alignment: Price ${price:.2f} vs EMA9 ${indicators.get('ema_9', 0):.2f} vs EMA21 ${indicators.get('ema_21', 0):.2f}
- Bollinger Bands: Position {indicators.get('bb_position', 50):.0f}% (0=bottom, 100=top)
- Volume: {indicators.get('volume_ratio', 1):.2f}x average
- ATR: {indicators.get('atr_percent', 0):.2f}% (volatility)
- Recent High: ${indicators.get('recent_high', 0):,.2f} | Recent Low: ${indicators.get('recent_low', 0):,.2f}

TRADE SETUP ANALYSIS:
"""
        
        if best_setup:
            context += f"""
Best Setup Found: {best_setup['type']}
Direction: {best_setup['direction']}
Confidence: {best_setup['confidence']:.0f}%
Reasons:
"""
            for reason in best_setup['reasons']:
                context += f"  • {reason}\n"
        else:
            context += "No high-confidence setup identified.\n"
        
        context += f"""
PORTFOLIO STATUS:
- Total Value: ${portfolio_value:,.2f}
- Available Balance: ${available_balance:,.2f}
- Current Drawdown: {drawdown:.1f}%
- Open Positions: {position_count}/3
"""
        
        if existing_position:
            context += f"""
- EXISTING POSITION IN {symbol}:
  Side: {existing_position.get('side')}
  Entry: ${existing_position.get('entry_price', 0):,.2f}
  Current PnL: {existing_position.get('pnl_percent', 0):+.2f}%
  Leverage: {existing_position.get('leverage')}x
"""
        
        context += f"""
COMPETITION STATUS:
- Days Remaining: {14 - day_number}
- Pressure Level: {'🔴 HIGH - Need aggressive gains' if day_number > 10 else '🟡 MEDIUM - Steady growth' if day_number > 5 else '🟢 LOW - Building foundation'}

YOUR DECISION:
Analyze the above data and provide your trading decision in strict JSON format.
"""
        
        return context


# Singleton instance
_analyzer_instance = None

def get_analyzer() -> MarketAnalyzer:
    """Get or create market analyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = MarketAnalyzer()
    return _analyzer_instance

