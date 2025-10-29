"""
Web UI for Apex Trading Bot
Provides a dashboard to monitor bot performance, trades, and status
"""
import json
import os
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, jsonify, request
from typing import Dict, List

from executor import get_executor
from logger import get_logger
from risk_manager import get_risk_manager
from analytics.performance_tracker import get_performance_tracker
from config import INITIAL_CAPITAL, DECISION_LOG_FILE, TRADE_LOG_FILE, PERFORMANCE_LOG_FILE, ERROR_LOG_FILE

app = Flask(__name__, template_folder='templates', static_folder='static')


def read_jsonl_file(filepath: str, limit: int = 100) -> List[Dict]:
    """Read and parse JSONL file, returning most recent entries"""
    if not os.path.exists(filepath):
        return []
    
    entries = []
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
            # Get last N lines
            for line in lines[-limit:]:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        # Return in chronological order (oldest first)
        return entries
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []


@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/portfolio')
def api_portfolio():
    """Get current portfolio status"""
    try:
        executor = get_executor()
        portfolio = executor.get_portfolio_status()
        
        # Get risk summary
        try:
            risk_manager = get_risk_manager()
            risk_manager.update_portfolio_metrics(portfolio['total_value'])
            risk_summary = risk_manager.get_risk_summary()
        except Exception:
            risk_summary = {'current_drawdown': portfolio.get('drawdown_percent', 0), 'circuit_breaker_level': None}
        
        # Calculate total return
        total_return = ((portfolio['total_value'] - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_value': portfolio['total_value'],
                'initial_capital': INITIAL_CAPITAL,
                'total_return': total_return,
                'available_balance': portfolio.get('available_balance', 0),
                'unrealized_pnl': portfolio.get('unrealized_pnl', 0),
                'drawdown_percent': portfolio.get('drawdown_percent', 0),
                'position_count': portfolio.get('position_count', 0),
                'circuit_breaker_level': risk_summary.get('circuit_breaker_level'),
                'positions': portfolio.get('positions', [])
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/metrics')
def api_metrics():
    """Get performance metrics"""
    try:
        logger = get_logger()
        metrics = logger.calculate_metrics()
        
        # Get risk summary
        try:
            risk_manager = get_risk_manager()
            risk_summary = risk_manager.get_risk_summary()
        except Exception:
            risk_summary = {}
        
        return jsonify({
            'status': 'success',
            'data': {
                **metrics,
                'circuit_breaker': risk_summary.get('circuit_breaker_level'),
                'current_drawdown': risk_summary.get('current_drawdown', 0)
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/trades')
def api_trades():
    """Get recent trades"""
    try:
        limit = int(request.args.get('limit', 50))
        trades = read_jsonl_file(TRADE_LOG_FILE, limit)
        
        # Sort by timestamp (most recent first)
        trades.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({
            'status': 'success',
            'data': trades
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/decisions')
def api_decisions():
    """Get recent decisions"""
    try:
        limit = int(request.args.get('limit', 50))
        decisions = read_jsonl_file(DECISION_LOG_FILE, limit)
        
        # Sort by timestamp (most recent first)
        decisions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({
            'status': 'success',
            'data': decisions
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/performance')
def api_performance():
    """Get performance history for charts"""
    try:
        hours = int(request.args.get('hours', 24))
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        snapshots = read_jsonl_file(PERFORMANCE_LOG_FILE, limit=1000)
        
        # Filter by time and sort
        filtered = [
            s for s in snapshots 
            if datetime.fromisoformat(s['timestamp'].replace('Z', '+00:00')) >= cutoff
        ]
        filtered.sort(key=lambda x: x.get('timestamp', ''))
        
        return jsonify({
            'status': 'success',
            'data': filtered
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/errors')
def api_errors():
    """Get recent errors"""
    try:
        limit = int(request.args.get('limit', 20))
        errors = read_jsonl_file(ERROR_LOG_FILE, limit)
        
        # Sort by timestamp (most recent first)
        errors.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({
            'status': 'success',
            'data': errors
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/performance-by-strategy')
def api_performance_by_strategy():
    """Get performance breakdown by strategy/regime"""
    try:
        tracker = get_performance_tracker()
        stats = tracker.get_recent_performance(days=7)
        
        return jsonify({
            'status': 'success',
            'data': {
                'by_strategy': dict(stats['by_strategy']),
                'by_regime': dict(stats['by_regime']),
                'by_confidence': dict(stats['by_confidence']),
                'overall': stats['overall']
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/health')
def api_health():
    """Get bot health status"""
    try:
        from health_monitor import get_health_monitor
        
        health_monitor = get_health_monitor()
        health = health_monitor.monitor_health()
        
        # Get agent stats
        try:
            from deepseek_agent import get_deepseek_agent
            agent = get_deepseek_agent()
            agent_stats = agent.get_stats()
        except Exception:
            agent_stats = {}
        
        return jsonify({
            'status': 'success',
            'data': {
                'overall': health.get('overall', False),
                'loop_running': health.get('loop_running', False),
                'error_rate_ok': health.get('error_rate_ok', False),
                'apis_ok': health.get('apis_ok', False),
                'agent_stats': agent_stats,
                'time_since_cycle': health.get('time_since_cycle', 0)
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("=" * 70)
    print("🌐 Starting Apex Trading Bot Web UI")
    print("=" * 70)
    print("📍 Dashboard: http://localhost:5000")
    print("=" * 70)
    
    app.run(host='0.0.0.0', port=5001, debug=False)

