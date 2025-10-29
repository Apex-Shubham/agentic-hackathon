"""
Performance Tracker Module
Analyzes past trades to learn and improve strategy performance over time
"""
import json
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Dict, List


class PerformanceTracker:
    """Tracks trade performance and learns from past results"""
    
    def __init__(self):
        self.trades_file = 'logs/trades.jsonl'
        self.decisions_file = 'logs/decisions.jsonl'
    
    def get_recent_performance(self, days: int = 7) -> Dict:
        """Analyze last N days of trades"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        stats = {
            'by_strategy': defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0}),
            'by_regime': defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0}),
            'by_confidence': defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0}),
            'overall': {'win_rate': 0, 'avg_pnl': 0, 'total_trades': 0}
        }
        
        if not os.path.exists(self.trades_file):
            return stats
        
        try:
            with open(self.trades_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        trade = json.loads(line)
                        trade_time = datetime.fromisoformat(trade['timestamp'].replace('Z', '+00:00'))
                        if trade_time < cutoff:
                            continue
                        
                        # Get strategy from decision log if available
                        strategy = trade.get('strategy', 'unknown')
                        # Try to get regime from decision log
                        regime = trade.get('regime', 'UNKNOWN')
                        confidence = trade.get('confidence', 50)
                        confidence_bucket = int(confidence / 10) * 10  # Bucket by 10s (50, 60, 70, etc.)
                        pnl = trade.get('pnl_percent', 0)
                        
                        if pnl is None:
                            continue  # Skip trades without PnL yet
                            
                        is_win = pnl > 0
                        
                        # Track by strategy
                        stats['by_strategy'][strategy]['wins' if is_win else 'losses'] += 1
                        stats['by_strategy'][strategy]['pnl'] += pnl
                        
                        # Track by regime
                        stats['by_regime'][regime]['wins' if is_win else 'losses'] += 1
                        stats['by_regime'][regime]['pnl'] += pnl
                        
                        # Track by confidence
                        stats['by_confidence'][confidence_bucket]['wins' if is_win else 'losses'] += 1
                        stats['by_confidence'][confidence_bucket]['pnl'] += pnl
                        
                        stats['overall']['total_trades'] += 1
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        continue  # Skip malformed lines
        except FileNotFoundError:
            return stats
        
        # Calculate win rates
        if stats['overall']['total_trades'] > 0:
            total_wins = sum(s['wins'] for s in stats['by_strategy'].values())
            stats['overall']['win_rate'] = total_wins / stats['overall']['total_trades']
            total_pnl = sum(s['pnl'] for s in stats['by_strategy'].values())
            stats['overall']['avg_pnl'] = total_pnl / stats['overall']['total_trades']
        
        return stats
    
    def get_best_strategies(self) -> List[Dict]:
        """Return strategies sorted by profitability"""
        stats = self.get_recent_performance()
        strategies = []
        
        for name, data in stats['by_strategy'].items():
            total = data['wins'] + data['losses']
            if total >= 3:  # Min 3 trades
                strategies.append({
                    'name': name,
                    'win_rate': data['wins'] / total if total > 0 else 0,
                    'avg_pnl': data['pnl'] / total if total > 0 else 0,
                    'count': total
                })
        
        return sorted(strategies, key=lambda x: x['avg_pnl'], reverse=True)
    
    def suggest_confidence_adjustment(self) -> int:
        """Recommend confidence threshold changes based on win rate"""
        stats = self.get_recent_performance(days=7)
        win_rate = stats['overall'].get('win_rate', 0.5)  # Default 50% if no data
        
        if stats['overall']['total_trades'] < 5:
            return 0  # Not enough data yet
        
        if win_rate < 0.40:
            return 5  # Increase threshold (be more selective)
        elif win_rate > 0.65:
            return -5  # Decrease threshold (take more trades)
        return 0
    
    def get_strategy_boost(self, strategy_name: str) -> int:
        """Get confidence boost for a specific strategy if it's performing well"""
        best_strategies = self.get_best_strategies()
        
        if not best_strategies:
            return 0
        
        # Check if this strategy is in top 2
        top_strategies = [s['name'] for s in best_strategies[:2]]
        if strategy_name in top_strategies:
            strategy_data = next((s for s in best_strategies if s['name'] == strategy_name), None)
            if strategy_data and strategy_data['win_rate'] > 0.50:
                return 5  # Boost confidence by 5 points
        
        return 0
    
    def get_regime_performance(self, regime: str) -> Dict:
        """Get performance stats for a specific market regime"""
        stats = self.get_recent_performance()
        regime_stats = stats['by_regime'].get(regime, {'wins': 0, 'losses': 0, 'pnl': 0})
        
        total_trades = regime_stats['wins'] + regime_stats['losses']
        if total_trades == 0:
            return {'win_rate': 0.5, 'avg_pnl': 0, 'count': 0}  # Default neutral
        
        return {
            'win_rate': regime_stats['wins'] / total_trades,
            'avg_pnl': regime_stats['pnl'] / total_trades if total_trades > 0 else 0,
            'count': total_trades
        }


# Global instance
_performance_tracker_instance = None

def get_performance_tracker() -> PerformanceTracker:
    """Get or create performance tracker instance"""
    global _performance_tracker_instance
    if _performance_tracker_instance is None:
        _performance_tracker_instance = PerformanceTracker()
    return _performance_tracker_instance

