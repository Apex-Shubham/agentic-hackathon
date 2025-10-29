"""
Market Analysis Module - ENHANCED VERSION
Improved trade setups with multi-confirmation signals and better risk/reward
"""
from typing import Dict, List, Optional
import json
from analytics.performance_tracker import get_performance_tracker


class MarketAnalyzer:
    """Analyzes market conditions and generates high-quality trade setups"""
    
    def __init__(self):
        self.setup_history = []
        self.min_setup_confidence = 70  # Only consider setups with 70%+ confidence
        self.perf_tracker = get_performance_tracker()
    
    def find_trade_setups(self, market_data: Dict) -> List[Dict]:
        """
        Identify high-probability trade setups with enhanced multi-confirmation logic
        Returns list of potential setups with confidence scores
        """
        setups = []
        # Build assessment scaffold
        assessment = {
            'symbol': None,
            'regime': None,
            'price': None,
            'indicators_snapshot': {},
            'strategy_checks': [],
            'shortlisted': []
        }
        
        if 'error' in market_data or not market_data.get('indicators'):
            return setups
        
        indicators = market_data['indicators']
        regime = market_data['regime']
        symbol = market_data['symbol']
        price = market_data['price']
        assessment['symbol'] = symbol
        assessment['regime'] = regime
        assessment['price'] = price
        # capture a compact snapshot of key indicators if present
        for key in ['ema_9','ema_21','ema_50','rsi','macd_diff','bb_upper','bb_lower','atr','volume','volume_ratio']:
            if key in indicators:
                assessment['indicators_snapshot'][key] = indicators.get(key)
        
        # Setup 1: Enhanced Trend Following with Multi-Timeframe Confirmation
        trend_setup = self._identify_trend_setup_enhanced(indicators, regime, symbol, price)
        assessment['strategy_checks'].append({
            'name': 'trend_following',
            'accepted': bool(trend_setup and trend_setup.get('confidence', 0) >= self.min_setup_confidence),
            'confidence': (trend_setup or {}).get('confidence', 0),
            'direction': (trend_setup or {}).get('direction'),
            'reasons': (trend_setup or {}).get('reasons')
        })
        if trend_setup and trend_setup['confidence'] >= self.min_setup_confidence:
            setups.append(trend_setup)
        
        # Setup 2: Smart Breakout with Volume Confirmation
        breakout_setup = self._identify_breakout_setup_enhanced(indicators, regime, symbol, price, market_data)
        assessment['strategy_checks'].append({
            'name': 'breakout',
            'accepted': bool(breakout_setup and breakout_setup.get('confidence', 0) >= self.min_setup_confidence),
            'confidence': (breakout_setup or {}).get('confidence', 0),
            'direction': (breakout_setup or {}).get('direction'),
            'reasons': (breakout_setup or {}).get('reasons')
        })
        if breakout_setup and breakout_setup['confidence'] >= self.min_setup_confidence:
            setups.append(breakout_setup)
        
        # Setup 3: Mean Reversion with Divergence Detection
        reversal_setup = self._identify_reversal_setup_enhanced(indicators, regime, symbol, price)
        assessment['strategy_checks'].append({
            'name': 'mean_reversion',
            'accepted': bool(reversal_setup and reversal_setup.get('confidence', 0) >= self.min_setup_confidence),
            'confidence': (reversal_setup or {}).get('confidence', 0),
            'direction': (reversal_setup or {}).get('direction'),
            'reasons': (reversal_setup or {}).get('reasons')
        })
        if reversal_setup and reversal_setup['confidence'] >= self.min_setup_confidence:
            setups.append(reversal_setup)
        
        # Setup 4: Momentum with Trend Alignment
        momentum_setup = self._identify_momentum_setup_enhanced(indicators, regime, symbol, price, market_data)
        assessment['strategy_checks'].append({
            'name': 'momentum',
            'accepted': bool(momentum_setup and momentum_setup.get('confidence', 0) >= self.min_setup_confidence),
            'confidence': (momentum_setup or {}).get('confidence', 0),
            'direction': (momentum_setup or {}).get('direction'),
            'reasons': (momentum_setup or {}).get('reasons')
        })
        if momentum_setup and momentum_setup['confidence'] >= self.min_setup_confidence:
            setups.append(momentum_setup)
        
        # Setup 5: NEW - Volatility Contraction Pattern
        volatility_setup = self._identify_volatility_breakout(indicators, regime, symbol, price, market_data)
        assessment['strategy_checks'].append({
            'name': 'volatility_breakout',
            'accepted': bool(volatility_setup and volatility_setup.get('confidence', 0) >= self.min_setup_confidence),
            'confidence': (volatility_setup or {}).get('confidence', 0),
            'direction': (volatility_setup or {}).get('direction'),
            'reasons': (volatility_setup or {}).get('reasons')
        })
        if volatility_setup and volatility_setup['confidence'] >= self.min_setup_confidence:
            setups.append(volatility_setup)
        
        # Setup 6: NEW - EMA Crossover with Confirmation
        crossover_setup = self._identify_ema_crossover(indicators, regime, symbol, price)
        assessment['strategy_checks'].append({
            'name': 'ema_crossover',
            'accepted': bool(crossover_setup and crossover_setup.get('confidence', 0) >= self.min_setup_confidence),
            'confidence': (crossover_setup or {}).get('confidence', 0),
            'direction': (crossover_setup or {}).get('direction'),
            'reasons': (crossover_setup or {}).get('reasons')
        })
        if crossover_setup and crossover_setup['confidence'] >= self.min_setup_confidence:
            setups.append(crossover_setup)

        # Record shortlisted setups summary in assessment and write
        assessment['shortlisted'] = [
            {
                'name': s.get('name'),
                'direction': s.get('direction'),
                'confidence': s.get('confidence'),
                'stop_loss_percent': s.get('stop_loss_percent'),
                'take_profit_percent': s.get('take_profit_percent')
            }
            for s in setups
        ]
        try:
            from logger import get_logger
            get_logger().log_assessment(assessment)
        except Exception:
            pass
        
        return setups
    
    def _identify_trend_setup_enhanced(self, indicators: Dict, regime: str, symbol: str, price: float) -> Optional[Dict]:
        """
        ENHANCED: Trend-following with multiple confirmation layers
        - EMA alignment (9 > 21 > 50 for uptrend)
        - Price action above/below key EMAs
        - MACD confirmation
        - RSI in healthy range (not overbought/oversold)
        - Volume above average
        """
        confidence = 0
        direction = None
        reasons = []
        stop_loss_pct = 4
        take_profit_pct = 12
        
        ema_9 = indicators.get('ema_9', 0)
        ema_21 = indicators.get('ema_21', 0)
        ema_50 = indicators.get('ema_50', 0)
        rsi = indicators.get('rsi', 50)
        macd_diff = indicators.get('macd_diff', 0)
        volume_ratio = indicators.get('volume_ratio', 1)
        
        # === BULLISH TREND SETUP ===
        if regime in ['STRONG_TREND_UP']:
            # Core trend confirmation
            confidence += 25
            direction = 'LONG'
            reasons.append("✓ Strong uptrend regime detected")
            
            # Check EMA alignment (bullish stack)
            if ema_9 > ema_21 > ema_50:
                confidence += 20
                reasons.append("✓ Perfect EMA alignment (9>21>50)")
            elif ema_9 > ema_21:
                confidence += 10
                reasons.append("✓ Short-term EMA alignment")
            
            # Price position relative to EMAs
            if price > ema_9 and price > ema_21:
                confidence += 15
                reasons.append("✓ Price trading above key EMAs")
            
            # RSI health check (avoid overbought)
            if 50 < rsi < 70:
                confidence += 15
                reasons.append(f"✓ RSI in healthy bullish zone ({rsi:.1f})")
            elif 45 < rsi <= 50:
                confidence += 8
                reasons.append(f"✓ RSI neutral-bullish ({rsi:.1f})")
            elif rsi >= 70:
                confidence -= 10
                reasons.append(f"⚠ RSI overbought ({rsi:.1f})")
            
            # MACD momentum confirmation
            if macd_diff > 0:
                confidence += 15
                reasons.append("✓ MACD bullish crossover confirmed")
                if macd_diff > 0.1:
                    confidence += 5
                    reasons.append("✓ Strong MACD momentum")
            else:
                confidence -= 8
                reasons.append("⚠ MACD bearish (conflicting signal)")
            
            # Volume validation
            if volume_ratio > 1.3:
                confidence += 10
                reasons.append(f"✓ High volume confirmation ({volume_ratio:.2f}x)")
            elif volume_ratio < 0.8:
                confidence -= 5
                reasons.append("⚠ Below-average volume")
            
            # Adjust stop loss and take profit for trending markets
            stop_loss_pct = 3.5
            take_profit_pct = 15
        
        # === BEARISH TREND SETUP ===
        elif regime in ['STRONG_TREND_DOWN']:
            # Core trend confirmation
            confidence += 25
            direction = 'SHORT'
            reasons.append("✓ Strong downtrend regime detected")
            
            # Check EMA alignment (bearish stack)
            if ema_9 < ema_21 < ema_50:
                confidence += 20
                reasons.append("✓ Perfect EMA alignment (9<21<50)")
            elif ema_9 < ema_21:
                confidence += 10
                reasons.append("✓ Short-term EMA bearish")
            
            # Price position relative to EMAs
            if price < ema_9 and price < ema_21:
                confidence += 15
                reasons.append("✓ Price trading below key EMAs")
            
            # RSI health check (avoid oversold)
            if 30 < rsi < 50:
                confidence += 15
                reasons.append(f"✓ RSI in healthy bearish zone ({rsi:.1f})")
            elif 50 < rsi <= 55:
                confidence += 8
                reasons.append(f"✓ RSI neutral-bearish ({rsi:.1f})")
            elif rsi <= 30:
                confidence -= 10
                reasons.append(f"⚠ RSI oversold ({rsi:.1f})")
            
            # MACD momentum confirmation
            if macd_diff < 0:
                confidence += 15
                reasons.append("✓ MACD bearish crossover confirmed")
                if macd_diff < -0.1:
                    confidence += 5
                    reasons.append("✓ Strong MACD bearish momentum")
            else:
                confidence -= 8
                reasons.append("⚠ MACD bullish (conflicting signal)")
            
            # Volume validation
            if volume_ratio > 1.3:
                confidence += 10
                reasons.append(f"✓ High volume confirmation ({volume_ratio:.2f}x)")
            elif volume_ratio < 0.8:
                confidence -= 5
                reasons.append("⚠ Below-average volume")
            
            # Adjust stop loss and take profit
            stop_loss_pct = 3.5
            take_profit_pct = 15
        
        min_conf_local = 55 if regime == 'VOLATILE' else 70
        if confidence >= min_conf_local and direction:
            return {
                'type': 'TREND_FOLLOWING_ENHANCED',
                'symbol': symbol,
                'direction': direction,
                'confidence': min(confidence, 95),
                'entry_price': price,
                'stop_loss_percent': stop_loss_pct,
                'take_profit_percent': take_profit_pct,
                'reasons': reasons,
                'strategy': 'TREND_FOLLOWING'  # Tag for tracking
            }
        
        # Volatility fallback scoring to avoid zero-confidence in VOLATILE
        try:
            atr = indicators.get('atr', 0)
            current_price = indicators.get('current_price', price)
            atr_ratio = (atr / current_price) if current_price else 0
            volume = indicators.get('volume_ratio', 1.0)
            base_conf = 0
            if atr_ratio > 0.008:
                base_conf += min(40, int(atr_ratio * 4000))
            if volume > 1.2:
                base_conf += min(25, int((volume - 1.0) * 25))
            if regime == 'VOLATILE':
                base_conf += 20
            if rsi < 35 or rsi > 65:
                base_conf += 15
            min_conf = 55 if regime == 'VOLATILE' else 70
            if base_conf >= min_conf:
                inferred_dir = 'LONG' if rsi < 50 else 'SHORT'
                return {
                    'type': 'TREND_FOLLOWING_VOL_FALLBACK',
                    'symbol': symbol,
                    'direction': inferred_dir,
                    'confidence': min(95, base_conf),
                    'entry_price': price,
                    'stop_loss_percent': stop_loss_pct,
                    'take_profit_percent': take_profit_pct,
                    'reasons': reasons + [f"Vol fallback ATR:{atr_ratio:.2%} Vol:{volume:.1f}x RSI:{rsi:.0f}"]
                }
        except Exception:
            pass
        return None
    
    def _identify_breakout_setup_enhanced(self, indicators: Dict, regime: str, symbol: str, price: float, market_data: Dict) -> Optional[Dict]:
        """
        ENHANCED: Breakout detection with volume and momentum confirmation
        - Price breaking key levels (resistance/support)
        - Strong volume spike (>1.5x average)
        - Bollinger Band breakout
        - Recent consolidation followed by expansion
        """
        confidence = 0
        direction = None
        reasons = []
        stop_loss_pct = 4.5
        take_profit_pct = 18
        
        bb_position = indicators.get('bb_position', 50)
        recent_high = indicators.get('recent_high', 0)
        recent_low = indicators.get('recent_low', 0)
        volume_ratio = indicators.get('volume_ratio', 1)
        rsi = indicators.get('rsi', 50)
        price_change_24h = market_data.get('price_change_24h', 0)
        atr_percent = indicators.get('atr_percent', 0)
        
        # === BULLISH BREAKOUT ===
        if regime in ['BREAKOUT_UP'] or (bb_position > 90 and volume_ratio > 1.5):
            confidence += 30
            direction = 'LONG'
            reasons.append("✓ Bullish breakout pattern detected")
            
            # Volume spike confirmation (critical for breakouts)
            if volume_ratio > 2.0:
                confidence += 25
                reasons.append(f"✓ Massive volume spike ({volume_ratio:.2f}x) - strong conviction")
            elif volume_ratio > 1.5:
                confidence += 15
                reasons.append(f"✓ Strong volume ({volume_ratio:.2f}x)")
            else:
                confidence -= 15
                reasons.append("⚠ Insufficient volume for valid breakout")
            
            # Price breaking recent high
            if price > recent_high * 0.998:
                confidence += 20
                reasons.append("✓ Breaking above recent high resistance")
            
            # RSI momentum check
            if 55 < rsi < 75:
                confidence += 15
                reasons.append(f"✓ RSI shows strong momentum ({rsi:.1f})")
            elif rsi >= 75:
                confidence -= 10
                reasons.append(f"⚠ RSI extremely overbought ({rsi:.1f})")
            
            # 24-hour performance validation
            if price_change_24h > 4:
                confidence += 10
                reasons.append(f"✓ Strong 24h momentum ({price_change_24h:+.1f}%)")
            
            # Bollinger Band upper break
            if bb_position > 95:
                confidence += 8
                reasons.append("✓ Breaking above upper Bollinger Band")
            
            # Volatility expansion (breakouts need expansion)
            if atr_percent > 3:
                confidence += 7
                reasons.append(f"✓ Volatility expanding ({atr_percent:.1f}%)")
        
        # === BEARISH BREAKDOWN ===
        elif regime in ['BREAKOUT_DOWN'] or (bb_position < 10 and volume_ratio > 1.5):
            confidence += 30
            direction = 'SHORT'
            reasons.append("✓ Bearish breakdown pattern detected")
            
            # Volume spike confirmation
            if volume_ratio > 2.0:
                confidence += 25
                reasons.append(f"✓ Massive volume spike ({volume_ratio:.2f}x)")
            elif volume_ratio > 1.5:
                confidence += 15
                reasons.append(f"✓ Strong volume ({volume_ratio:.2f}x)")
            else:
                confidence -= 15
                reasons.append("⚠ Insufficient volume for valid breakdown")
            
            # Price breaking recent low
            if price < recent_low * 1.002:
                confidence += 20
                reasons.append("✓ Breaking below recent low support")
            
            # RSI momentum check
            if 25 < rsi < 45:
                confidence += 15
                reasons.append(f"✓ RSI shows strong bearish momentum ({rsi:.1f})")
            elif rsi <= 25:
                confidence -= 10
                reasons.append(f"⚠ RSI extremely oversold ({rsi:.1f})")
            
            # 24-hour performance validation
            if price_change_24h < -4:
                confidence += 10
                reasons.append(f"✓ Strong 24h bearish momentum ({price_change_24h:.1f}%)")
            
            # Bollinger Band lower break
            if bb_position < 5:
                confidence += 8
                reasons.append("✓ Breaking below lower Bollinger Band")
            
            # Volatility expansion
            if atr_percent > 3:
                confidence += 7
                reasons.append(f"✓ Volatility expanding ({atr_percent:.1f}%)")
        
        min_conf_local = 55 if (market_data.get('regime') == 'VOLATILE') else 70
        if confidence >= min_conf_local and direction:
            return {
                'type': 'BREAKOUT_ENHANCED',
                'symbol': symbol,
                'direction': direction,
                'confidence': min(confidence, 95),
                'entry_price': price,
                'stop_loss_percent': stop_loss_pct,
                'take_profit_percent': take_profit_pct,
                'reasons': reasons,
                'strategy': 'BREAKOUT'  # Tag for tracking
            }
        
        # Volatility fallback scoring
        try:
            atr = indicators.get('atr', 0)
            current_price = indicators.get('current_price', price)
            atr_ratio = (atr / current_price) if current_price else 0
            volume = indicators.get('volume_ratio', 1.0)
            rsi = indicators.get('rsi', 50)
            base_conf = 0
            if atr_ratio > 0.008:
                base_conf += min(40, int(atr_ratio * 4000))
            if volume > 1.2:
                base_conf += min(25, int((volume - 1.0) * 25))
            if regime == 'VOLATILE':
                base_conf += 20
            if rsi < 35 or rsi > 65:
                base_conf += 15
            min_conf = 55 if regime == 'VOLATILE' else 70
            if base_conf >= min_conf:
                inferred_dir = 'LONG' if rsi < 50 else 'SHORT'
                return {
                    'type': 'BREAKOUT_VOL_FALLBACK',
                    'symbol': symbol,
                    'direction': inferred_dir,
                    'confidence': min(95, base_conf),
                    'entry_price': price,
                    'stop_loss_percent': stop_loss_pct,
                    'take_profit_percent': take_profit_pct,
                    'reasons': reasons + [f"Vol fallback ATR:{atr_ratio:.2%} Vol:{volume:.1f}x RSI:{rsi:.0f}"]
                }
        except Exception:
            pass
        return None
    
    def _identify_reversal_setup_enhanced(self, indicators: Dict, regime: str, symbol: str, price: float) -> Optional[Dict]:
        """
        ENHANCED: Mean reversion with divergence detection
        - Extreme RSI levels with recovery signs
        - Bollinger Band extremes with mean reversion
        - MACD divergence detection
        - Not fighting strong trends
        """
        confidence = 0
        direction = None
        reasons = []
        stop_loss_pct = 5
        take_profit_pct = 10
        
        rsi = indicators.get('rsi', 50)
        bb_position = indicators.get('bb_position', 50)
        macd_diff = indicators.get('macd_diff', 0)
        ema_9 = indicators.get('ema_9', 0)
        ema_21 = indicators.get('ema_21', 0)
        
        # === BULLISH REVERSAL (Buy the Dip) ===
        if rsi < 35 and bb_position < 25:
            confidence += 35
            direction = 'LONG'
            reasons.append(f"✓ Oversold conditions (RSI: {rsi:.1f}, BB: {bb_position:.0f}%)")
            
            # Extreme oversold bonus
            if rsi < 25:
                confidence += 15
                reasons.append("✓ Extremely oversold - high reversal probability")
            
            # MACD showing early reversal signs
            if macd_diff > -0.05:
                confidence += 20
                reasons.append("✓ MACD divergence - momentum weakening")
            elif macd_diff > 0:
                confidence += 25
                reasons.append("✓ MACD bullish crossover - reversal confirmed")
            
            # Price near lower Bollinger Band
            if bb_position < 15:
                confidence += 15
                reasons.append("✓ Price at extreme lower band - reversion likely")
            
            # Make sure we're not fighting a strong downtrend
            if regime in ['STRONG_TREND_DOWN', 'BREAKOUT_DOWN']:
                confidence -= 25
                reasons.append("⚠ Strong downtrend active - risky reversal")
            elif regime in ['RANGING', 'VOLATILE', 'NEUTRAL']:
                confidence += 10
                reasons.append("✓ No strong trend - good reversal environment")
            
            # EMA support check
            if price < ema_21 * 0.97:
                confidence += 8
                reasons.append("✓ Price well below EMA - rubber band effect")
        
        # === BEARISH REVERSAL (Sell the Rally) ===
        elif rsi > 65 and bb_position > 75:
            confidence += 35
            direction = 'SHORT'
            reasons.append(f"✓ Overbought conditions (RSI: {rsi:.1f}, BB: {bb_position:.0f}%)")
            
            # Extreme overbought bonus
            if rsi > 75:
                confidence += 15
                reasons.append("✓ Extremely overbought - high reversal probability")
            
            # MACD showing early reversal signs
            if macd_diff < 0.05:
                confidence += 20
                reasons.append("✓ MACD divergence - momentum weakening")
            elif macd_diff < 0:
                confidence += 25
                reasons.append("✓ MACD bearish crossover - reversal confirmed")
            
            # Price near upper Bollinger Band
            if bb_position > 85:
                confidence += 15
                reasons.append("✓ Price at extreme upper band - reversion likely")
            
            # Make sure we're not fighting a strong uptrend
            if regime in ['STRONG_TREND_UP', 'BREAKOUT_UP']:
                confidence -= 25
                reasons.append("⚠ Strong uptrend active - risky reversal")
            elif regime in ['RANGING', 'VOLATILE', 'NEUTRAL']:
                confidence += 10
                reasons.append("✓ No strong trend - good reversal environment")
            
            # EMA resistance check
            if price > ema_21 * 1.03:
                confidence += 8
                reasons.append("✓ Price well above EMA - rubber band effect")
        
        min_conf_local = 55 if regime == 'VOLATILE' else 70
        if confidence >= min_conf_local and direction:
            return {
                'type': 'REVERSAL_ENHANCED',
                'symbol': symbol,
                'direction': direction,
                'confidence': min(confidence, 92),
                'entry_price': price,
                'stop_loss_percent': stop_loss_pct,
                'take_profit_percent': take_profit_pct,
                'reasons': reasons
            }
        
        # Volatility fallback scoring
        try:
            atr = indicators.get('atr', 0)
            current_price = indicators.get('current_price', price)
            atr_ratio = (atr / current_price) if current_price else 0
            volume = indicators.get('volume_ratio', 1.0)
            base_conf = 0
            if atr_ratio > 0.008:
                base_conf += min(40, int(atr_ratio * 4000))
            if volume > 1.2:
                base_conf += min(25, int((volume - 1.0) * 25))
            if regime == 'VOLATILE':
                base_conf += 20
            if rsi < 35 or rsi > 65:
                base_conf += 15
            min_conf = 55 if regime == 'VOLATILE' else 70
            if base_conf >= min_conf:
                inferred_dir = 'LONG' if rsi < 50 else 'SHORT'
                return {
                    'type': 'REVERSAL_VOL_FALLBACK',
                    'symbol': symbol,
                    'direction': inferred_dir,
                    'confidence': min(92, base_conf),
                    'entry_price': price,
                    'stop_loss_percent': stop_loss_pct,
                    'take_profit_percent': take_profit_pct,
                    'reasons': reasons + [f"Vol fallback ATR:{atr_ratio:.2%} Vol:{volume:.1f}x RSI:{rsi:.0f}"]
                }
        except Exception:
            pass
        return None
    
    def _identify_momentum_setup_enhanced(self, indicators: Dict, regime: str, symbol: str, price: float, market_data: Dict) -> Optional[Dict]:
        """
        ENHANCED: Momentum trading with trend alignment
        - Strong price momentum (>5% moves)
        - Aligned with trend direction
        - Volume confirmation
        - RSI not at extremes
        """
        confidence = 0
        direction = None
        reasons = []
        stop_loss_pct = 4
        take_profit_pct = 16
        
        price_change_4h = indicators.get('price_change_4h', 0)
        price_change_24h = market_data.get('price_change_24h', 0)
        rsi = indicators.get('rsi', 50)
        volume_ratio = indicators.get('volume_ratio', 1)
        macd_diff = indicators.get('macd_diff', 0)
        
        # === BULLISH MOMENTUM ===
        if price_change_4h > 3 and price_change_24h > 5:
            confidence += 30
            direction = 'LONG'
            reasons.append(f"✓ Strong upward momentum ({price_change_24h:.1f}% / 24h)")
            
            # Extreme momentum bonus
            if price_change_24h > 10:
                confidence += 20
                reasons.append("✓ Exceptional momentum - continuation likely")
            elif price_change_24h > 7:
                confidence += 10
                reasons.append("✓ Very strong momentum")
            
            # RSI sustainability check
            if 55 < rsi < 75:
                confidence += 20
                reasons.append(f"✓ RSI sustainable momentum zone ({rsi:.1f})")
            elif rsi >= 75:
                confidence -= 15
                reasons.append(f"⚠ RSI too high - momentum may exhaust ({rsi:.1f})")
            
            # Volume confirmation crucial for momentum
            if volume_ratio > 2.0:
                confidence += 20
                reasons.append(f"✓ Massive volume surge ({volume_ratio:.2f}x)")
            elif volume_ratio > 1.5:
                confidence += 12
                reasons.append(f"✓ Strong volume ({volume_ratio:.2f}x)")
            else:
                confidence -= 10
                reasons.append("⚠ Weak volume - momentum questionable")
            
            # MACD trend alignment
            if macd_diff > 0.1:
                confidence += 12
                reasons.append("✓ MACD strongly bullish - aligned")
            
            # Regime alignment
            if regime in ['STRONG_TREND_UP', 'BREAKOUT_UP', 'MOMENTUM']:
                confidence += 15
                reasons.append("✓ Regime aligned with momentum")
            else:
                confidence -= 8
                reasons.append("⚠ Regime not aligned")
        
        # === BEARISH MOMENTUM ===
        elif price_change_4h < -3 and price_change_24h < -5:
            confidence += 30
            direction = 'SHORT'
            reasons.append(f"✓ Strong downward momentum ({price_change_24h:.1f}% / 24h)")
            
            # Extreme momentum bonus
            if price_change_24h < -10:
                confidence += 20
                reasons.append("✓ Exceptional bearish momentum")
            elif price_change_24h < -7:
                confidence += 10
                reasons.append("✓ Very strong bearish momentum")
            
            # RSI sustainability check
            if 25 < rsi < 45:
                confidence += 20
                reasons.append(f"✓ RSI sustainable bearish zone ({rsi:.1f})")
            elif rsi <= 25:
                confidence -= 15
                reasons.append(f"⚠ RSI too low - momentum may reverse ({rsi:.1f})")
            
            # Volume confirmation
            if volume_ratio > 2.0:
                confidence += 20
                reasons.append(f"✓ Massive volume surge ({volume_ratio:.2f}x)")
            elif volume_ratio > 1.5:
                confidence += 12
                reasons.append(f"✓ Strong volume ({volume_ratio:.2f}x)")
            else:
                confidence -= 10
                reasons.append("⚠ Weak volume - momentum questionable")
            
            # MACD trend alignment
            if macd_diff < -0.1:
                confidence += 12
                reasons.append("✓ MACD strongly bearish - aligned")
            
            # Regime alignment
            if regime in ['STRONG_TREND_DOWN', 'BREAKOUT_DOWN', 'MOMENTUM']:
                confidence += 15
                reasons.append("✓ Regime aligned with momentum")
            else:
                confidence -= 8
                reasons.append("⚠ Regime not aligned")
        
        min_conf_local = 55 if (market_data.get('regime') == 'VOLATILE') else 70
        if confidence >= min_conf_local and direction:
            return {
                'type': 'MOMENTUM_ENHANCED',
                'symbol': symbol,
                'direction': direction,
                'confidence': min(confidence, 95),
                'entry_price': price,
                'stop_loss_percent': stop_loss_pct,
                'take_profit_percent': take_profit_pct,
                'reasons': reasons
            }
        
        # Volatility fallback scoring
        try:
            atr = indicators.get('atr', 0)
            current_price = indicators.get('current_price', price)
            atr_ratio = (atr / current_price) if current_price else 0
            volume = indicators.get('volume_ratio', 1.0)
            rsi = indicators.get('rsi', 50)
            base_conf = 0
            if atr_ratio > 0.008:
                base_conf += min(40, int(atr_ratio * 4000))
            if volume > 1.2:
                base_conf += min(25, int((volume - 1.0) * 25))
            if market_data.get('regime') == 'VOLATILE':
                base_conf += 20
            if rsi < 35 or rsi > 65:
                base_conf += 15
            min_conf = 55 if market_data.get('regime') == 'VOLATILE' else 70
            if base_conf >= min_conf:
                inferred_dir = 'LONG' if rsi < 50 else 'SHORT'
                return {
                    'type': 'MOMENTUM_VOL_FALLBACK',
                    'symbol': symbol,
                    'direction': inferred_dir,
                    'confidence': min(95, base_conf),
                    'entry_price': price,
                    'stop_loss_percent': stop_loss_pct,
                    'take_profit_percent': take_profit_pct,
                    'reasons': reasons + [f"Vol fallback ATR:{atr_ratio:.2%} Vol:{volume:.1f}x RSI:{rsi:.0f}"]
                }
        except Exception:
            pass
        return None
    
    def _identify_volatility_breakout(self, indicators: Dict, regime: str, symbol: str, price: float, market_data: Dict) -> Optional[Dict]:
        """
        BALANCED: Volatility trading with quality filters
        - Core volatility scoring (ATR-based)
        - Regime boost for VOLATILE markets
        - Quality filters (RSI extremes, volume, trend alignment)
        """
        # Extract indicators
        atr = indicators.get('atr', 0)
        atr_ratio = atr / price if price else 0
        volume = indicators.get('volume_ratio', 1.0)
        rsi = indicators.get('rsi', 50)
        ema_21 = indicators.get('ema_21', price)
        stop_loss_pct = 4
        take_profit_pct = 14
        
        confidence = 0
        reasons = []
        
        # Core volatility (0-50 points)
        if atr_ratio > 0.004:  # >0.4% ATR
            atr_score = min(50, int(atr_ratio * 10000))
            confidence += atr_score
            reasons.append(f"✓ Volatility high (ATR {atr_ratio:.2%}) -> +{atr_score}")
        
        # Regime boost (0-20 points)
        if regime == 'VOLATILE':
            confidence += 20
            reasons.append("✓ VOLATILE regime -> +20")
        
        # Quality filters (0-30 points total)
        # RSI extremes = mean reversion opportunity
        if rsi < 35:
            confidence += 15
            reasons.append(f"✓ Oversold RSI ({rsi:.1f}) -> +15")
        elif rsi > 65:
            confidence += 15
            reasons.append(f"✓ Overbought RSI ({rsi:.1f}) -> +15")
        
        # Volume confirmation
        if volume > 1.3:
            confidence += 10
            reasons.append(f"✓ Volume confirmation ({volume:.2f}x) -> +10")
        
        # Trend alignment
        if (price < ema_21 and rsi < 45) or (price > ema_21 and rsi > 55):
            confidence += 5
            reasons.append("✓ Trend alignment -> +5")
        
        # Performance-based boost: if this strategy is performing well, boost confidence
        strategy_boost = self.perf_tracker.get_strategy_boost('VOLATILITY_BREAKOUT')
        if strategy_boost > 0:
            confidence += strategy_boost
            reasons.append(f"✓ Strategy performing well -> +{strategy_boost}")
        
        # Lower threshold for VOLATILE to capture BTC
        min_conf = 65 if regime == 'VOLATILE' else 75
        
        if confidence >= min_conf:
            direction = 'LONG' if rsi < 50 else 'SHORT'
            return {
                'type': 'VOLATILITY_BREAKOUT',
                'symbol': symbol,
                'direction': direction,
                'confidence': min(95, confidence),
                'entry_price': price,
                'stop_loss_percent': stop_loss_pct,
                'take_profit_percent': take_profit_pct,
                'reasons': reasons,
                'strategy': 'VOLATILITY_BREAKOUT'  # Tag for tracking
            }
        
        return None
    
    def _identify_ema_crossover(self, indicators: Dict, regime: str, symbol: str, price: float) -> Optional[Dict]:
        """
        NEW SETUP: EMA crossover with confirmation
        - EMA 9 crossing EMA 21
        - Price confirmation
        - MACD alignment
        """
        confidence = 0
        direction = None
        reasons = []
        stop_loss_pct = 3.5
        take_profit_pct = 12
        
        ema_9 = indicators.get('ema_9', 0)
        ema_21 = indicators.get('ema_21', 0)
        ema_50 = indicators.get('ema_50', 0)
        macd_diff = indicators.get('macd_diff', 0)
        rsi = indicators.get('rsi', 50)
        volume_ratio = indicators.get('volume_ratio', 1)
        
        # Calculate proximity to crossover
        ema_diff_pct = ((ema_9 - ema_21) / ema_21) * 100
        
        # Bullish crossover (9 crossing above 21)
        if 0 < ema_diff_pct < 0.5 and price > ema_9:
            confidence += 35
            direction = 'LONG'
            reasons.append("✓ Bullish EMA crossover in progress (9 > 21)")
            
            if macd_diff > 0:
                confidence += 20
                reasons.append("✓ MACD confirms bullish momentum")
            
            if ema_21 > ema_50:
                confidence += 15
                reasons.append("✓ Longer-term trend also bullish")
            
            if 50 < rsi < 65:
                confidence += 12
                reasons.append(f"✓ RSI in optimal range ({rsi:.1f})")
            
            if volume_ratio > 1.2:
                confidence += 10
                reasons.append("✓ Volume supporting move")
            
            if regime in ['STRONG_TREND_UP', 'NEUTRAL']:
                confidence += 8
                reasons.append("✓ Favorable market regime")
        
        # Bearish crossover (9 crossing below 21)
        elif -0.5 < ema_diff_pct < 0 and price < ema_9:
            confidence += 35
            direction = 'SHORT'
            reasons.append("✓ Bearish EMA crossover in progress (9 < 21)")
            
            if macd_diff < 0:
                confidence += 20
                reasons.append("✓ MACD confirms bearish momentum")
            
            if ema_21 < ema_50:
                confidence += 15
                reasons.append("✓ Longer-term trend also bearish")
            
            if 35 < rsi < 50:
                confidence += 12
                reasons.append(f"✓ RSI in optimal range ({rsi:.1f})")
            
            if volume_ratio > 1.2:
                confidence += 10
                reasons.append("✓ Volume supporting move")
            
            if regime in ['STRONG_TREND_DOWN', 'NEUTRAL']:
                confidence += 8
                reasons.append("✓ Favorable market regime")
        
        min_conf_local = 55 if regime == 'VOLATILE' else 70
        if confidence >= min_conf_local and direction:
            return {
                'type': 'EMA_CROSSOVER',
                'symbol': symbol,
                'direction': direction,
                'confidence': min(confidence, 92),
                'entry_price': price,
                'stop_loss_percent': stop_loss_pct,
                'take_profit_percent': take_profit_pct,
                'reasons': reasons
            }
        
        # Volatility fallback scoring
        try:
            atr = indicators.get('atr', 0)
            current_price = indicators.get('current_price', price)
            atr_ratio = (atr / current_price) if current_price else 0
            volume = indicators.get('volume_ratio', 1.0)
            rsi = indicators.get('rsi', 50)
            base_conf = 0
            if atr_ratio > 0.008:
                base_conf += min(40, int(atr_ratio * 4000))
            if volume > 1.2:
                base_conf += min(25, int((volume - 1.0) * 25))
            if regime == 'VOLATILE':
                base_conf += 20
            if rsi < 35 or rsi > 65:
                base_conf += 15
            min_conf = 55 if regime == 'VOLATILE' else 70
            if base_conf >= min_conf:
                inferred_dir = 'LONG' if rsi < 50 else 'SHORT'
                return {
                    'type': 'EMA_CROSSOVER_VOL_FALLBACK',
                    'symbol': symbol,
                    'direction': inferred_dir,
                    'confidence': min(92, base_conf),
                    'entry_price': price,
                    'stop_loss_percent': stop_loss_pct,
                    'take_profit_percent': take_profit_pct,
                    'reasons': reasons + [f"Vol fallback ATR:{atr_ratio:.2%} Vol:{volume:.1f}x RSI:{rsi:.0f}"]
                }
        except Exception:
            pass
        return None
    
    def should_exit_position(self, position: Dict, market_data: Dict, indicators: Dict) -> tuple[bool, str, int]:
        """
        ENHANCED EXIT LOGIC: Determine if position should be closed
        Returns: (should_exit, reason, confidence)
        """
        symbol = position.get('symbol')
        side = position.get('side')  # 'LONG' or 'SHORT'
        entry_price = position.get('entry_price', 0)
        current_price = market_data.get('price', 0)
        pnl_percent = position.get('pnl_percent', 0)
        
        rsi = indicators.get('rsi', 50)
        macd_diff = indicators.get('macd_diff', 0)
        regime = market_data.get('regime', 'UNKNOWN')
        bb_position = indicators.get('bb_position', 50)
        volume_ratio = indicators.get('volume_ratio', 1)
        
        reasons = []
        exit_confidence = 0
        
        # === PROFIT PROTECTION ===
        if pnl_percent > 10:
            # Take partial profits on large gains
            if side == 'LONG' and (rsi > 75 or bb_position > 90):
                exit_confidence += 40
                reasons.append(f"✓ Large profit ({pnl_percent:+.1f}%) + overbought - secure gains")
            elif side == 'SHORT' and (rsi < 25 or bb_position < 10):
                exit_confidence += 40
                reasons.append(f"✓ Large profit ({pnl_percent:+.1f}%) + oversold - secure gains")
        
        # === TREND REVERSAL DETECTION ===
        if side == 'LONG':
            # Exit long positions if bearish signals emerge
            if macd_diff < -0.05 and rsi < 45:
                exit_confidence += 35
                reasons.append("⚠ Bearish MACD crossover + weak RSI - trend reversing")
            
            if regime in ['STRONG_TREND_DOWN', 'BREAKOUT_DOWN']:
                exit_confidence += 30
                reasons.append("⚠ Market regime turned bearish")
            
            if bb_position < 20 and volume_ratio > 1.3:
                exit_confidence += 25
                reasons.append("⚠ Breaking lower BB with volume - exit long")
        
        elif side == 'SHORT':
            # Exit short positions if bullish signals emerge
            if macd_diff > 0.05 and rsi > 55:
                exit_confidence += 35
                reasons.append("⚠ Bullish MACD crossover + strong RSI - trend reversing")
            
            if regime in ['STRONG_TREND_UP', 'BREAKOUT_UP']:
                exit_confidence += 30
                reasons.append("⚠ Market regime turned bullish")
            
            if bb_position > 80 and volume_ratio > 1.3:
                exit_confidence += 25
                reasons.append("⚠ Breaking upper BB with volume - exit short")
        
        # === MOMENTUM EXHAUSTION ===
        if side == 'LONG' and rsi > 78:
            exit_confidence += 25
            reasons.append(f"⚠ Extreme overbought RSI ({rsi:.1f}) - momentum exhaustion")
        elif side == 'SHORT' and rsi < 22:
            exit_confidence += 25
            reasons.append(f"⚠ Extreme oversold RSI ({rsi:.1f}) - momentum exhaustion")
        
        # === STOP LOSS TIGHTENING ===
        if pnl_percent < -3:
            exit_confidence += 20
            reasons.append(f"⚠ Loss exceeding -3% ({pnl_percent:.1f}%) - cut losses")
        
        # Decide to exit
        should_exit = exit_confidence >= 75
        reason_str = " | ".join(reasons) if reasons else "No exit signals"
        
        return should_exit, reason_str, exit_confidence
    
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
        
        # Sort by confidence
        setups_sorted = sorted(setups, key=lambda x: x['confidence'], reverse=True)
        best_setup = setups_sorted[0] if setups_sorted else None
        
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
- MACD: {'Bullish' if indicators.get('macd_diff', 0) > 0 else 'Bearish'} (diff: {indicators.get('macd_diff', 0):.4f})
- EMA9: ${indicators.get('ema_9', 0):.2f} | EMA21: ${indicators.get('ema_21', 0):.2f} | EMA50: ${indicators.get('ema_50', 0):.2f}
- Bollinger Position: {indicators.get('bb_position', 50):.0f}% (0=bottom, 100=top)
- Volume Ratio: {indicators.get('volume_ratio', 1):.2f}x average
- ATR: {indicators.get('atr_percent', 0):.2f}% (volatility)
- Recent High: ${indicators.get('recent_high', 0):,.2f} | Low: ${indicators.get('recent_low', 0):,.2f}

