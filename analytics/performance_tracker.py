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
        self.strategy_cooldowns = {}  # Track strategy cooldowns
        self.strategy_stats_cache = {}  # Cache strategy stats
        self.cache_timestamp = None
        self.cache_duration = timedelta(minutes=5)  # Update cache every 5 minutes
    
    def _read_trades(self, days=7, limit=None):
        """Read trades from JSONL file, optionally limited by count"""
        trades = []
        if os.path.exists(self.trades_file):
            with open(self.trades_file, 'r') as f:
                lines = f.readlines()
                if limit:
                    lines = lines[-limit:]  # Get last N trades
                for line in lines:
                    if line.strip():
                        try:
                            trades.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        return trades
    
    def calculate_strategy_performance(self, strategy_type: str, lookback_trades: int = 20) -> Dict:
        """
        Calculate comprehensive performance metrics for a strategy
        Parameters:
            strategy_type: Strategy name (e.g., 'TREND_FOLLOWING', 'BREAKOUT')
            lookback_trades: Number of recent trades to analyze
        Returns:
            dict with win_rate, avg_pnl_pct, profit_factor, trade_count, recent_performance
        """
        trades = self._read_trades(days=30, limit=lookback_trades * 2)
        
        strategy_trades = [t for t in trades if t.get('strategy', '').upper() == strategy_type.upper()]
        
        if len(strategy_trades) > lookback_trades:
            strategy_trades = strategy_trades[-lookback_trades:]
        
        if not strategy_trades:
            return {
                'win_rate': 0.5,
                'avg_pnl_pct': 0,
                'profit_factor': 1.0,
                'trade_count': 0,
                'recent_performance': {'win_rate': 0.5, 'avg_pnl': 0}
            }
        
        wins = []
        losses = []
        
        for trade in strategy_trades:
            pnl = trade.get('pnl_percent', 0) or trade.get('pnl', 0)
            if pnl > 0:
                wins.append(pnl)
            elif pnl < 0:
                losses.append(abs(pnl))
        
        total_trades = len(strategy_trades)
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        avg_pnl = sum(t.get('pnl_percent', 0) or t.get('pnl', 0) for t in strategy_trades) / total_trades if total_trades > 0 else 0
        
        total_wins = sum(wins) if wins else 0
        total_losses = sum(losses) if losses else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else (float('inf') if total_wins > 0 else 1.0)
        
        recent_trades = strategy_trades[-10:] if len(strategy_trades) >= 10 else strategy_trades
        recent_wins = sum(1 for t in recent_trades if (t.get('pnl_percent', 0) or t.get('pnl', 0)) > 0)
        recent_win_rate = recent_wins / len(recent_trades) if recent_trades else 0.5
        recent_avg_pnl = sum(t.get('pnl_percent', 0) or t.get('pnl', 0) for t in recent_trades) / len(recent_trades) if recent_trades else 0
        
        return {
            'win_rate': win_rate,
            'avg_pnl_pct': avg_pnl,
            'profit_factor': profit_factor,
            'trade_count': total_trades,
            'win_count': win_count,
            'loss_count': loss_count,
            'total_wins': total_wins,
            'total_losses': total_losses,
            'recent_performance': {
                'win_rate': recent_win_rate,
                'avg_pnl': recent_avg_pnl,
                'trade_count': len(recent_trades)
            }
        }
    
    def calculate_strategy_boost(self, strategy_type: str, lookback_trades: int = 20) -> Dict:
        """
        Calculate confidence boost/penalty based on strategy performance
        Parameters:
            strategy_type: Strategy name
            lookback_trades: Number of trades to analyze
        Returns:
            dict with boost, win_rate, avg_pnl, trade_count, reason
        """
        stats = self.calculate_strategy_performance(strategy_type, lookback_trades)
        
        win_rate = stats['win_rate']
        avg_pnl = stats['avg_pnl_pct']
        profit_factor = stats['profit_factor']
        trade_count = stats['trade_count']
        
        if trade_count < 5:
            return {
                'boost': 0,
                'win_rate': win_rate,
                'avg_pnl': avg_pnl,
                'trade_count': trade_count,
                'reason': f"Insufficient data ({trade_count} trades)"
            }
        
        boost = 0
        
        if win_rate > 0.70 and avg_pnl > 2:
            boost += 15
        elif win_rate > 0.60 and avg_pnl > 1.5:
            boost += 10
        elif win_rate > 0.50 and avg_pnl > 1:
            boost += 5
        elif win_rate < 0.40:
            boost -= 10
        elif win_rate < 0.30:
            boost -= 20
        
        if profit_factor > 2.0:
            boost += 5
        elif profit_factor < 1.0:
            boost -= 10
        
        recent_stats = self.calculate_strategy_performance(strategy_type, lookback_trades=5)
        if recent_stats['trade_count'] >= 3:
            recent_win_rate = recent_stats['win_rate']
            if recent_win_rate > win_rate + 0.15:
                boost += 5
            elif recent_win_rate < win_rate - 0.15:
                boost -= 5
        
        boost = max(-25, min(20, boost))
        
        return {
            'boost': boost,
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'profit_factor': profit_factor,
            'trade_count': trade_count,
            'reason': f"WR:{win_rate:.1%} PnL:{avg_pnl:.2f}% PF:{profit_factor:.2f}"
        }
    
    def check_strategy_cooldown(self, strategy_type: str) -> tuple[bool, str]:
        """
        Check if strategy is in cooldown due to poor performance
        Returns: (is_cooldown, reason)
        """
        if strategy_type not in self.strategy_cooldowns:
            return False, ""
        
        cooldown_until = self.strategy_cooldowns[strategy_type]
        if datetime.now(timezone.utc) < cooldown_until:
            remaining = (cooldown_until - datetime.now(timezone.utc)).total_seconds() / 3600
            return True, f"Strategy {strategy_type} in cooldown for {remaining:.1f} more hours"
        
        del self.strategy_cooldowns[strategy_type]
        return False, ""
    
    def update_strategy_cooldown(self, strategy_type: str):
        """Set cooldown for strategy if performance is poor"""
        recent_stats = self.calculate_strategy_performance(strategy_type, lookback_trades=10)
        
        if recent_stats['trade_count'] >= 10:
            win_rate = recent_stats['win_rate']
            if win_rate < 0.30:
                cooldown_until = datetime.now(timezone.utc) + timedelta(hours=2)
                self.strategy_cooldowns[strategy_type] = cooldown_until
                print(f"   ⏸️  Strategy {strategy_type} entering cooldown: WR={win_rate:.1%} over last {recent_stats['trade_count']} trades")
                return True
        return False
    
    def get_strategy_dashboard_data(self) -> Dict:
        """Export comprehensive strategy performance dashboard data"""
        strategies = ['TREND_FOLLOWING', 'BREAKOUT', 'MOMENTUM', 'REVERSAL', 'VOLATILITY_BREAKOUT', 'EMA_CROSSOVER']
        
        dashboard = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'strategies': {}
        }
        
        for strategy in strategies:
            stats = self.calculate_strategy_performance(strategy)
            boost_data = self.calculate_strategy_boost(strategy)
            is_cooldown, cooldown_reason = self.check_strategy_cooldown(strategy)
            
            dashboard['strategies'][strategy] = {
                'win_rate': stats['win_rate'],
                'avg_pnl_pct': stats['avg_pnl_pct'],
                'profit_factor': stats['profit_factor'],
                'trade_count': stats['trade_count'],
                'boost': boost_data['boost'],
                'boost_reason': boost_data['reason'],
                'is_cooldown': is_cooldown,
                'cooldown_reason': cooldown_reason,
                'recent_performance': stats['recent_performance']
            }
        
        return dashboard

    def get_recent_performance(self, days: int = 7) -> Dict:
        """Analyze last N days of trades"""
        # This implementation now only reads from JSONL
        stats = {
            'by_strategy': defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0}),
            'by_regime': defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0}),
            'by_confidence': defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0}),
            'overall': {'win_rate': 0, 'avg_pnl': 0, 'total_trades': 0}
        }
        trades = self._read_trades(days)
        for trade in trades:
            try:
                strategy = trade.get('strategy', 'unknown')
                regime = trade.get('regime', 'UNKNOWN')
                confidence = trade.get('confidence', 50)
                confidence_bucket = int(confidence / 10) * 10
                pnl = trade.get('pnl_percent', 0)
                if pnl is None:
                    continue
                is_win = pnl > 0
                stats['by_strategy'][strategy]['wins' if is_win else 'losses'] += 1
                stats['by_strategy'][strategy]['pnl'] += pnl
                stats['by_regime'][regime]['wins' if is_win else 'losses'] += 1
                stats['by_regime'][regime]['pnl'] += pnl
                stats['by_confidence'][confidence_bucket]['wins' if is_win else 'losses'] += 1
                stats['by_confidence'][confidence_bucket]['pnl'] += pnl
                stats['overall']['total_trades'] += 1
            except Exception as e:
                continue
        # Calculate win_rate
        if stats['overall']['total_trades'] > 0:
            total_wins = sum(s['wins'] for s in stats['by_strategy'].values())
            stats['overall']['win_rate'] = total_wins / stats['overall']['total_trades']
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
        """
        Get confidence boost for a specific strategy (legacy method, uses calculate_strategy_boost)
        Returns just the boost value for backward compatibility
        """
        boost_data = self.calculate_strategy_boost(strategy_name)
        return boost_data['boost']
    
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

