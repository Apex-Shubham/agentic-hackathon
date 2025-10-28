"""
Main Trading Bot Orchestrator
Coordinates all modules and runs the main trading loop
"""
import sys
import time
import signal
import atexit
from datetime import datetime, timedelta, timezone
from typing import Dict

from config import (
    validate_config, COMPETITION_START_DATE, COMPETITION_DURATION_DAYS,
    CHECK_INTERVAL_SECONDS, TRADING_ASSETS, INITIAL_CAPITAL
)
from data_pipeline import DataPipeline
from market_analyzer import get_analyzer
from deepseek_agent import get_deepseek_agent
from risk_manager import get_risk_manager
from executor import get_executor
from logger import get_logger
from health_monitor import get_health_monitor


class TradingBot:
    """Main trading bot orchestrator"""
    
    def __init__(self):
        print("=" * 70)
        print("🤖 AUTONOMOUS AI TRADING BOT - INITIALIZING")
        print("=" * 70)
        
        # Validate configuration
        try:
            validate_config()
            print("✅ Configuration validated")
        except ValueError as e:
            print(f"❌ Configuration error: {e}")
            sys.exit(1)
        
        # Initialize modules
        self.data_pipeline = DataPipeline()
        self.analyzer = get_analyzer()
        self.deepseek_agent = get_deepseek_agent()
        self.risk_manager = get_risk_manager()
        self.executor = get_executor()
        self.logger = get_logger()
        self.health_monitor = get_health_monitor()
        
        # Competition tracking
        self.start_time = datetime.now(timezone.utc)
        self.competition_start = datetime.fromisoformat(COMPETITION_START_DATE.replace('Z', '+00:00'))
        self.competition_end = self.competition_start + timedelta(days=COMPETITION_DURATION_DAYS)
        
        # State
        self.running = True
        self.cycle_count = 0
        
        print(f"📅 Competition: {COMPETITION_DURATION_DAYS} days")
        print(f"💰 Initial Capital: ${INITIAL_CAPITAL:,.2f}")
        print(f"📊 Trading Assets: {', '.join(TRADING_ASSETS)}")
        print(f"⏱️  Check Interval: {CHECK_INTERVAL_SECONDS}s")
        print("=" * 70)
        
        # Register cleanup handlers
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, lambda s, f: self.shutdown())
        signal.signal(signal.SIGTERM, lambda s, f: self.shutdown())
        
        # Test connections
        if not self._test_connections():
            print("❌ Connection tests failed. Please check your API keys.")
            sys.exit(1)
    
    def _test_connections(self) -> bool:
        """Test all external connections"""
        print("\n🔌 Testing connections...")
        
        # Test Binance
        if not self.data_pipeline.test_connection():
            return False
        
        print("✅ All connections successful\n")
        return True
    
    def run(self):
        """Main trading loop"""
        print("🚀 STARTING AUTONOMOUS TRADING")
        print("=" * 70)
        print("⚠️  Bot will run continuously for 14 days")
        print("⚠️  Do not interrupt unless absolutely necessary")
        print("=" * 70)
        print()
        
        while self.running:
            try:
                # Check if competition has ended
                if self._competition_ended():
                    print("\n🏁 Competition period completed!")
                    self.shutdown()
                    break
                
                # Health check
                if not self._health_check():
                    print("⚠️ Health check failed, attempting recovery...")
                    time.sleep(60)
                    continue
                
                # Execute trading cycle
                self._trading_cycle()
                
                # Record successful cycle
                self.health_monitor.record_successful_cycle()
                self.cycle_count += 1
                
                # Sleep until next cycle
                time.sleep(CHECK_INTERVAL_SECONDS)
                
            except KeyboardInterrupt:
                print("\n⚠️ Keyboard interrupt received")
                self.shutdown()
                break
                
            except Exception as e:
                print(f"\n❌ Error in main loop: {e}")
                self.health_monitor.handle_error(e, {'location': 'main_loop'})
                
                # Check if we need to restart
                if self.health_monitor.auto_restart_on_crash():
                    print("🔄 Attempting to continue after error...")
                
                time.sleep(30)  # Wait before retrying
    
    def _trading_cycle(self):
        """Execute one complete trading cycle"""
        current_day = self._get_competition_day()
        
        # Log cycle start
        if self.cycle_count % 12 == 0:  # Every hour (12 * 5min)
            print(f"\n⏰ [{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] Day {current_day}/14 | Cycle #{self.cycle_count}")
        
        # Get portfolio status first
        portfolio = self.executor.get_portfolio_status()
        
        # Update risk manager with current portfolio value
        self.risk_manager.update_portfolio_metrics(portfolio['total_value'])
        
        # Log performance snapshot
        self.logger.log_performance_snapshot(portfolio)
        
        # Check circuit breakers
        can_trade, reason = self.risk_manager.check_circuit_breakers()
        if not can_trade:
            print(f"🛑 Trading halted: {reason}")
            
            # If circuit breaker active, close risky positions
            if self.risk_manager.circuit_breaker_level in ['LEVEL_2', 'LEVEL_3', 'LEVEL_4']:
                positions = portfolio.get('positions', [])
                for pos in positions:
                    if pos['pnl_percent'] < -3:  # Close losing positions
                        print(f"   Closing losing position: {pos['symbol']} ({pos['pnl_percent']:.1f}%)")
                        self.executor.close_position(pos['symbol'])
            
            return
        
        # Update trailing stops for existing positions
        self.executor.update_trailing_stops()
        
        # Analyze each asset
        for asset in TRADING_ASSETS:
            try:
                self._analyze_and_trade(asset, portfolio, current_day)
            except Exception as e:
                print(f"❌ Error processing {asset}: {e}")
                self.health_monitor.handle_error(e, {'asset': asset, 'action': 'analyze_and_trade'})
        
        # Print status summary periodically
        if self.cycle_count % 12 == 0:
            self._print_status(portfolio)
    
    def _analyze_and_trade(self, asset: str, portfolio: Dict, day_number: int):
        """Analyze asset and execute trade if appropriate"""
        
        # Fetch market data
        market_data = self.data_pipeline.fetch_realtime_data(asset)
        
        # Validate data
        if not self.health_monitor.validate_data_integrity(market_data):
            print(f"⚠️ Invalid data for {asset}, skipping...")
            return
        
        # Get market regime
        regime = market_data.get('regime', 'UNKNOWN')
        
        # Check if we already have a position in this asset
        existing_position = None
        for pos in portfolio.get('positions', []):
            if pos['symbol'] == asset:
                existing_position = pos
                break
        
        # If we have an existing position, check if we should close it
        if existing_position:
            # Close if significant loss or stale position
            pnl = existing_position['pnl_percent']
            
            if pnl < -5:  # Stop loss triggered at software level
                print(f"🛑 Closing {asset}: Stop loss triggered ({pnl:.1f}%)")
                result = self.executor.close_position(asset)
                self.logger.log_trade(result)
                return
            
            # Don't open new position if we already have one
            return
        
        # Get LLM decision
        try:
            decision = self.deepseek_agent.get_decision(market_data, portfolio, day_number)
        except Exception as e:
            print(f"⚠️ DeepSeek API error for {asset}, using fallback...")
            self.health_monitor.handle_api_failure('deepseek', e)
            decision = self.deepseek_agent.get_fallback_decision(market_data, portfolio)
        
        # Skip if HOLD or low confidence
        if decision['action'] == 'HOLD' or decision['confidence'] < 70:
            return
        
        # Calculate position size
        position_size = self.risk_manager.calculate_position_size(
            decision['confidence'],
            regime,
            day_number,
            self.risk_manager.current_drawdown
        )
        
        # Skip if position size too small
        if position_size == 0:
            return
        
        # Calculate leverage
        leverage = self.risk_manager.calculate_optimal_leverage(
            decision['confidence'],
            regime
        )
        
        # Validate trade
        is_valid, validation_msg = self.risk_manager.validate_trade(
            decision, portfolio, position_size, leverage
        )
        
        if not is_valid:
            print(f"⚠️ Trade validation failed for {asset}: {validation_msg}")
            return
        
        # Execute trade
        if decision['action'] in ['LONG', 'SHORT']:
            position_size_dollars = portfolio['total_value'] * position_size
            
            print(f"\n📈 EXECUTING {decision['action']} on {asset}")
            print(f"   Confidence: {decision['confidence']:.0f}%")
            print(f"   Position Size: {position_size:.1%} (${position_size_dollars:,.2f})")
            print(f"   Leverage: {leverage}x")
            print(f"   Reason: {decision['entry_reason']}")
            
            result = self.executor.execute_trade(
                asset, decision, position_size_dollars, leverage
            )
            
            # Log decision and trade
            self.logger.log_decision(decision, market_data, result)
            
            if result['status'] == 'SUCCESS':
                self.logger.log_trade(result)
                self.risk_manager.total_trades_today += 1
            else:
                print(f"   ❌ Trade execution failed: {result.get('message')}")
        
        elif decision['action'] == 'CLOSE' and existing_position:
            print(f"\n📉 CLOSING position on {asset}")
            print(f"   Reason: {decision['entry_reason']}")
            
            result = self.executor.close_position(asset)
            self.logger.log_decision(decision, market_data, result)
            
            if result['status'] == 'SUCCESS':
                self.logger.log_trade(result)
    
    def _health_check(self) -> bool:
        """Perform health check"""
        health = self.health_monitor.monitor_health()
        
        if not health['overall']:
            print(f"⚠️ Health issues detected:")
            if not health['loop_running']:
                print(f"   - Loop may be stuck ({health['time_since_cycle']:.0f}s since last cycle)")
            if not health['error_rate_ok']:
                print(f"   - High error rate ({health['consecutive_errors']} consecutive errors)")
            if not health['apis_ok']:
                print(f"   - API issues detected")
            
            return False
        
        return True
    
    def _print_status(self, portfolio: Dict):
        """Print current status summary"""
        metrics = self.logger.calculate_metrics()
        risk_summary = self.risk_manager.get_risk_summary()
        
        print(f"\n{'='*70}")
        print(f"📊 STATUS SUMMARY")
        print(f"{'='*70}")
        print(f"Portfolio Value:    ${portfolio['total_value']:>15,.2f}")
        print(f"Total Return:       {metrics['total_return']:>14.2f}%")
        print(f"Drawdown:           {risk_summary['current_drawdown']:>14.2f}%")
        print(f"Open Positions:     {portfolio['position_count']:>15d}")
        print(f"Total Trades:       {metrics['total_trades']:>15d}")
        print(f"Win Rate:           {metrics['win_rate']:>14.2f}%")
        print(f"Sharpe Ratio:       {metrics['sharpe_ratio']:>15.2f}")
        
        if risk_summary['circuit_breaker_level']:
            print(f"⚠️  Circuit Breaker:  {risk_summary['circuit_breaker_level']}")
        
        print(f"{'='*70}\n")
    
    def _get_competition_day(self) -> int:
        """Get current day of competition (1-14 or fractional for tests)"""
        elapsed = datetime.now(timezone.utc) - self.competition_start
        # Calculate fractional day for test runs
        day = elapsed.total_seconds() / (24 * 3600)
        day = min(day + 1, COMPETITION_DURATION_DAYS + 1)
        return max(1, int(day))
    
    def _competition_ended(self) -> bool:
        """Check if competition period has ended"""
        return datetime.now(timezone.utc) >= self.competition_end
    
    def shutdown(self):
        """Graceful shutdown"""
        print("\n" + "="*70)
        print("🛑 SHUTTING DOWN TRADING BOT")
        print("="*70)
        
        self.running = False
        
        # Close all positions
        print("\n📊 Closing all open positions...")
        self.executor.close_all_positions()
        
        # Generate final report
        print("\n📈 Generating final report...")
        self.logger.generate_final_report()
        
        print("\n✅ Shutdown complete")
        print("="*70)
    
    def cleanup(self):
        """Cleanup function called on exit"""
        if self.running:
            self.shutdown()


def main():
    """Main entry point"""
    try:
        bot = TradingBot()
        bot.run()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

