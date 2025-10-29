"""
Main Trading Bot Orchestrator - FIXED VERSION
Uses actual Binance balance and proper competition date checking
"""
import sys
import time
import signal
import atexit
from datetime import datetime, timedelta, timezone
from typing import Dict

from config import (
    validate_config, COMPETITION_START_DATE, COMPETITION_DURATION_DAYS,
    CHECK_INTERVAL_SECONDS, TRADING_ASSETS, get_binance_balance, MIN_CONFIDENCE,
    INITIAL_CAPITAL, MAX_OPEN_POSITIONS, MAX_POSITIONS_PER_SYMBOL
)
from data_pipeline import DataPipeline
from market_analyzer import get_analyzer
from deepseek_agent import get_deepseek_agent
from risk_manager import get_risk_manager
from executor import get_executor
from logger import get_logger
from health_monitor import get_health_monitor


class TradingBot:
    """Main trading bot orchestrator with enhanced signals"""
    
    def __init__(self):
        print("=" * 70)
        print("🤖 ENHANCED AUTONOMOUS AI TRADING BOT - INITIALIZING")
        print("=" * 70)
        
        # Validate configuration
        try:
            validate_config()
            print("✅ Configuration validated")
        except ValueError as e:
            print(f"❌ Configuration error: {e}")
            sys.exit(1)
        
        # FIXED: Get actual balance from Binance instead of using hardcoded value
        self.initial_capital = get_binance_balance()
        print(f"💰 Fetched Balance from Binance: ${self.initial_capital:,.2f}")
        
        # Initialize modules
        self.data_pipeline = DataPipeline()
        self.analyzer = get_analyzer()
        self.deepseek_agent = get_deepseek_agent()
        
        # FIXED: Pass actual balance to risk manager
        self.risk_manager = get_risk_manager(initial_capital=self.initial_capital)
        self.executor = get_executor()
        self.logger = get_logger(initial_capital=self.initial_capital)
        self.health_monitor = get_health_monitor()
        
        # Telegram bot integration removed
        
        # Competition tracking
        self.start_time = datetime.now(timezone.utc)
        self.competition_start = datetime.fromisoformat(COMPETITION_START_DATE.replace('Z', '+00:00'))
        self.competition_end = self.competition_start + timedelta(days=COMPETITION_DURATION_DAYS)
        
        # FIXED: Calculate days elapsed properly
        days_elapsed = (self.start_time - self.competition_start).total_seconds() / 86400
        
        # State
        self.running = True
        self.cycle_count = 0
        
        print(f"📅 Competition: Day {days_elapsed:.3f} of {COMPETITION_DURATION_DAYS}")
        print(f"💰 Initial Capital: ${self.initial_capital:,.2f}")
        print(f"📊 Trading Assets: {', '.join(TRADING_ASSETS)}")
        print(f"⏱️  Check Interval: {CHECK_INTERVAL_SECONDS}s")
        print(f"🎯 Enhanced Signals: Multi-confirmation + Smart Exits")
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
        print("🚀 STARTING ENHANCED AUTONOMOUS TRADING")
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

        # Optionally force a single initial trade to bootstrap
        self._force_initial_trade_once(portfolio, current_day)
        
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
        
        # Update trailing stops and close stale positions
        self.executor.update_trailing_stops()
        self.executor.close_stale_positions()
        
        # Analyze each asset
        for asset in TRADING_ASSETS:
            try:
                # Refresh portfolio before each asset to consider any prior trades
                portfolio = self.executor.get_portfolio_status()
                self._analyze_and_trade(asset, portfolio, current_day)
            except Exception as e:
                print(f"❌ Error processing {asset}: {e}")
                self.health_monitor.handle_error(e, {'asset': asset, 'action': 'analyze_and_trade'})
        
        # Print status summary periodically
        if self.cycle_count % 12 == 0:
            self._print_status(portfolio)
    
    def _analyze_and_trade(self, asset: str, portfolio: Dict, day_number: int):
        """ENHANCED: Analyze asset and execute trade with improved signals"""
        
        # Fetch market data
        market_data = self.data_pipeline.fetch_realtime_data(asset)
        
        # Validate data
        if not self.health_monitor.validate_data_integrity(market_data):
            print(f"⚠️ Invalid data for {asset}, skipping...")
            return
        
        # Get market regime and indicators
        regime = market_data.get('regime', 'UNKNOWN')
        indicators = market_data.get('indicators', {})
        
        # Check existing positions for this asset (PYRAMIDING ALLOWED - max 2 per symbol)
        existing_positions = []
        open_positions = portfolio.get('positions', [])
        for pos in open_positions:
            if pos['symbol'] == asset:
                existing_positions.append(pos)
        
        # Count positions per symbol
        positions_on_symbol = len(existing_positions)
        from config import MAX_POSITIONS_PER_SYMBOL
        
        if existing_positions:
            print(f"\n🔍 Checking existing positions for {asset}:")
            for i, pos in enumerate(existing_positions, 1):
                print(f"   Position #{i}: {pos.get('side', 'UNKNOWN')} | PnL: {pos.get('pnl_percent', 0):+.2f}%")
            print(f"   Total positions on {asset}: {positions_on_symbol}/{MAX_POSITIONS_PER_SYMBOL}")
        
        # ========================================
        # ENHANCED EXIT LOGIC (only for worst performing position if multiple)
        # ========================================
        if existing_positions:
            # Find worst performing position for exit signals
            worst_position = min(existing_positions, key=lambda p: p.get('pnl_percent', 0))
            pnl = worst_position['pnl_percent']
            
            # Emergency stop loss at -5%
            if pnl < -5:
                print(f"🛑 Emergency Stop Loss: Closing worst position on {asset} at {pnl:.1f}%")
                result = self.executor.close_position(asset)
                self.logger.log_trade(result)
                # Continue to allow pyramiding if under limit
                if positions_on_symbol - 1 >= MAX_POSITIONS_PER_SYMBOL:
                    return  # Can't pyramid if still at limit after closing
            
            # Check enhanced exit signals from market analyzer (on worst position)
            should_exit, exit_reason, exit_confidence = self.analyzer.should_exit_position(
                worst_position, market_data, indicators
            )
            
            if should_exit and exit_confidence >= 75:
                print(f"\n📉 SMART EXIT SIGNAL for {asset}")
                print(f"   Exit Confidence: {exit_confidence}%")
                print(f"   Closing position with PnL: {pnl:+.2f}%")
                print(f"   Reason: {exit_reason}")
                
                result = self.executor.close_position(asset)
                
                # Create decision object for logging
                exit_decision = {
                    'action': 'CLOSE',
                    'confidence': exit_confidence,
                    'entry_reason': exit_reason
                }
                self.logger.log_decision(exit_decision, market_data, result)
                
                if result['status'] == 'SUCCESS':
                    strategy = 'EXIT_SIGNAL'  # Mark as exit signal strategy
                    regime = market_data.get('regime', 'UNKNOWN')
                    self.logger.log_trade(result, strategy=strategy, regime=regime, confidence=exit_confidence)
                    # Continue to allow pyramiding if under limit after close
                    if positions_on_symbol - 1 >= MAX_POSITIONS_PER_SYMBOL:
                        return  # Can't pyramid if still at limit after closing
                else:
                    # If close failed, still allow pyramiding if under limit
                    pass
        
        # ========================================
        # ENHANCED ENTRY LOGIC (PYRAMIDING ALLOWED)
        # ========================================
        
        # Check if we can add more positions (pyramiding check)
        if positions_on_symbol >= MAX_POSITIONS_PER_SYMBOL:
            print(f"   ⚠️ Already at max positions ({positions_on_symbol}/{MAX_POSITIONS_PER_SYMBOL}) for {asset}")
            print(f"   💡 Will skip pyramiding - waiting for exit signals or position closure")
            return
        
        # Get LLM decision (LLM will evaluate if pyramiding is profitable)
        try:
            decision = self.deepseek_agent.get_decision(market_data, portfolio, day_number)
        except Exception as e:
            print(f"⚠️ DeepSeek API error for {asset}, using fallback...")
            self.health_monitor.handle_api_failure('deepseek', e)
            decision = self.deepseek_agent.get_fallback_decision(market_data, portfolio)
        
        # Skip if HOLD or low confidence (lower threshold in volatile markets)
        from config import MIN_CONFIDENCE_VOLATILE
        min_conf = MIN_CONFIDENCE_VOLATILE if market_data.get('regime') == 'VOLATILE' else MIN_CONFIDENCE
        if decision['action'] == 'HOLD' or decision['confidence'] < min_conf:
            return
        
        # Calculate position size and leverage (confidence-based)
        portfolio_value = portfolio.get('total_value', INITIAL_CAPITAL)
        position_info = self.risk_manager.calculate_position_size(
            balance=portfolio_value,
            confidence=decision['confidence'],
            market_data=market_data
        )
        
        # Extract size and leverage from result
        position_size = position_info['size_percent'] / 100.0  # Convert back to decimal for validation
        leverage = position_info['leverage']
        position_size_dollars = position_info['size']
        
        # Skip if position size too small
        if position_size == 0:
            return
        
        # Detailed logging before validation
        open_positions = portfolio.get('positions', [])
        available_balance = portfolio.get('available_balance', 0)
        positions_on_this_symbol = len([p for p in open_positions if p.get('symbol') == asset])
        
        print(f"\n🔍 Trade validation for {asset}:")
        if positions_on_this_symbol > 0:
            print(f"   🏗️  PYRAMIDING: Adding position #{positions_on_this_symbol + 1} (already have {positions_on_this_symbol})")
            for i, pos in enumerate([p for p in open_positions if p.get('symbol') == asset], 1):
                print(f"      Existing #{i}: {pos.get('side', 'UNKNOWN')} | PnL: {pos.get('pnl_percent', 0):+.2f}%")
        else:
            print(f"   📊 NEW POSITION: No existing positions on {asset}")
        print(f"   Total portfolio positions: {len(open_positions)}/{MAX_OPEN_POSITIONS}")
        print(f"   Positions on {asset}: {positions_on_this_symbol}/{MAX_POSITIONS_PER_SYMBOL}")
        print(f"   Confidence: {decision['confidence']:.1f}% (threshold: {min_conf}%)")
        print(f"   Position size: ${position_size_dollars:,.2f} ({position_size:.1%})")
        print(f"   Leverage: {leverage}x")
        print(f"   Available balance: ${available_balance:,.2f}")
        
        # Check each rejection reason
        if positions_on_this_symbol >= MAX_POSITIONS_PER_SYMBOL:
            print(f"   ❌ REJECTED: Max positions per symbol ({MAX_POSITIONS_PER_SYMBOL}) reached")
        elif len(open_positions) >= MAX_OPEN_POSITIONS:
            print(f"   ❌ REJECTED: Max total positions ({MAX_OPEN_POSITIONS}) reached")
        elif decision['confidence'] < min_conf:
            print(f"   ❌ REJECTED: Confidence too low")
        elif position_size_dollars > available_balance * 0.95:
            print(f"   ❌ REJECTED: Position too large (>95% of available balance)")
        else:
            print(f"   ✅ Passing validation checks")
        
        # Validate trade
        is_valid, validation_msg = self.risk_manager.validate_trade(
            decision, portfolio, position_size, leverage, symbol=asset
        )
        
        if not is_valid:
            print(f"   ❌ Validation failed: {validation_msg}")
            return
        else:
            print(f"   ✅ Validation passed")
        
        # Execute trade
        if decision['action'] in ['LONG', 'SHORT']:
            # Use position_size_dollars already calculated from position_info
            
            print(f"\n📈 EXECUTING {decision['action']} on {asset}")
            print(f"   Confidence: {decision['confidence']:.0f}%")
            print(f"   Position Size: {position_size:.1%} (${position_size_dollars:,.2f})")
            print(f"   Leverage: {leverage}x")
            print(f"   Reason: {decision['entry_reason']}")
            
            # Additional validation checks before execution
            existing_on_symbol = [p for p in open_positions if p.get('symbol') == asset]
            if existing_on_symbol:
                print(f"   🏗️  PYRAMIDING: Adding to existing {len(existing_on_symbol)} position(s) on {asset}")
            else:
                print(f"   📊 NEW POSITION: First position on {asset}")
            
            if len(open_positions) >= MAX_OPEN_POSITIONS:
                print(f"   ⚠️ WARNING: At max total positions ({len(open_positions)}/{MAX_OPEN_POSITIONS})")
            else:
                print(f"   ✅ Total position limit OK: {len(open_positions)}/{MAX_OPEN_POSITIONS}")
            
            if len(existing_on_symbol) + 1 > MAX_POSITIONS_PER_SYMBOL:
                print(f"   ⚠️ WARNING: Will exceed per-symbol limit (will be {len(existing_on_symbol) + 1}/{MAX_POSITIONS_PER_SYMBOL})")
            else:
                print(f"   ✅ Per-symbol limit OK: {len(existing_on_symbol)} → {len(existing_on_symbol) + 1}/{MAX_POSITIONS_PER_SYMBOL}")
            
            print(f"   ✅ Proceeding with execution...")
            
            # In high volatility, tighten SL/TP as per config
            if market_data.get('is_high_volatility'):
                from config import SCALP_STOP_LOSS, SCALP_TAKE_PROFIT
                decision['stop_loss_percent'] = SCALP_STOP_LOSS * 100 if SCALP_STOP_LOSS < 1 else SCALP_STOP_LOSS
                decision['take_profit_percent'] = SCALP_TAKE_PROFIT * 100 if SCALP_TAKE_PROFIT < 1 else SCALP_TAKE_PROFIT

            result = self.executor.execute_trade(
                asset, decision, position_size_dollars, leverage
            )
            
            # Log decision and trade
            self.logger.log_decision(decision, market_data, result)
            
            if result['status'] == 'SUCCESS':
                # Extract strategy and regime for performance tracking
                strategy = decision.get('strategy') or 'unknown'
                regime = market_data.get('regime', 'UNKNOWN')
                confidence = decision.get('confidence')
                self.logger.log_trade(result, strategy=strategy, regime=regime, confidence=confidence)
                self.risk_manager.total_trades_today += 1
                # Update portfolio after successful trade so next asset can trade with updated margin
                portfolio.update(self.executor.get_portfolio_status())
            else:
                print(f"   ❌ Trade execution failed: {result.get('message')}")
        
        elif decision['action'] == 'CLOSE' and existing_positions:
            print(f"\n📉 CLOSING position on {asset}")
            print(f"   Reason: {decision['entry_reason']}")
            
            result = self.executor.close_position(asset)
            self.logger.log_decision(decision, market_data, result)
            
            if result['status'] == 'SUCCESS':
                strategy = decision.get('strategy') or 'CLOSE'
                regime = market_data.get('regime', 'UNKNOWN')
                confidence = decision.get('confidence')
                self.logger.log_trade(result, strategy=strategy, regime=regime, confidence=confidence)
    
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

    def _force_initial_trade_once(self, portfolio, day_number):
        # Only execute once per process
        if getattr(self, "_forced_trade_done", False):
            return
        from config import (
            FORCE_INITIAL_TRADE, INITIAL_TRADE_SYMBOL, INITIAL_TRADE_SIDE,
            INITIAL_TRADE_SIZE_PCT, INITIAL_TRADE_LEVERAGE, MIN_CONFIDENCE
        )
        if not FORCE_INITIAL_TRADE:
            return
        try:
            asset = INITIAL_TRADE_SYMBOL
            decision = {
                'action': INITIAL_TRADE_SIDE,
                'confidence': max(MIN_CONFIDENCE, 90),
                'position_size_percent': INITIAL_TRADE_SIZE_PCT,
                'leverage': INITIAL_TRADE_LEVERAGE,
                'entry_reason': 'Forced initial trade (bootstrap)',
                'stop_loss_percent': 4,
                'take_profit_percent': 15,
                'urgency': 'HIGH'
            }
            size_decimal = INITIAL_TRADE_SIZE_PCT / 100

            is_valid, msg = self.risk_manager.validate_trade(
                decision=decision,
                portfolio=portfolio,
                position_size=size_decimal,
                leverage=INITIAL_TRADE_LEVERAGE,
                symbol=asset
            )
            if not is_valid:
                print(f"⚠️ Forced trade blocked by validation: {msg}")
                self._forced_trade_done = True
                return

            position_size_dollars = portfolio['total_value'] * size_decimal
            print(f"\n⚡ FORCED TRADE: {decision['action']} {asset} | size={size_decimal:.1%} ($" \
                  f"{position_size_dollars:,.2f}) lev={INITIAL_TRADE_LEVERAGE}x")
            result = self.executor.execute_trade(
                asset, decision, position_size_dollars, INITIAL_TRADE_LEVERAGE
            )

            self.logger.log_decision(decision, {'symbol': asset, 'price': None, 'regime': 'UNKNOWN'}, result)
            if result.get('status') == 'SUCCESS':
                self.logger.log_trade(result)
                self.risk_manager.total_trades_today += 1
                updated = self.executor.get_portfolio_status()
                portfolio.update(updated)
            else:
                print(f"   ❌ Forced trade failed: {result.get('message')}")
            self._forced_trade_done = True
        except Exception as e:
            print(f"❌ Forced trade error: {e}")
            self._forced_trade_done = True
    
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