ENHANCED TRADE ANALYSIS:
"""
        
        if best_setup:
            context += f"""
🎯 PRIMARY SETUP: {best_setup['type']}
   Direction: {best_setup['direction']}
   Confidence: {best_setup['confidence']:.0f}%
   Entry: ${best_setup['entry_price']:,.2f}
   Stop Loss: {best_setup.get('stop_loss_percent', 4):.1f}%
   Take Profit: {best_setup.get('take_profit_percent', 12):.1f}%
   
   Signal Reasons:
"""
            for reason in best_setup['reasons']:
                context += f"   {reason}\n"
            
            # Show additional setups if available
            if len(setups_sorted) > 1:
                context += f"\n📋 ALTERNATIVE SETUPS ({len(setups_sorted)-1} found):\n"
                for i, setup in enumerate(setups_sorted[1:3], 1):  # Show top 2 alternatives
                    context += f"   {i}. {setup['type']}: {setup['direction']} ({setup['confidence']:.0f}%)\n"
        else:
            context += "❌ No high-confidence setups identified (all below 70% threshold)\n"
        
        context += f"""
PORTFOLIO STATUS:
- Total Value: ${portfolio_value:,.2f}
- Available Balance: ${available_balance:,.2f}
- Current Drawdown: {drawdown:.1f}%
- Open Positions: {position_count}/3
"""
        
        if existing_position:
            # Check if position should be exited
            should_exit, exit_reason, exit_conf = self.should_exit_position(
                existing_position, market_data, indicators
            )
            
            context += f"""
📊 EXISTING POSITION IN {symbol}:
   Side: {existing_position.get('side')}
   Entry: ${existing_position.get('entry_price', 0):,.2f}
   Current PnL: {existing_position.get('pnl_percent', 0):+.2f}%
   Leverage: {existing_position.get('leverage')}x
   
   Exit Analysis: {'🔴 SUGGEST CLOSE' if should_exit else '🟢 HOLD'}
   Exit Confidence: {exit_conf}%
   Reason: {exit_reason}
"""
        
        context += f"""
COMPETITION STATUS:
- Days Remaining: {14 - day_number}
- Phase: {'🔴 FINAL PUSH' if day_number > 11 else '🟡 MID-GAME' if day_number > 7 else '🟢 EARLY PHASE'}
- Strategy: {'Maximum aggression needed' if day_number > 11 else 'Balanced risk/reward' if day_number > 7 else 'Building steady foundation'}

DECISION REQUIRED:
Analyze all signals and provide trading decision in strict JSON format.
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