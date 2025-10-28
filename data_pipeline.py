"""
Data Pipeline Module
Handles real-time data fetching, technical indicator calculation, and market data processing
"""
import time
from typing import Dict, List, Optional
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from binance.client import Client
from binance.exceptions import BinanceAPIException
import ta
from config import (
    BINANCE_API_KEY, BINANCE_API_SECRET, TIMEFRAMES,
    KLINE_LIMIT, MAX_API_RETRIES, RETRY_BACKOFF_MULTIPLIER
)


class DataPipeline:
    """Fetches and processes market data for trading decisions"""
    
    def __init__(self):
        self.client = Client(
            api_key=BINANCE_API_KEY,
            api_secret=BINANCE_API_SECRET,
            testnet=True
        )
        self.cache = {}  # Cache for rate limiting
        self.last_fetch = {}
    
    def fetch_realtime_data(self, symbol: str) -> Dict:
        """
        Fetch real-time market data for a symbol
        Returns comprehensive market data including price, indicators, and regime
        """
        try:
            # Get current price
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price'])
            
            # Get 24h stats
            stats_24h = self.client.futures_ticker(symbol=symbol)
            
            # Fetch OHLCV data for multiple timeframes
            timeframe_data = {}
            for timeframe in TIMEFRAMES:
                df = self._fetch_klines(symbol, timeframe)
                if df is not None and not df.empty:
                    timeframe_data[timeframe] = df
            
            # Use primary timeframe (1h) for main analysis
            primary_df = timeframe_data.get('1h')
            
            if primary_df is None or primary_df.empty:
                return {'symbol': symbol, 'price': current_price, 'error': 'No data available'}
            
            # Calculate technical indicators
            indicators = self.calculate_technical_indicators(primary_df)
            
            # Get market regime
            regime = self.get_market_regime(primary_df, indicators)
            
            # Get funding rate
            funding_rate = self.get_funding_rate(symbol)
            
            # Compile all data
            market_data = {
                'symbol': symbol,
                'price': current_price,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'volume_24h': float(stats_24h['volume']),
                'price_change_24h': float(stats_24h['priceChangePercent']),
                'high_24h': float(stats_24h['highPrice']),
                'low_24h': float(stats_24h['lowPrice']),
                'funding_rate': funding_rate,
                'regime': regime,
                'indicators': indicators,
                'timeframe_data': {tf: self._extract_recent_data(df) for tf, df in timeframe_data.items()}
            }
            
            return market_data
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    def _fetch_klines(self, symbol: str, timeframe: str, limit: int = KLINE_LIMIT) -> Optional[pd.DataFrame]:
        """Fetch OHLCV candle data"""
        try:
            # Check cache (5 minute cache)
            cache_key = f"{symbol}_{timeframe}"
            if cache_key in self.cache:
                cache_time, cached_df = self.cache[cache_key]
                if time.time() - cache_time < 300:  # 5 minutes
                    return cached_df
            
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=timeframe,
                limit=limit
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # Cache result
            self.cache[cache_key] = (time.time(), df)
            
            return df
            
        except Exception as e:
            print(f"Error fetching klines for {symbol} {timeframe}: {e}")
            return None
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate technical indicators from OHLCV data"""
        if df is None or len(df) < 50:
            return {}
        
        try:
            # Make a copy to avoid modifying original
            df = df.copy()
            
            # Moving Averages
            ema_9 = ta.trend.EMAIndicator(df['close'], window=9).ema_indicator().iloc[-1]
            ema_21 = ta.trend.EMAIndicator(df['close'], window=21).ema_indicator().iloc[-1]
            ema_50 = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator().iloc[-1]
            ema_200 = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator().iloc[-1] if len(df) >= 200 else None
            
            # RSI
            rsi = ta.momentum.RSIIndicator(df['close'], window=14).rsi().iloc[-1]
            
            # MACD
            macd = ta.trend.MACD(df['close'])
            macd_line = macd.macd().iloc[-1]
            macd_signal = macd.macd_signal().iloc[-1]
            macd_diff = macd.macd_diff().iloc[-1]
            
            # Bollinger Bands
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
            bb_high = bb.bollinger_hband().iloc[-1]
            bb_mid = bb.bollinger_mavg().iloc[-1]
            bb_low = bb.bollinger_lband().iloc[-1]
            bb_width = ((bb_high - bb_low) / bb_mid) * 100
            
            current_price = df['close'].iloc[-1]
            bb_position = ((current_price - bb_low) / (bb_high - bb_low)) * 100 if bb_high != bb_low else 50
            
            # ATR (Average True Range) - for volatility
            atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range().iloc[-1]
            atr_percent = (atr / current_price) * 100
            
            # Volume analysis
            volume_sma_20 = df['volume'].rolling(20).mean().iloc[-1]
            current_volume = df['volume'].iloc[-1]
            volume_ratio = current_volume / volume_sma_20 if volume_sma_20 > 0 else 1
            
            # Price momentum
            price_change_1h = ((df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]) * 100 if len(df) >= 2 else 0
            price_change_4h = ((df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]) * 100 if len(df) >= 5 else 0
            price_change_24h = ((df['close'].iloc[-1] - df['close'].iloc[-25]) / df['close'].iloc[-25]) * 100 if len(df) >= 25 else 0
            
            # Support and Resistance (simple version using recent highs/lows)
            recent_high = df['high'].tail(20).max()
            recent_low = df['low'].tail(20).min()
            
            indicators = {
                'ema_9': float(ema_9),
                'ema_21': float(ema_21),
                'ema_50': float(ema_50),
                'ema_200': float(ema_200) if ema_200 else None,
                'rsi': float(rsi),
                'macd': float(macd_line),
                'macd_signal': float(macd_signal),
                'macd_diff': float(macd_diff),
                'bb_high': float(bb_high),
                'bb_mid': float(bb_mid),
                'bb_low': float(bb_low),
                'bb_width': float(bb_width),
                'bb_position': float(bb_position),
                'atr': float(atr),
                'atr_percent': float(atr_percent),
                'volume_ratio': float(volume_ratio),
                'price_change_1h': float(price_change_1h),
                'price_change_4h': float(price_change_4h),
                'price_change_24h': float(price_change_24h),
                'recent_high': float(recent_high),
                'recent_low': float(recent_low),
                'current_price': float(current_price)
            }
            
            return indicators
            
        except Exception as e:
            print(f"Error calculating indicators: {e}")
            return {}
    
    def get_market_regime(self, df: pd.DataFrame, indicators: Dict) -> str:
        """
        Classify market regime based on technical analysis
        Returns: STRONG_TREND_UP, STRONG_TREND_DOWN, BREAKOUT, RANGING, VOLATILE
        """
        if not indicators:
            return "UNKNOWN"
        
        try:
            current_price = indicators['current_price']
            ema_9 = indicators['ema_9']
            ema_21 = indicators['ema_21']
            ema_50 = indicators['ema_50']
            rsi = indicators['rsi']
            bb_position = indicators['bb_position']
            atr_percent = indicators['atr_percent']
            macd_diff = indicators['macd_diff']
            volume_ratio = indicators['volume_ratio']
            
            # Check for strong trend
            ema_aligned_up = ema_9 > ema_21 > ema_50
            ema_aligned_down = ema_9 < ema_21 < ema_50
            price_above_ema = current_price > ema_21
            price_below_ema = current_price < ema_21
            
            # Strong uptrend conditions
            if (ema_aligned_up and price_above_ema and 
                rsi > 50 and macd_diff > 0 and volume_ratio > 1.2):
                return "STRONG_TREND_UP"
            
            # Strong downtrend conditions
            if (ema_aligned_down and price_below_ema and 
                rsi < 50 and macd_diff < 0 and volume_ratio > 1.2):
                return "STRONG_TREND_DOWN"
            
            # Breakout conditions (high volatility + strong move)
            if atr_percent > 3.0 and volume_ratio > 1.5:
                if bb_position > 80:
                    return "BREAKOUT_UP"
                elif bb_position < 20:
                    return "BREAKOUT_DOWN"
            
            # Volatile/choppy market
            if atr_percent > 4.0:
                return "VOLATILE"
            
            # Ranging market (price bouncing between levels)
            if 40 < rsi < 60 and 30 < bb_position < 70 and atr_percent < 2.5:
                return "RANGING"
            
            # Default to neutral
            return "NEUTRAL"
            
        except Exception as e:
            print(f"Error determining market regime: {e}")
            return "UNKNOWN"
    
    def get_funding_rate(self, symbol: str) -> float:
        """Get current funding rate for perpetual futures"""
        try:
            funding = self.client.futures_funding_rate(symbol=symbol, limit=1)
            if funding:
                return float(funding[0]['fundingRate'])
        except Exception as e:
            print(f"Error fetching funding rate for {symbol}: {e}")
        return 0.0
    
    def _extract_recent_data(self, df: pd.DataFrame, periods: int = 5) -> List[Dict]:
        """Extract recent candle data for context"""
        if df is None or df.empty:
            return []
        
        recent = df.tail(periods)
        return recent[['timestamp', 'open', 'high', 'low', 'close', 'volume']].to_dict('records')
    
    def handle_data_gaps(self, symbol: str) -> bool:
        """Check and handle data gaps or missing data"""
        try:
            # Verify we can fetch recent data
            df = self._fetch_klines(symbol, '1h', limit=50)
            if df is None or len(df) < 30:
                print(f"⚠️ Data gap detected for {symbol}, attempting recovery...")
                # Clear cache and retry
                cache_key = f"{symbol}_1h"
                if cache_key in self.cache:
                    del self.cache[cache_key]
                return False
            return True
        except Exception as e:
            print(f"Error checking data gaps for {symbol}: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test connection to Binance Futures"""
        try:
            self.client.futures_ping()
            print("✅ Connected to Binance Futures Testnet")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Binance: {e}")
            return False


def retry_on_failure(func, max_retries=MAX_API_RETRIES):
    """Retry wrapper for API calls"""
    for attempt in range(max_retries):
        try:
            return func()
        except BinanceAPIException as e:
            if attempt < max_retries - 1:
                wait_time = RETRY_BACKOFF_MULTIPLIER ** attempt
                print(f"API error, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = RETRY_BACKOFF_MULTIPLIER ** attempt
                print(f"Error: {e}, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise

