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
from time_filters import get_trading_period, get_entry_hour_utc, format_trading_period_summary


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
                # No auto-restart or auto-continue on unexpected errors
                self.shutdown()
                break
    
    def _trading_cycle(self):
        """Execute one complete trading cycle"""
        current_day = self._get_competition_day()
        
        # Get trading period (time-based filters)
        trading_period = get_trading_period()
        
        # Log cycle start
        if self.cycle_count % 12 == 0:  # Every hour (12 * 5min)
            period_summary = format_trading_period_summary(trading_period)
            print(f"\n⏰ [{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] Day {current_day}/14 | Cycle #{self.cycle_count}")
            print(f"   {period_summary}")
        
        # Get portfolio status first
        portfolio = self.executor.get_portfolio_status()
        
        # Update risk manager with current portfolio value
        self.risk_manager.update_portfolio_metrics(portfolio['total_value'])
        
        # Log performance snapshot
        self.logger.log_performance_snapshot(portfolio)
        
        # Update strategy cooldowns (check every hour)
        if self.cycle_count % 12 == 0:
            strategies = ['TREND_FOLLOWING', 'BREAKOUT', 'MOMENTUM', 'REVERSAL', 'VOLATILITY_BREAKOUT', 'EMA_CROSSOVER']
            for strategy in strategies:
                self.analyzer.perf_tracker.update_strategy_cooldown(strategy)
        
        # Log strategy dashboard periodically (every 6 hours)
        if self.cycle_count % 72 == 0:
            dashboard = self.analyzer.perf_tracker.get_strategy_dashboard_data()
            print(f"\n📊 Strategy Performance Dashboard:")
            for strategy, stats in dashboard['strategies'].items():
                status = "⏸️ COOLDOWN" if stats['is_cooldown'] else f"📈 +{stats['boost']}" if stats['boost'] > 0 else f"📉 {stats['boost']}" if stats['boost'] < 0 else "➖"
                print(f"   {status} {strategy}: WR={stats['win_rate']:.1%} | PnL={stats['avg_pnl_pct']:.2f}% | PF={stats['profit_factor']:.2f} | Trades={stats['trade_count']}")

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
        
        # Update trailing stops with dynamic ATR-based system
        self._update_all_trailing_stops(portfolio)
        
        # Check TP hits and convert TP3 to trailing stop when TP2 hits
        self.executor.check_tp_hits_and_convert_tp3()
        
        self.executor.close_stale_positions()
        
        # Analyze each asset
        print(f"\n{'='*70}")
        print(f"🔄 TRADING CYCLE - Processing {len(TRADING_ASSETS)} symbol(s): {', '.join(TRADING_ASSETS)}")
        print(f"{'='*70}")
        
        for asset in TRADING_ASSETS:
            try:
                print(f"\n{'─'*70}")
                print(f"📊 Processing {asset} | Cycle #{self.cycle_count}")
                print(f"{'─'*70}")
                
                # Refresh portfolio before each asset to consider any prior trades
                portfolio = self.executor.get_portfolio_status()
                self._analyze_and_trade(asset, portfolio, current_day, trading_period)
            except Exception as e:
                print(f"❌ Error processing {asset}: {e}")
                import traceback
                traceback.print_exc()
                self.health_monitor.handle_error(e, {'asset': asset, 'action': 'analyze_and_trade'})
        
        # Print status summary periodically
        if self.cycle_count % 12 == 0:
            self._print_status(portfolio)
    
    def _analyze_and_trade(self, asset: str, portfolio: Dict, day_number: int, trading_period: Dict = None):
        """ENHANCED: Analyze asset and execute trade with improved signals"""
        
        # Apply time-based filters for new entries
        if trading_period and not trading_period.get('should_trade', True):
            print(f"   ⏸️  Skipping new trades for {asset}: {trading_period.get('reason', 'Low liquidity period')}")
            # Still monitor existing positions
            existing_positions = [p for p in portfolio.get('positions', []) if p.get('symbol') == asset]
            if existing_positions:
                print(f"   📊 Continuing to monitor {len(existing_positions)} existing position(s)")
                # Check exit signals and quick profit lock for existing positions
                market_data = self.data_pipeline.fetch_realtime_data(asset)
                if market_data and 'error' not in market_data:
                    for pos in existing_positions:
                        self._check_quick_profit_lock(pos, market_data.get('price', 0))
            return
        
        print(f"🔍 Step 1/6: Fetching market data for {asset}...")
        # Fetch market data
        market_data = self.data_pipeline.fetch_realtime_data(asset)
        
        # Validate data
        print(f"🔍 Step 2/6: Validating data integrity for {asset}...")
        if not self.health_monitor.validate_data_integrity(market_data):
            print(f"   ❌ {asset} REJECTED: Invalid data for {asset}, skipping...")
            if 'error' in market_data:
                print(f"      Error details: {market_data.get('error')}")
            return
        else:
            print(f"   ✅ {asset} data validated successfully")
        
        # Get market regime and indicators
        regime = market_data.get('regime', 'UNKNOWN')
        indicators = market_data.get('indicators', {})
        price = market_data.get('price', 0)
        
        print(f"   📊 {asset} Market Data:")
        print(f"      Price: ${price:,.2f}")
        print(f"      Regime: {regime}")
        print(f"      RSI: {indicators.get('rsi', 0):.1f}" if indicators.get('rsi') else "      RSI: N/A")
        print(f"      Volume Ratio: {indicators.get('volume_ratio', 1.0):.2f}x" if indicators.get('volume_ratio') else "      Volume Ratio: N/A")
        
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
        # QUICK PROFIT LOCK (for low confidence positions)
        # ========================================
        for pos in existing_positions:
            self._check_quick_profit_lock(pos, market_data.get('price', 0))
        
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
            
            # Check graduated exit signals from market analyzer (on worst position)
            exit_signal = self.analyzer.should_exit_position(
                worst_position, market_data, indicators
            )
            
            exit_action = exit_signal.get('exit_action', 'NONE')
            exit_confidence = exit_signal.get('exit_confidence', 0)
            
            if exit_action != 'NONE' and exit_confidence >= 75:
                print(f"\n📉 TIERED EXIT SIGNAL for {asset}")
                print(f"   🎯 Exit tier activated: {exit_action} at {exit_confidence}% confidence")
                print(f"   Current PnL: {pnl:+.2f}%")
                print(f"   Reasons: {' | '.join(exit_signal.get('reasons', []))}")
                
                result = self.executor.execute_tiered_exit(worst_position, exit_signal)
                
                # Create decision object for logging
                exit_decision = {
                    'action': 'CLOSE' if exit_action == 'FULL' else 'PARTIAL_CLOSE',
                    'confidence': exit_confidence,
                    'entry_reason': ' | '.join(exit_signal.get('reasons', [])),
                    'exit_tier': exit_action
                }
                self.logger.log_decision(exit_decision, market_data, result)
                
                if result.get('status') == 'SUCCESS' or result.get('status') == 'NONE':
                    strategy = f'EXIT_{exit_action}'
                    regime = market_data.get('regime', 'UNKNOWN')
                    if exit_action == 'FULL':
                        self.logger.log_trade(result, strategy=strategy, regime=regime, confidence=exit_confidence)
                    # Continue to allow pyramiding if under limit after close
                    if exit_action == 'FULL' and positions_on_symbol - 1 >= MAX_POSITIONS_PER_SYMBOL:
                        return  # Can't pyramid if still at limit after closing
        
        # ========================================
        # ENHANCED ENTRY LOGIC (PYRAMIDING ALLOWED)
        # ========================================
        
        # Check if we can add more positions (pyramiding check)
        if positions_on_symbol >= MAX_POSITIONS_PER_SYMBOL:
            print(f"   ⚠️ Already at max positions ({positions_on_symbol}/{MAX_POSITIONS_PER_SYMBOL}) for {asset}")
            print(f"   💡 Will skip pyramiding - waiting for exit signals or position closure")
            return
        
        # Get LLM decision (LLM will evaluate if pyramiding is profitable)
        print(f"🔍 Step 3/6: Getting LLM decision for {asset}...")
        try:
            decision = self.deepseek_agent.get_decision(market_data, portfolio, day_number)
            print(f"   ✅ {asset} LLM Decision received: action={decision.get('action')}, confidence={decision.get('confidence', 0):.1f}%")
        except Exception as e:
            print(f"   ⚠️ {asset} DeepSeek API error, using fallback...")
            print(f"      Error: {e}")
            self.health_monitor.handle_api_failure('deepseek', e)
            decision = self.deepseek_agent.get_fallback_decision(market_data, portfolio)
            print(f"   ✅ {asset} Fallback Decision: action={decision.get('action')}, confidence={decision.get('confidence', 0):.1f}%")
        
        # Skip if HOLD or low confidence (lower threshold in volatile markets)
        print(f"🔍 Step 4/6: Checking decision threshold for {asset}...")
        from config import MIN_CONFIDENCE_VOLATILE
        min_conf = MIN_CONFIDENCE_VOLATILE if market_data.get('regime') == 'VOLATILE' else MIN_CONFIDENCE
        
        if decision['action'] == 'HOLD':
            print(f"   ⚠️ {asset} SKIPPED: LLM returned HOLD (no trade signal)")
            print(f"      Decision details: confidence={decision.get('confidence', 0):.1f}%, reason='{decision.get('entry_reason', 'N/A')}'")
            return
        elif decision['confidence'] < min_conf:
            print(f"   ⚠️ {asset} SKIPPED: Confidence too low")
            print(f"      Confidence: {decision.get('confidence', 0):.1f}% < threshold: {min_conf}%")
            print(f"      Regime: {regime} (threshold: {min_conf}% for this regime)")
            return
        else:
            print(f"   ✅ {asset} Decision passed: action={decision.get('action')}, confidence={decision.get('confidence', 0):.1f}% >= {min_conf}%")
        
        # Pyramiding validation
        is_pyramid = positions_on_symbol > 0
        first_position = existing_positions[0] if existing_positions else None
        
        if is_pyramid:
            # Enhanced pyramid rules
            first_pnl = first_position.get('pnl_percent', 0)
            first_side = first_position.get('side')
            decision_side = decision.get('action')
            
            # Only pyramid if first position is profitable
            if first_pnl <= 0:
                print(f"   ❌ PYRAMID REJECTED: First position losing ({first_pnl:.2f}%) - pyramid blocked")
                return
            
            # Require confidence >= 70 for pyramid
            if decision['confidence'] < 70:
                print(f"   ❌ PYRAMID REJECTED: Confidence {decision['confidence']:.1f}% < 70% threshold for pyramiding")
                return
            
            # Ensure same direction
            if first_side != decision_side:
                print(f"   ❌ PYRAMID REJECTED: Direction mismatch (first: {first_side}, new: {decision_side})")
                return
            
            print(f"   🏗️  PYRAMID OPPORTUNITY: First position +{first_pnl:.2f}%")
        
        # Calculate position size and leverage (strategy and confidence-based)
        print(f"🔍 Step 5/6: Calculating position size for {asset}...")
        portfolio_value = portfolio.get('total_value', INITIAL_CAPITAL)
        
        # Extract strategy type from decision or market analyzer setups
        strategy_type = decision.get('strategy') or decision.get('strategy_type')
        
        # If not in decision, try to extract from market analyzer setups
        if not strategy_type:
            try:
                setups = self.analyzer.find_trade_setups(market_data)
                if setups:
                    # Get the best setup (highest confidence)
                    best_setup = max(setups, key=lambda s: s.get('confidence', 0))
                    strategy_type = best_setup.get('strategy')
            except Exception:
                pass
        
        # Normalize strategy type to match STRATEGY_LEVERAGE keys
        if strategy_type:
            # Map common variations to standard names
            strategy_mapping = {
                'trend_following': 'TREND_FOLLOWING',
                'TREND_FOLLOWING_ENHANCED': 'TREND_FOLLOWING',
                'momentum': 'MOMENTUM',
                'MOMENTUM_ENHANCED': 'MOMENTUM',
                'breakout': 'BREAKOUT',
                'BREAKOUT_ENHANCED': 'BREAKOUT',
                'mean_reversion': 'REVERSAL',
                'MEAN_REVERSION': 'REVERSAL',
                'reversal': 'REVERSAL',
                'volatility_breakout': 'VOLATILITY_BREAKOUT',
                'VOLATILITY_BREAKOUT': 'VOLATILITY_BREAKOUT',
                'ema_crossover': 'EMA_CROSSOVER',
                'EMA_CROSSOVER': 'EMA_CROSSOVER'
            }
            strategy_type = strategy_mapping.get(strategy_type, strategy_type.upper())
        
        # Apply time-based size multiplier
        size_multiplier = trading_period.get('size_multiplier', 1.0) if trading_period else 1.0
        
        # Calculate base position size
        base_position_info = self.risk_manager.calculate_position_size(
            balance=portfolio_value,
            confidence=decision['confidence'],
            market_data=market_data,
            strategy_type=strategy_type,
            size_multiplier=size_multiplier
        )
        
        base_size_dollars = base_position_info['size']
        
        # If pyramiding, calculate adjusted pyramid size
        if is_pyramid and first_position:
            pyramid_info = self.risk_manager.calculate_pyramid_size(
                first_position, base_size_dollars, decision['confidence'], portfolio_value
            )
            position_size_dollars = pyramid_info['pyramid_size']
            pyramid_multiplier = pyramid_info['multiplier']
            
            if position_size_dollars <= 0:
                print(f"   ❌ PYRAMID REJECTED: Calculated pyramid size is ${position_size_dollars:,.2f}")
                return
            
            print(f"   🏗️  PYRAMID SIZE: ${position_size_dollars:,.2f} ({pyramid_multiplier:.2f}x base, reason: {pyramid_info['reason']})")
        else:
            position_size_dollars = base_size_dollars
            pyramid_multiplier = 1.0
        
        # Calculate position size percentage
        position_size = position_size_dollars / portfolio_value if portfolio_value > 0 else 0
        leverage = base_position_info['leverage']
        
        multiplier_text = f" (x{size_multiplier:.2f} time boost)" if size_multiplier > 1.0 else ""
        
        print(f"   💰 {asset} Position Sizing:")
        print(f"      Portfolio Value: ${portfolio_value:,.2f}")
        print(f"      Position Size: ${position_size_dollars:,.2f} ({position_size:.1%}){multiplier_text}")
        print(f"      Leverage: {leverage}x")
        
        # Skip if position size too small
        if position_size == 0:
            print(f"   ❌ {asset} REJECTED: Position size calculated as 0 (insufficient balance or calculation error)")
            return
        else:
            print(f"   ✅ {asset} Position size validated")
        
        # Detailed logging before validation
        print(f"🔍 Step 6/6: Final validation for {asset}...")
        open_positions = portfolio.get('positions', [])
        available_balance = portfolio.get('available_balance', 0)
        positions_on_this_symbol = len([p for p in open_positions if p.get('symbol') == asset])
        
        print(f"\n   📋 {asset} Trade Validation:")
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
    
    def _update_all_trailing_stops(self, portfolio: Dict):
        """
        Update dynamic trailing stops for all open positions
        Fetches fresh market data for each position and updates trailing stops
        """
        try:
            positions = portfolio.get('positions', [])
            if not positions:
                return
            
            trailing_active = []
            
            for pos in positions:
                symbol = pos['symbol']
                
                # Fetch fresh market data for this symbol (needed for ATR)
                try:
                    market_data = self.data_pipeline.fetch_realtime_data(symbol)
                    
                    # Validate market data
                    if not market_data or 'error' in market_data or not market_data.get('indicators'):
                        continue
                    
                    # Update trailing stop for this position
                    updated = self.executor.update_dynamic_trailing_stop(pos, market_data)
                    
                    if updated:
                        trailing_active.append(symbol)
                    
                except Exception as e:
                    print(f"   ⚠️ Error updating trailing stop for {symbol}: {e}")
                    continue
            
            # Log trailing status
            if trailing_active:
                print(f"\n   📊 Trailing stops active: {', '.join(trailing_active)}")
                
        except Exception as e:
            print(f"Error in _update_all_trailing_stops: {e}")
    
    def _check_quick_profit_lock(self, position: Dict, current_price: float) -> bool:
        """
        Check and execute quick profit lock for low confidence positions
        Parameters:
            position: Position object with entry_price, quantity, etc.
            current_price: Current market price
        Returns:
            bool: True if action taken
        """
        try:
            symbol = position.get('symbol')
            if not symbol:
                return False
            
            # Check if already locked
            if symbol in self.executor.open_positions:
                if self.executor.open_positions[symbol].get('profit_locked', False):
                    return False
            
            # Only apply to positions with confidence < 75%
            # Try to get confidence from position or executor tracking
            confidence = position.get('confidence', 100)
            if symbol in self.executor.open_positions:
                tracked_pos = self.executor.open_positions[symbol]
                if 'confidence' in tracked_pos:
                    confidence = tracked_pos['confidence']
            if confidence >= 75:
                return False
            
            # Check unrealized PnL
            pnl_percent = position.get('pnl_percent', 0)
            if pnl_percent < 4.0:
                return False
            
            # Execute quick profit lock
            print(f"\n🔒 Quick profit lock triggered for {symbol} at {pnl_percent:.2f}% profit")
            print(f"   Original confidence: {confidence}%")
            
            # Close 50% of position
            partial_result = self.executor.close_partial_position(symbol, 0.5)
            
            if partial_result.get('status') != 'SUCCESS':
                print(f"   ❌ Failed to close partial position: {partial_result.get('message')}")
                return False
            
            close_price = partial_result.get('close_price', 0)
            remaining_qty = partial_result.get('remaining_quantity', 0)
            print(f"   ✅ Closed 50% at price ${close_price:,.2f}, remaining quantity: {remaining_qty}")
            
            # Update stop loss to entry price (breakeven)
            entry_price = position.get('entry_price', 0)
            side = position.get('side', 'LONG')
            price_precision = 2
            
            try:
                exchange_info = self.executor.client.futures_exchange_info()
                symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
                if symbol_info:
                    price_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'), None)
                    if price_filter:
                        tick_size = float(price_filter['tickSize'])
                        price_precision = max(0, len(str(tick_size).rstrip('0').split('.')[-1]))
            except Exception:
                pass
            
            sl_result = self.executor.set_stop_loss(
                symbol, side, entry_price, remaining_qty, 0, price_precision, move_to_breakeven=True
            )
            
            if sl_result:
                print(f"   ✅ Stop loss moved to breakeven: ${entry_price:,.2f}")
            else:
                print(f"   ⚠️ Failed to update stop loss to breakeven (partial close still executed)")
            
            # Set profit_locked flag
            if symbol in self.executor.open_positions:
                self.executor.open_positions[symbol]['profit_locked'] = True
            
            return True
            
        except Exception as e:
            print(f"Error in quick profit lock check for {symbol}: {e}")
            return False

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