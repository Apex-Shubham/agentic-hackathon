"""
Unit tests for Data Pipeline
Tests data fetching and technical indicator calculations
"""
import pytest
import pandas as pd
import numpy as np
from data_pipeline import DataPipeline


class TestDataPipeline:
    """Test suite for DataPipeline class"""
    
    def create_sample_dataframe(self, periods=100):
        """Create sample OHLCV data for testing"""
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='1H')
        
        # Generate realistic price data
        base_price = 50000
        price_changes = np.random.randn(periods) * 100
        close_prices = base_price + np.cumsum(price_changes)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices + np.random.randn(periods) * 50,
            'high': close_prices + np.abs(np.random.randn(periods)) * 100,
            'low': close_prices - np.abs(np.random.randn(periods)) * 100,
            'close': close_prices,
            'volume': np.random.uniform(1000, 10000, periods)
        })
        
        return df
    
    def test_calculate_technical_indicators(self):
        """Test that all technical indicators are calculated"""
        pipeline = DataPipeline()
        df = self.create_sample_dataframe()
        
        indicators = pipeline.calculate_technical_indicators(df)
        
        # Check all expected indicators are present
        expected_indicators = [
            'ema_9', 'ema_21', 'ema_50', 'rsi', 'macd', 'macd_signal',
            'macd_diff', 'bb_high', 'bb_mid', 'bb_low', 'bb_width',
            'bb_position', 'atr', 'atr_percent', 'volume_ratio',
            'price_change_1h', 'recent_high', 'recent_low', 'current_price'
        ]
        
        for indicator in expected_indicators:
            assert indicator in indicators, f"Missing indicator: {indicator}"
    
    def test_indicators_valid_ranges(self):
        """Test that indicators are in valid ranges"""
        pipeline = DataPipeline()
        df = self.create_sample_dataframe()
        
        indicators = pipeline.calculate_technical_indicators(df)
        
        # RSI should be 0-100
        assert 0 <= indicators['rsi'] <= 100, f"RSI out of range: {indicators['rsi']}"
        
        # BB position should be 0-100 (percentage)
        assert 0 <= indicators['bb_position'] <= 100, f"BB position out of range: {indicators['bb_position']}"
        
        # ATR percent should be positive
        assert indicators['atr_percent'] > 0, "ATR percent should be positive"
        
        # Volume ratio should be positive
        assert indicators['volume_ratio'] > 0, "Volume ratio should be positive"
    
    def test_get_market_regime_trending_up(self):
        """Test market regime classification for uptrend"""
        pipeline = DataPipeline()
        df = self.create_sample_dataframe()
        
        # Create indicators for strong uptrend
        indicators = {
            'current_price': 51000,
            'ema_9': 50800,
            'ema_21': 50500,
            'ema_50': 50000,
            'rsi': 65,
            'bb_position': 70,
            'atr_percent': 2.0,
            'macd_diff': 50,
            'volume_ratio': 1.5
        }
        
        regime = pipeline.get_market_regime(df, indicators)
        
        # Should identify as uptrend
        assert 'TREND' in regime or 'UP' in regime, f"Should identify uptrend, got: {regime}"
    
    def test_get_market_regime_ranging(self):
        """Test market regime classification for ranging market"""
        pipeline = DataPipeline()
        df = self.create_sample_dataframe()
        
        # Create indicators for ranging market
        indicators = {
            'current_price': 50000,
            'ema_9': 50050,
            'ema_21': 50000,
            'ema_50': 49950,
            'rsi': 50,
            'bb_position': 50,
            'atr_percent': 1.5,
            'macd_diff': 0,
            'volume_ratio': 0.9
        }
        
        regime = pipeline.get_market_regime(df, indicators)
        
        # Should identify as ranging or neutral
        assert regime in ['RANGING', 'NEUTRAL'], f"Should identify ranging market, got: {regime}"
    
    def test_get_market_regime_volatile(self):
        """Test market regime classification for volatile market"""
        pipeline = DataPipeline()
        df = self.create_sample_dataframe()
        
        # Create indicators for volatile market
        indicators = {
            'current_price': 50000,
            'ema_9': 50000,
            'ema_21': 50000,
            'ema_50': 50000,
            'rsi': 60,
            'bb_position': 50,
            'atr_percent': 5.0,  # High volatility
            'macd_diff': 10,
            'volume_ratio': 1.2
        }
        
        regime = pipeline.get_market_regime(df, indicators)
        
        assert regime == 'VOLATILE', f"Should identify volatile market, got: {regime}"
    
    def test_indicators_with_insufficient_data(self):
        """Test indicator calculation with insufficient data"""
        pipeline = DataPipeline()
        df = self.create_sample_dataframe(periods=10)  # Too few periods
        
        indicators = pipeline.calculate_technical_indicators(df)
        
        # Should return empty dict or handle gracefully
        assert isinstance(indicators, dict), "Should return dictionary"
    
    def test_ema_calculation_order(self):
        """Test that EMAs are in correct order for trends"""
        pipeline = DataPipeline()
        
        # Create uptrending data
        periods = 250
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='1H')
        close_prices = np.linspace(40000, 50000, periods)  # Linear uptrend
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices,
            'high': close_prices + 100,
            'low': close_prices - 100,
            'close': close_prices,
            'volume': np.ones(periods) * 5000
        })
        
        indicators = pipeline.calculate_technical_indicators(df)
        
        # In strong uptrend: EMA9 > EMA21 > EMA50
        if indicators.get('ema_200'):
            assert indicators['ema_9'] > indicators['ema_21'] > indicators['ema_50'], \
                "EMAs should be ordered for uptrend"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

