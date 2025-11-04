"""
Logging & Monitoring Module
Handles all logging, performance tracking, and report generation
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any
import pandas as pd
import numpy as np
from config import (
    LOG_DIR, DECISION_LOG_FILE, TRADE_LOG_FILE,
    PERFORMANCE_LOG_FILE, ERROR_LOG_FILE, INITIAL_CAPITAL,
    ASSESSMENT_LOG_FILE
)


class BotLogger:
    """Centralized logging system for the trading bot"""
    
    def __init__(self, log_dir=LOG_DIR, initial_capital=None):
        self.start_time = datetime.now(timezone.utc)
        self.initial_capital = INITIAL_CAPITAL
        self.trades = []
        self.decisions = []
        self.performance_snapshots = []
        
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        self.log_dir = log_dir
    
    def log_decision(self, decision: Dict, market_data: Dict, execution_result: Dict = None):
        """Log a trading decision"""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'asset': market_data.get('symbol', 'UNKNOWN'),
            'action': decision.get('action'),
            'confidence': decision.get('confidence'),
            'position_size_percent': decision.get('position_size_percent'),
            'leverage': decision.get('leverage'),
            'entry_reason': decision.get('entry_reason'),
            'stop_loss_percent': decision.get('stop_loss_percent'),
            'take_profit_percent': decision.get('take_profit_percent'),
            'urgency': decision.get('urgency'),
            'market_price': market_data.get('price'),
            'market_regime': market_data.get('regime'),
            'strategy': decision.get('strategy') or execution_result.get('strategy') or 'unknown',  # Extract strategy
            'execution_result': execution_result
        }
        
        self.decisions.append(log_entry)
        
        # Append to file
        with open(DECISION_LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def log_trade(self, trade_details: Dict, strategy: str = None, regime: str = None, confidence: float = None):
        """Log a trade execution with optional strategy/regime for performance tracking"""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'symbol': trade_details.get('symbol'),
            'side': trade_details.get('side'),
            'quantity': trade_details.get('quantity'),
            'entry_price': trade_details.get('entry_price'),
            'exit_price': trade_details.get('exit_price'),
            'leverage': trade_details.get('leverage'),
            'pnl': trade_details.get('pnl'),
            'pnl_percent': trade_details.get('pnl_percent'),
            'stop_loss_price': trade_details.get('stop_loss_price'),
            'take_profit_price': trade_details.get('take_profit_price'),
            'order_id': trade_details.get('order_id'),
            'status': trade_details.get('status'),
            'strategy': strategy or trade_details.get('strategy') or 'unknown',
            'regime': regime or trade_details.get('regime') or 'UNKNOWN',
            'confidence': confidence or trade_details.get('confidence')
        }
        
        self.trades.append(log_entry)
        
        # Append to file
        with open(TRADE_LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def log_performance_snapshot(self, portfolio: Dict):
        """Log current portfolio performance"""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'portfolio_value': portfolio.get('total_value'),
            'available_balance': portfolio.get('available_balance'),
            'unrealized_pnl': portfolio.get('unrealized_pnl'),
            'open_positions': len(portfolio.get('positions', [])),
            'drawdown_percent': portfolio.get('drawdown_percent'),
            'total_return_percent': ((portfolio.get('total_value', INITIAL_CAPITAL) - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
        }
        
        self.performance_snapshots.append(log_entry)
        
        # Append to file
        with open(PERFORMANCE_LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def log_error(self, error: Exception, context: Dict = None):
        """Log an error with context"""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }
        
        # Append to file
        with open(ERROR_LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Also print to console for visibility
        print(f"❌ ERROR [{log_entry['timestamp']}]: {error}")
        if context:
            print(f"   Context: {context}")

    def log_assessment(self, assessment: Dict):
        """Log detailed market assessment/thoughts for an asset and cycle."""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **assessment,
        }
        # Append to file
        with open(ASSESSMENT_LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def calculate_metrics(self) -> Dict:
        """Calculate performance metrics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'total_return': 0
            }
        
        trades_df = pd.DataFrame(self.trades)
        
        # Filter completed trades with PnL
        completed_trades = trades_df[trades_df['pnl'].notna()]
        
        if len(completed_trades) == 0:
            # Ensure full metrics schema even when no completed trades yet
            return {
                'total_trades': len(trades_df),
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'sharpe_ratio': self._calculate_sharpe_ratio(),
                'max_drawdown': self._calculate_max_drawdown(),
                'total_return': (
                    ((self.performance_snapshots[-1]['portfolio_value'] - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
                    if self.performance_snapshots else 0
                )
            }
        
        # Calculate metrics
        winning_trades = completed_trades[completed_trades['pnl'] > 0]
        losing_trades = completed_trades[completed_trades['pnl'] <= 0]
        
        win_rate = len(winning_trades) / len(completed_trades) * 100 if len(completed_trades) > 0 else 0
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = abs(losing_trades['pnl'].mean()) if len(losing_trades) > 0 else 0
        
        total_wins = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        total_losses = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Calculate Sharpe ratio from performance snapshots
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown()
        
        # Calculate total return
        if self.performance_snapshots:
            latest_value = self.performance_snapshots[-1]['portfolio_value']
            total_return = ((latest_value - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
        else:
            total_return = 0
        
        return {
            'total_trades': len(completed_trades),
            'win_rate': round(win_rate, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'total_return': round(total_return, 2)
        }
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio from returns"""
        if len(self.performance_snapshots) < 2:
            return 0
        
        df = pd.DataFrame(self.performance_snapshots)
        df['returns'] = df['portfolio_value'].pct_change()
        
        # Remove NaN values
        returns = df['returns'].dropna()
        
        if len(returns) < 2:
            return 0
        
        # Annualized Sharpe ratio (assuming 5-minute intervals)
        mean_return = returns.mean()
        std_return = returns.std()
        
        if std_return == 0:
            return 0
        
        # Annualize: 288 five-minute periods per day, 365 days per year
        sharpe = (mean_return / std_return) * np.sqrt(288 * 365)
        
        return sharpe
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown percentage"""
        if not self.performance_snapshots:
            return 0
        
        df = pd.DataFrame(self.performance_snapshots)
        values = df['portfolio_value'].values
        
        peak = values[0]
        max_dd = 0
        
        for value in values:
            if value > peak:
                peak = value
            dd = ((peak - value) / peak) * 100
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def generate_daily_report(self, day_number: int) -> str:
        """Generate daily performance report"""
        metrics = self.calculate_metrics()
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║               DAILY PERFORMANCE REPORT - DAY {day_number:2d}              ║
╚══════════════════════════════════════════════════════════════╝

📊 PERFORMANCE METRICS
  Total Return:        {metrics['total_return']:>10.2f}%
  Max Drawdown:        {metrics['max_drawdown']:>10.2f}%
  Sharpe Ratio:        {metrics['sharpe_ratio']:>10.2f}

📈 TRADING STATISTICS
  Total Trades:        {metrics['total_trades']:>10d}
  Win Rate:            {metrics['win_rate']:>10.2f}%
  Avg Win:             ${metrics['avg_win']:>10.2f}
  Avg Loss:            ${metrics['avg_loss']:>10.2f}
  Profit Factor:       {metrics['profit_factor']:>10.2f}

⏰ Runtime: {self._get_runtime()}

{"✅ ON TRACK" if metrics['total_return'] > 0 and metrics['max_drawdown'] < 30 else "⚠️  NEEDS IMPROVEMENT"}
"""
        
        print(report)
        return report
    
    def generate_final_report(self) -> str:
        """Generate final competition report"""
        metrics = self.calculate_metrics()
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║            🏆 FINAL COMPETITION REPORT 🏆                    ║
╚══════════════════════════════════════════════════════════════╝

📊 FINAL PERFORMANCE
  Initial Capital:     ${INITIAL_CAPITAL:>10,.2f}
  Final Value:         ${INITIAL_CAPITAL * (1 + metrics['total_return']/100):>10,.2f}
  Total Return:        {metrics['total_return']:>10.2f}%
  Max Drawdown:        {metrics['max_drawdown']:>10.2f}%
  Sharpe Ratio:        {metrics['sharpe_ratio']:>10.2f}

📈 TRADING STATISTICS
  Total Trades:        {metrics['total_trades']:>10d}
  Winning Trades:      {int(metrics['total_trades'] * metrics['win_rate'] / 100):>10d}
  Losing Trades:       {int(metrics['total_trades'] * (100 - metrics['win_rate']) / 100):>10d}
  Win Rate:            {metrics['win_rate']:>10.2f}%
  Profit Factor:       {metrics['profit_factor']:>10.2f}

🎯 COMPETITION SCORE (Estimated)
  Returns Component (60%):         {metrics['total_return'] * 0.6:.2f}
  Risk-Adjusted (40%):              {metrics['sharpe_ratio'] * 10:.2f}
  
⏰ Total Runtime: {self._get_runtime()}

{"✅ COMPETITION RULES COMPLIED" if metrics['max_drawdown'] < 40 else "❌ DISQUALIFIED - MAX DRAWDOWN EXCEEDED"}
"""
        
        print(report)
        
        # Save to file
        with open(f'{self.log_dir}/final_report.txt', 'w') as f:
            f.write(report)
        
        return report
    
    def _get_runtime(self) -> str:
        """Get formatted runtime"""
        runtime = datetime.now(timezone.utc) - self.start_time
        days = runtime.days
        hours = runtime.seconds // 3600
        minutes = (runtime.seconds % 3600) // 60
        return f"{days}d {hours}h {minutes}m"
    
    def log_info(self, message: str):
        """Log informational message"""
        timestamp = datetime.now(timezone.utc).isoformat()
        print(f"ℹ️  [{timestamp}] {message}")

    def close(self):
        pass

    def get_realized_pnl(self):
        """Sum realized PnL across all closed trades (where 'pnl' is present)."""
        if not self.trades:
            return 0.0
        return sum([t['pnl'] for t in self.trades if t.get('pnl') is not None])


# Global logger instance
_logger_instance = None

def get_logger(initial_capital=None) -> BotLogger:
    """Get or create global logger instance. initial_capital used on first create only."""
    global _logger_instance
    if _logger_instance is None:
        if initial_capital is not None:
            _logger_instance = BotLogger()
            _logger_instance.initial_capital = initial_capital
        else:
            _logger_instance = BotLogger()
    return _logger_instance

