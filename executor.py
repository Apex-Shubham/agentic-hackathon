"""
Order Execution Engine
Handles trade execution, position management, stop-loss and take-profit orders
"""
from typing import Dict, List, Optional
import math
import time
from datetime import datetime, timezone
from binance.client import Client
from binance.exceptions import BinanceAPIException
from config import (
    BINANCE_API_KEY, BINANCE_API_SECRET, TRAILING_STOP_ACTIVATION,
    SCALED_TP_LEVELS, INITIAL_CAPITAL, STALE_POSITION_MINUTES, STALE_PNL_BAND
)
from time_filters import get_entry_hour_utc


class Executor:
    """Executes trades and manages positions on Binance Futures"""
    
    def __init__(self):
        self.client = Client(
            api_key=BINANCE_API_KEY,
            api_secret=BINANCE_API_SECRET,
            testnet=True
        )
        self.open_positions = {}
        self.position_entry_prices = {}
        self.stop_loss_orders = {}
        self.take_profit_orders = {}
        self.trailing_stops = {}
    
    def execute_trade(
        self,
        symbol: str,
        decision: Dict,
        position_size_dollars: float,
        leverage: int
    ) -> Dict:
        """
        Execute a trade based on decision
        Returns: Execution result with order details
        """
        try:
            action = decision['action']
            
            if action == 'HOLD':
                return {'status': 'HOLD', 'message': 'No action taken'}
            
            elif action == 'CLOSE':
                return self.close_position(symbol)
            
            elif action in ['LONG', 'SHORT']:
                return self._open_position(
                    symbol, action, position_size_dollars, leverage, decision
                )
            
            else:
                return {'status': 'ERROR', 'message': f'Unknown action: {action}'}
                
        except Exception as e:
            print(f"Error executing trade for {symbol}: {e}")
            return {'status': 'ERROR', 'message': str(e)}
    
    def _open_position(
        self,
        symbol: str,
        side: str,
        position_size_dollars: float,
        leverage: int,
        decision: Dict
    ) -> Dict:
        """Open a new position"""
        try:
            # Set leverage
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            
            # Get current price
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price'])
            
            # Get symbol info for precision
            exchange_info = self.client.futures_exchange_info()
            symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
            
            if not symbol_info:
                return {'status': 'ERROR', 'message': f'Symbol {symbol} not found'}
            
            # Get quantity and price precision, step/tick, min notional
            quantity_precision = 0
            price_precision = 2
            tick_size = 0.01
            step_size = 0.001
            min_notional = None
            for f in symbol_info['filters']:
                if f['filterType'] == 'LOT_SIZE':
                    step_size = float(f['stepSize'])
                    quantity_precision = len(str(step_size).rstrip('0').split('.')[-1])
                if f['filterType'] == 'PRICE_FILTER':
                    tick_size = float(f['tickSize'])
                    # derive price precision from tick size
                    if tick_size > 0:
                        price_precision = max(0, len(str(tick_size).rstrip('0').split('.')[-1]))
                if f['filterType'] in ('MIN_NOTIONAL', 'NOTIONAL'):
                    # Different API variants
                    mn = f.get('notional') or f.get('minNotional')
                    if mn is not None:
                        try:
                            min_notional = float(mn)
                        except Exception:
                            pass
            
            # Calculate quantity
            quantity = position_size_dollars / current_price
            # snap to step size (avoid floating artifacts)
            if step_size > 0:
                increments = max(1, int(quantity / step_size))
                quantity = round(increments * step_size, quantity_precision)
            else:
                quantity = round(quantity, quantity_precision)

            # Ensure min notional requirement
            notional = quantity * current_price
            if min_notional and notional < min_notional:
                needed_qty = (min_notional / current_price)
                if step_size > 0:
                    increments = int(needed_qty / step_size + 0.9999)
                    quantity = round(increments * step_size, quantity_precision)
                else:
                    quantity = round(needed_qty, quantity_precision)
            
            # Determine order side
            order_side = 'BUY' if side == 'LONG' else 'SELL'
            
            # Place market order
            order = self.client.futures_create_order(
                symbol=symbol,
                side=order_side,
                type='MARKET',
                quantity=quantity
            )
            
            # Determine fill price robustly
            fill_price = float(order.get('avgPrice') or 0.0)
            if fill_price <= 0:
                # Try position info (most reliable for entry)
                try:
                    time.sleep(0.5)
                    pos_info = self.client.futures_position_information(symbol=symbol)
                    for pos in pos_info:
                        amt = float(pos.get('positionAmt', 0))
                        if abs(amt) > 0:
                            fill_price = float(pos.get('entryPrice', 0)) or fill_price
                            break
                except Exception:
                    pass
            if fill_price <= 0:
                # Fallback to mark price
                try:
                    mark = self.client.futures_mark_price(symbol=symbol)
                    fill_price = float(mark.get('markPrice', current_price))
                except Exception:
                    fill_price = current_price

            # Final attempt: recent user trades price
            if fill_price <= 0:
                try:
                    trades = self.client.futures_account_trades(symbol=symbol, limit=5)
                    if trades:
                        fill_price = float(trades[-1].get('price', current_price))
                except Exception:
                    pass
            
            print(f"✅ Opened {side} position: {symbol} @ ${fill_price:,.2f} | Qty: {quantity} | Leverage: {leverage}x")
            
            # Determine if this is a pyramid position
            is_pyramid = decision.get('is_pyramid', False)
            pyramid_of_position_id = decision.get('pyramid_of_position_id')
            pyramid_multiplier = decision.get('pyramid_multiplier', 1.0)
            pyramid_stop_price = decision.get('pyramid_stop_price')
            
            # Store position info with TP tracking flags and trailing stop metadata
            self.open_positions[symbol] = {
                'symbol': symbol,
                'side': side,
                'entry_price': fill_price,
                'quantity': quantity,
                'leverage': leverage,
                'entry_time': datetime.now(timezone.utc).isoformat(),
                'entry_hour_utc': get_entry_hour_utc(),  # Track entry hour for analytics
                'order_id': order['orderId'],
                'confidence': decision.get('confidence', 75),  # Store confidence for quick profit lock
                'is_pyramid': is_pyramid,  # Pyramid position flag
                'pyramid_of_position_id': pyramid_of_position_id,  # Link to first position
                'pyramid_multiplier': pyramid_multiplier,  # Size multiplier used
                'tp2_hit': False,  # Flag to track if TP2 has been hit (for TP3 trailing stop)
                'tp_order_ids': [],  # Will be populated below
                'is_trailing': False,  # Trailing stop activation flag
                'trail_started_at': None,  # Timestamp when trailing started
                'highest_price_reached': fill_price,  # Track peak price for LONG, lowest for SHORT
                'trail_type': None,  # 'tight', 'wide', or 'aggressive'
                'current_stop_loss_price': None,  # Current stop loss price
                'aggressive_trailing': False,  # Flag for TP3 aggressive trailing
                'profit_locked': False,  # Quick profit lock flag
                'partial_close_price': None,  # Price at which partial close occurred
                'original_quantity': quantity,  # Original position quantity
                'remaining_quantity': quantity,  # Remaining position quantity
                'partial_exits': []  # Track partial exit history
            }
            
            # If pyramid, use special stop loss at first position's current price
            if is_pyramid and pyramid_stop_price:
                print(f"   🏗️  PYRAMID STOP: Setting stop at first position entry: ${pyramid_stop_price:,.2f}")
                self.set_stop_loss(
                    symbol, side, pyramid_stop_price, quantity, 0, price_precision, move_to_breakeven=False
                )
            else:
                # Normal stop loss
                sl_order_id = self.set_stop_loss(
                    symbol, side, fill_price, quantity, decision['stop_loss_percent'], price_precision
                )
            
            # Set scaled take profit levels (3 tiers)
            tp_order_ids = self.set_take_profit(
                symbol, side, fill_price, quantity, decision['take_profit_percent'], price_precision
            )
            
            # Update position with TP order IDs
            if symbol in self.open_positions:
                self.open_positions[symbol]['tp_order_ids'] = tp_order_ids
            
            # Log total orders created for this position
            total_orders = 1  # Entry order
            if sl_order_id:
                total_orders += 1
            total_orders += len(tp_order_ids)
            print(f"   📋 Total orders created for {symbol}: {total_orders} (1 entry + {1 if sl_order_id else 0} stop-loss + {len(tp_order_ids)} take-profit)")

            # Verify order status for diagnostics
            order_status = None
            try:
                order_status = self.client.futures_get_order(symbol=symbol, orderId=order['orderId'])
            except Exception:
                pass
            
            return {
                'status': 'SUCCESS',
                'symbol': symbol,
                'side': side,
                'entry_price': fill_price,
                'quantity': quantity,
                'leverage': leverage,
                'order_id': order['orderId'],
                'stop_loss_order': sl_order_id,
                'take_profit_orders': tp_order_ids,
                'tp_count': len(tp_order_ids),
                'binance_order_status': order_status
            }
            
        except BinanceAPIException as e:
            print(f"Binance API error opening position: {e}")
            return {'status': 'ERROR', 'message': str(e)}
        except Exception as e:
            print(f"Error opening position: {e}")
            return {'status': 'ERROR', 'message': str(e)}
    
    def set_stop_loss(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        stop_loss_percent: float,
        price_precision: int,
        move_to_breakeven: bool = False
    ) -> Optional[str]:
        """Set stop loss order"""
        try:
            # Cancel existing stop loss if present
            existing_sl = self.stop_loss_orders.get(symbol)
            if existing_sl:
                try:
                    self.client.futures_cancel_order(symbol=symbol, orderId=existing_sl)
                except Exception:
                    pass
            
            # Calculate stop price
            if move_to_breakeven:
                # Move stop to entry price (breakeven)
                if side == 'LONG':
                    stop_price = entry_price * 1.001  # Slightly above entry
                    order_side = 'SELL'
                else:  # SHORT
                    stop_price = entry_price * 0.999  # Slightly below entry
                    order_side = 'BUY'
            else:
                if side == 'LONG':
                    stop_price = entry_price * (1 - stop_loss_percent / 100)
                    order_side = 'SELL'
                else:  # SHORT
                    stop_price = entry_price * (1 + stop_loss_percent / 100)
                    order_side = 'BUY'
            
            # Guard against invalid prices
            if stop_price <= 0:
                raise ValueError("Computed stop price <= 0")
            
            # Round to appropriate precision
            stop_price = round(stop_price, price_precision)
            
            # Place stop loss order
            order = self.client.futures_create_order(
                symbol=symbol,
                side=order_side,
                type='STOP_MARKET',
                stopPrice=stop_price,
                quantity=quantity,
                timeInForce='GTC'
            )
            
            order_id = str(order['orderId'])
            self.stop_loss_orders[symbol] = order_id
            
            # Store initial stop loss price in position tracking
            if symbol in self.open_positions:
                self.open_positions[symbol]['current_stop_loss_price'] = stop_price
            
            if move_to_breakeven:
                print(f"   🛡️ Stop Loss moved to breakeven @ ${stop_price:,.2f}")
            else:
                print(f"   🛡️ Stop Loss set @ ${stop_price:,.2f} ({stop_loss_percent}%)")
            
            return order_id
            
        except Exception as e:
            print(f"Error setting stop loss for {symbol}: {e}")
            return None
    
    def set_take_profit(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        take_profit_percent: float,
        price_precision: int
    ) -> List[str]:
        """
        Set scaled take profit orders with 3 tiers:
        - TP1: 30% of position at 6% profit
        - TP2: 40% of position at 12% profit  
        - TP3: 30% of position at 20% profit
        """
        order_ids = []
        
        try:
            # Fetch symbol filters for proper rounding
            exchange_info = self.client.futures_exchange_info()
            symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
            if not symbol_info:
                raise ValueError(f"Symbol info not found for {symbol}")
            
            # LOT_SIZE filter
            lot_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
            step_size = float(lot_filter['stepSize'])
            min_qty = float(lot_filter['minQty'])
            
            # PRICE precision
            price_precision_local = int(symbol_info.get('pricePrecision', price_precision))
            
            # Define 3-tier TP structure
            tp_configs = [
                {'percent': 30, 'profit_target': 6.0},   # TP1: 30% at 6%
                {'percent': 40, 'profit_target': 12.0},  # TP2: 40% at 12%
                {'percent': 30, 'profit_target': 20.0}   # TP3: 30% at 20%
            ]
            
            # Calculate TP quantities and prices
            tp_levels = []
            for i, config in enumerate(tp_configs):
                # Calculate quantity for this TP level
                tp_quantity = quantity * (config['percent'] / 100.0)
                
                # Round down to nearest step size
                if step_size > 0:
                    tp_quantity = math.floor(tp_quantity / step_size) * step_size
                else:
                    tp_quantity = round(tp_quantity, price_precision)
                
                # Skip if below minimum quantity
                if tp_quantity < min_qty or tp_quantity <= 0:
                    print(f"   ⚠️ TP{i+1} skipped: quantity {tp_quantity} below minimum {min_qty}")
                    continue
                
                # Calculate TP price based on direction
                profit_target = config['profit_target']
                if side == 'LONG':
                    tp_price = entry_price * (1 + profit_target / 100)
                    order_side = 'SELL'
                else:  # SHORT
                    tp_price = entry_price * (1 - profit_target / 100)
                    order_side = 'BUY'
                
                # Validate price
                if tp_price <= 0:
                    print(f"   ⚠️ TP{i+1} skipped: invalid price {tp_price}")
                    continue
                
                # Round price to precision
                tp_price = round(tp_price, price_precision_local)
                
                tp_levels.append({
                    'level': i + 1,
                    'quantity': tp_quantity,
                    'price': tp_price,
                    'profit_target': profit_target,
                    'percent_of_position': config['percent'],
                    'order_side': order_side
                })
            
            # Place TP orders
            for tp_level in tp_levels:
                try:
                    order = self.client.futures_create_order(
                        symbol=symbol,
                        side=tp_level['order_side'],
                        type='TAKE_PROFIT_MARKET',
                        stopPrice=tp_level['price'],
                        quantity=tp_level['quantity'],
                        timeInForce='GTC'
                    )
                    
                    order_id = str(order['orderId'])
                    order_ids.append(order_id)
                    
                    print(f"   🎯 TP{tp_level['level']}: {tp_level['percent_of_position']}% @ ${tp_level['price']:,.2f} ({tp_level['profit_target']:.1f}% profit) | qty={tp_level['quantity']}")
                    
                except BinanceAPIException as e:
                    print(f"   ⚠️ Failed to place TP{tp_level['level']} for {symbol}: {e}")
                    # Continue with other TPs even if one fails
                    continue
                except Exception as e:
                    print(f"   ⚠️ Error placing TP{tp_level['level']} for {symbol}: {e}")
                    continue
            
            # Verify at least one TP was placed
            if not order_ids:
                print(f"   ❌ WARNING: No take profit orders placed for {symbol}")
                return []
            
            # Store TP order IDs
            self.take_profit_orders[symbol] = order_ids
            
            print(f"   ✅ Placed {len(order_ids)}/3 take profit orders for {symbol}")
            
            return order_ids
            
        except Exception as e:
            print(f"Error setting take profit for {symbol}: {e}")
            return []
    
    def close_position(self, symbol: str) -> Dict:
        """Close an open position"""
        try:
            # Check if position exists
            if symbol not in self.open_positions:
                # Try to get from Binance directly
                positions = self.get_open_positions()
                symbol_pos = next((p for p in positions if p['symbol'] == symbol), None)
                if not symbol_pos:
                    return {'status': 'ERROR', 'message': f'No open position for {symbol}'}
            
            position = self.open_positions.get(symbol, {})
            side = position.get('side', 'UNKNOWN')
            quantity = position.get('quantity', 0)
            entry_price = position.get('entry_price', 0)
            
            # If we don't have quantity, fetch from Binance
            if quantity == 0:
                positions = self.client.futures_position_information(symbol=symbol)
                for pos in positions:
                    if float(pos['positionAmt']) != 0:
                        quantity = abs(float(pos['positionAmt']))
                        side = 'LONG' if float(pos['positionAmt']) > 0 else 'SHORT'
                        entry_price = float(pos['entryPrice'])
                        break
            
            if quantity == 0:
                return {'status': 'ERROR', 'message': 'No position to close'}
            
            # Close position (opposite side)
            order_side = 'SELL' if side == 'LONG' else 'BUY'
            
            order = self.client.futures_create_order(
                symbol=symbol,
                side=order_side,
                type='MARKET',
                quantity=quantity
            )
            
            exit_price = float(order.get('avgPrice', 0))
            
            # Calculate PnL
            if side == 'LONG':
                pnl_percent = ((exit_price - entry_price) / entry_price) * 100
            else:  # SHORT
                pnl_percent = ((entry_price - exit_price) / entry_price) * 100
            
            leverage = position.get('leverage', 1)
            pnl_percent *= leverage  # Account for leverage
            
            print(f"✅ Closed {side} position: {symbol} @ ${exit_price:,.2f} | PnL: {pnl_percent:+.2f}%")
            
            # Cancel any open stop loss / take profit orders
            self._cancel_orders(symbol)
            
            # Remove from tracking
            if symbol in self.open_positions:
                del self.open_positions[symbol]
            
            return {
                'status': 'SUCCESS',
                'symbol': symbol,
                'side': side,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'quantity': quantity,
                'pnl_percent': pnl_percent,
                'order_id': order['orderId']
            }
            
        except Exception as e:
            print(f"Error closing position for {symbol}: {e}")
            return {'status': 'ERROR', 'message': str(e)}
    
    def execute_tiered_exit(self, position: Dict, exit_signal: Dict) -> Dict:
        """
        Execute tiered exit based on exit signal
        Parameters:
            position: Position dict with symbol, side, entry_price, etc.
            exit_signal: Dict from should_exit_position with exit_action, etc.
        Returns:
            Execution result dict
        """
        try:
            symbol = position.get('symbol')
            side = position.get('side')
            entry_price = position.get('entry_price', 0)
            current_price = position.get('current_price', 0)
            
            if symbol not in self.open_positions:
                return {'status': 'ERROR', 'message': f'Position {symbol} not found'}
            
            tracked_pos = self.open_positions[symbol]
            current_quantity = tracked_pos.get('remaining_quantity', tracked_pos.get('quantity', 0))
            
            if current_quantity <= 0:
                return {'status': 'ERROR', 'message': 'No remaining quantity to close'}
            
            exit_action = exit_signal.get('exit_action', 'NONE')
            
            if exit_action == 'NONE':
                return {'status': 'NONE', 'message': 'No exit action recommended'}
            
            elif exit_action == 'FULL':
                result = self.close_position(symbol)
                if result.get('status') == 'SUCCESS':
                    if 'partial_exits' not in tracked_pos:
                        tracked_pos['partial_exits'] = []
                    tracked_pos['partial_exits'].append({
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'percentage': 1.0,
                        'price': result.get('exit_price', 0),
                        'reason': ' | '.join(exit_signal.get('reasons', []))
                    })
                return result
            
            elif exit_action == 'PARTIAL_60':
                percentage = 0.6
                
                if tracked_pos.get('profit_locked', False):
                    percentage = min(0.6 * (1.0 / 0.5), 1.0 - 0.01)
                
                partial_result = self.close_partial_position(symbol, percentage)
                
                if partial_result.get('status') == 'SUCCESS':
                    close_price = partial_result.get('close_price', 0)
                    remaining_qty = partial_result.get('remaining_quantity', 0)
                    
                    if 'partial_exits' not in tracked_pos:
                        tracked_pos['partial_exits'] = []
                    tracked_pos['partial_exits'].append({
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'percentage': percentage,
                        'price': close_price,
                        'reason': ' | '.join(exit_signal.get('reasons', []))
                    })
                    
                    price_precision = 2
                    try:
                        exchange_info = self.client.futures_exchange_info()
                        symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
                        if symbol_info:
                            price_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'), None)
                            if price_filter:
                                tick_size = float(price_filter['tickSize'])
                                price_precision = max(0, len(str(tick_size).rstrip('0').split('.')[-1]))
                    except Exception:
                        pass
                    
                    self.set_stop_loss(symbol, side, entry_price, remaining_qty, 0, price_precision, move_to_breakeven=True)
                    
                    tp_orders = self.take_profit_orders.get(symbol, [])
                    for tp_id in tp_orders:
                        try:
                            self.client.futures_cancel_order(symbol=symbol, orderId=tp_id)
                        except Exception:
                            pass
                    
                    decision = {'take_profit_percent': 15.0}
                    self.set_take_profit(symbol, side, entry_price, remaining_qty, decision['take_profit_percent'], price_precision)
                    
                    print(f"   ✅ Exit tier PARTIAL_60: Closed {percentage:.0%} at ${close_price:,.2f}, stop moved to breakeven")
                
                return partial_result
            
            elif exit_action == 'PARTIAL_40':
                percentage = 0.4
                
                if tracked_pos.get('profit_locked', False):
                    percentage = min(0.4 * (1.0 / 0.5), 1.0 - 0.01)
                
                partial_result = self.close_partial_position(symbol, percentage)
                
                if partial_result.get('status') == 'SUCCESS':
                    close_price = partial_result.get('close_price', 0)
                    remaining_qty = partial_result.get('remaining_quantity', 0)
                    
                    if current_price == 0:
                        current_price = close_price
                    
                    if 'partial_exits' not in tracked_pos:
                        tracked_pos['partial_exits'] = []
                    tracked_pos['partial_exits'].append({
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'percentage': percentage,
                        'price': close_price,
                        'reason': ' | '.join(exit_signal.get('reasons', []))
                    })
                    
                    price_precision = 2
                    try:
                        exchange_info = self.client.futures_exchange_info()
                        symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
                        if symbol_info:
                            price_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'), None)
                            if price_filter:
                                tick_size = float(price_filter['tickSize'])
                                price_precision = max(0, len(str(tick_size).rstrip('0').split('.')[-1]))
                    except Exception:
                        pass
                    
                    if side == 'LONG':
                        new_stop = current_price * 0.99
                    else:
                        new_stop = current_price * 1.01
                    
                    self.set_stop_loss(symbol, side, entry_price, remaining_qty, 1.0, price_precision, move_to_breakeven=False)
                    
                    tp_orders = self.take_profit_orders.get(symbol, [])
                    for tp_id in tp_orders:
                        try:
                            self.client.futures_cancel_order(symbol=symbol, orderId=tp_id)
                        except Exception:
                            pass
                    
                    decision = {'take_profit_percent': 15.0}
                    self.set_take_profit(symbol, side, entry_price, remaining_qty, decision['take_profit_percent'], price_precision)
                    
                    print(f"   ✅ Exit tier PARTIAL_40: Closed {percentage:.0%} at ${close_price:,.2f}, stop tightened to ${new_stop:,.2f} (1% away)")
                
                return partial_result
            
            return {'status': 'ERROR', 'message': f'Unknown exit action: {exit_action}'}
            
        except Exception as e:
            print(f"Error executing tiered exit for {symbol}: {e}")
            return {'status': 'ERROR', 'message': str(e)}
    
    def _cancel_orders(self, symbol: str):
        """Cancel all open orders for a symbol"""
        try:
            self.client.futures_cancel_all_open_orders(symbol=symbol)
            
            # Remove from tracking
            if symbol in self.stop_loss_orders:
                del self.stop_loss_orders[symbol]
            if symbol in self.take_profit_orders:
                del self.take_profit_orders[symbol]
            if symbol in self.trailing_stops:
                del self.trailing_stops[symbol]
            
            # Reset TP2 hit flag if position exists
            if symbol in self.open_positions:
                self.open_positions[symbol]['tp2_hit'] = False
                
        except Exception as e:
            print(f"Error canceling orders for {symbol}: {e}")
    
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions"""
        positions = []
        
        try:
            # Fetch from Binance
            account_positions = self.client.futures_position_information()
            
            for pos in account_positions:
                position_amt = float(pos['positionAmt'])
                
                if position_amt != 0:  # Has open position
                    symbol = pos['symbol']
                    entry_price = float(pos['entryPrice'])
                    mark_price = float(pos['markPrice'])
                    leverage = int(pos['leverage'])
                    
                    # Calculate PnL
                    if position_amt > 0:  # LONG
                        pnl_percent = ((mark_price - entry_price) / entry_price) * 100 * leverage
                        side = 'LONG'
                    else:  # SHORT
                        pnl_percent = ((entry_price - mark_price) / entry_price) * 100 * leverage
                        side = 'SHORT'
                    
                    positions.append({
                        'symbol': symbol,
                        'side': side,
                        'entry_price': entry_price,
                        'current_price': mark_price,
                        'quantity': abs(position_amt),
                        'leverage': leverage,
                        'pnl_percent': pnl_percent,
                        'unrealized_pnl': float(pos['unRealizedProfit'])
                    })
                    
                    # Update local tracking (preserve trailing stop metadata)
                    if symbol not in self.open_positions:
                        self.open_positions[symbol] = {
                            'symbol': symbol,
                            'side': side,
                            'entry_price': entry_price,
                            'quantity': abs(position_amt),
                            'leverage': leverage,
                            'is_trailing': False,
                            'trail_started_at': None,
                            'highest_price_reached': mark_price if side == 'LONG' else mark_price,
                            'trail_type': None,
                            'current_stop_loss_price': None,
                            'aggressive_trailing': False,
                            'tp2_hit': False,
                            'tp_order_ids': [],
                            'profit_locked': False,
                            'partial_close_price': None,
                            'original_quantity': abs(position_amt),
                            'remaining_quantity': abs(position_amt),
                            'partial_exits': [],
                            'is_pyramid': False,
                            'pyramid_of_position_id': None,
                            'pyramid_multiplier': 1.0
                        }
                    else:
                        # Update existing position data but preserve trailing metadata
                        self.open_positions[symbol].update({
                            'entry_price': entry_price,
                            'quantity': abs(position_amt),
                            'remaining_quantity': abs(position_amt),
                            'leverage': leverage
                        })
                        if 'partial_exits' not in self.open_positions[symbol]:
                            self.open_positions[symbol]['partial_exits'] = []
                        # Update highest/lowest price reached if applicable
                        if side == 'LONG' and mark_price > self.open_positions[symbol].get('highest_price_reached', entry_price):
                            self.open_positions[symbol]['highest_price_reached'] = mark_price
                        elif side == 'SHORT' and mark_price < self.open_positions[symbol].get('highest_price_reached', entry_price):
                            self.open_positions[symbol]['highest_price_reached'] = mark_price
            
        except Exception as e:
            print(f"Error fetching positions: {e}")
        
        return positions
    
    def get_portfolio_status(self) -> Dict:
        """Get complete portfolio status"""
        try:
            # Get account info
            account = self.client.futures_account()
            
            total_balance = float(account['totalWalletBalance'])
            available_balance = float(account['availableBalance'])
            unrealized_pnl = float(account['totalUnrealizedProfit'])
            total_value = total_balance + unrealized_pnl
            
            # Calculate drawdown
            peak_value = max(total_value, INITIAL_CAPITAL)
            drawdown_percent = ((peak_value - total_value) / peak_value) * 100 if peak_value > 0 else 0
            
            # Get open positions
            positions = self.get_open_positions()
            
            return {
                'total_value': total_value,
                'total_balance': total_balance,
                'available_balance': available_balance,
                'unrealized_pnl': unrealized_pnl,
                'drawdown_percent': drawdown_percent,
                'positions': positions,
                'position_count': len(positions)
            }
            
        except Exception as e:
            print(f"Error getting portfolio status: {e}")
            return {
                'total_value': INITIAL_CAPITAL,
                'available_balance': INITIAL_CAPITAL,
                'unrealized_pnl': 0,
                'drawdown_percent': 0,
                'positions': [],
                'position_count': 0
            }
    
    def update_trailing_stops(self):
        """Update trailing stops for profitable positions (legacy method - kept for compatibility)"""
        try:
            positions = self.get_open_positions()
            
            for pos in positions:
                symbol = pos['symbol']
                pnl_percent = pos['pnl_percent']
                
                # Activate trailing stop if position is profitable enough
                if pnl_percent >= TRAILING_STOP_ACTIVATION * 100:
                    # Move stop loss to breakeven or better
                    if symbol not in self.trailing_stops or self.trailing_stops[symbol] < pnl_percent:
                        self._update_stop_to_breakeven(pos)
                        self.trailing_stops[symbol] = pnl_percent
                        
        except Exception as e:
            print(f"Error updating trailing stops: {e}")
    
    def update_dynamic_trailing_stop(self, position: Dict, market_data: Dict) -> bool:
        """
        Upgrade trailing stop system with ATR-based dynamic distances
        Parameters:
            position: Position object with entry_price, current_price, symbol, side, quantity
            market_data: Market data with indicators (ATR, etc.)
        Returns:
            bool: True if trailing stop was updated, False otherwise
        """
        try:
            symbol = position['symbol']
            side = position['side']
            entry_price = position.get('entry_price', 0)
            current_price = position.get('current_price', 0)
            
            if not entry_price or not current_price or entry_price <= 0:
                return False
            
            # Get indicators from market_data
            indicators = market_data.get('indicators', {})
            atr = indicators.get('atr', 0)
            
            # Calculate current profit percentage
            if side == 'LONG':
                profit_percent = ((current_price - entry_price) / entry_price) * 100
            else:  # SHORT
                profit_percent = ((entry_price - current_price) / entry_price) * 100
            
            # Check if position is in tracked positions
            if symbol not in self.open_positions:
                return False
            
            tracked_position = self.open_positions[symbol]
            
            # Update highest/lowest price reached
            if side == 'LONG':
                if current_price > tracked_position.get('highest_price_reached', entry_price):
                    tracked_position['highest_price_reached'] = current_price
            else:  # SHORT
                if current_price < tracked_position.get('highest_price_reached', entry_price):
                    tracked_position['highest_price_reached'] = current_price
            
            # Start trailing at 3% profit (not 5%)
            if profit_percent < 3.0:
                return False
            
            # Calculate ATR ratio
            atr_ratio = (atr / current_price) if current_price > 0 else 0
            
            # Determine trail distance based on volatility
            # Check for aggressive trailing (TP3 after TP2 hit)
            if tracked_position.get('aggressive_trailing', False):
                trail_distance_pct = 1.5  # Aggressive trailing for TP3
                trail_type = 'aggressive'
            elif atr_ratio > 0.005:  # High volatility (>0.5%)
                trail_distance_pct = 3.5  # Wide trailing
                trail_type = 'wide'
            else:  # Low volatility
                trail_distance_pct = 2.0  # Tight trailing
                trail_type = 'tight'
            
            # Calculate new stop price
            if side == 'LONG':
                new_stop = current_price * (1 - trail_distance_pct / 100)
                order_side = 'SELL'
            else:  # SHORT
                new_stop = current_price * (1 + trail_distance_pct / 100)
                order_side = 'BUY'
            
            # Get current stop loss price
            current_stop = tracked_position.get('current_stop_loss_price')
            
            # For LONG: only move stop UP (higher price = better protection)
            # For SHORT: only move stop DOWN (lower price = better protection)
            should_update = False
            if side == 'LONG':
                if current_stop is None or new_stop > current_stop:
                    should_update = True
            else:  # SHORT
                if current_stop is None or new_stop < current_stop:
                    should_update = True
            
            if not should_update:
                return False
            
            # Get precision for price rounding
            exchange_info = self.client.futures_exchange_info()
            symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
            if not symbol_info:
                return False
            
            price_precision = int(symbol_info.get('pricePrecision', 2))
            new_stop = round(new_stop, price_precision)
            
            # Get quantity from position or tracked position
            quantity = position.get('quantity', tracked_position.get('quantity', 0))
            if quantity <= 0:
                # Try to get from Binance if not available
                try:
                    pos_info = self.client.futures_position_information(symbol=symbol)
                    for pos in pos_info:
                        amt = float(pos.get('positionAmt', 0))
                        if abs(amt) > 0:
                            quantity = abs(amt)
                            break
                except Exception:
                    pass
            
            if quantity <= 0:
                print(f"   ⚠️ Cannot update trailing stop for {symbol}: quantity is 0")
                return False
            
            # Check if stop loss order exists
            stop_order_id = self.stop_loss_orders.get(symbol)
            if not stop_order_id:
                # Create new stop loss order
                return self._create_stop_loss_order(
                    symbol, side, new_stop, quantity, price_precision, trail_type
                )
            
            # Modify existing stop loss order with retry logic
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    # Binance doesn't have modify_order for futures, so cancel and recreate
                    try:
                        self.client.futures_cancel_order(symbol=symbol, orderId=stop_order_id)
                    except Exception:
                        pass  # Order might already be filled or canceled
                    
                    # Create new stop loss order at new price
                    order = self.client.futures_create_order(
                        symbol=symbol,
                        side=order_side,
                        type='STOP_MARKET',
                        stopPrice=new_stop,
                        quantity=quantity,
                        timeInForce='GTC'
                    )
                    
                    new_order_id = str(order['orderId'])
                    self.stop_loss_orders[symbol] = new_order_id
                    
                    # Update tracking
                    tracked_position['current_stop_loss_price'] = new_stop
                    tracked_position['trail_type'] = trail_type
                    
                    if not tracked_position.get('is_trailing', False):
                        tracked_position['is_trailing'] = True
                        tracked_position['trail_started_at'] = datetime.now(timezone.utc).isoformat()
                        print(f"   🎯 Trailing stop ACTIVATED for {symbol} @ {profit_percent:.2f}% profit")
                    
                    print(f"   📈 Trailing stop UPDATED for {symbol}: ${new_stop:,.2f} ({trail_type}, {trail_distance_pct:.1f}% from ${current_price:,.2f})")
                    return True
                    
                except BinanceAPIException as e:
                    if attempt < max_retries - 1:
                        time.sleep(0.5)  # Brief delay before retry
                        continue
                    else:
                        print(f"   ❌ CRITICAL: Failed to update trailing stop for {symbol} after {max_retries} attempts: {e}")
                        return False
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                        continue
                    else:
                        print(f"   ❌ CRITICAL: Error updating trailing stop for {symbol}: {e}")
                        return False
            
            return False
            
        except Exception as e:
            print(f"Error in update_dynamic_trailing_stop for {symbol}: {e}")
            return False
    
    def _create_stop_loss_order(self, symbol: str, side: str, stop_price: float, 
                                quantity: float, price_precision: int, trail_type: str) -> bool:
        """Helper to create a new stop loss order"""
        try:
            if side == 'LONG':
                order_side = 'SELL'
            else:
                order_side = 'BUY'
            
            order = self.client.futures_create_order(
                symbol=symbol,
                side=order_side,
                type='STOP_MARKET',
                stopPrice=round(stop_price, price_precision),
                quantity=quantity,
                timeInForce='GTC'
            )
            
            order_id = str(order['orderId'])
            self.stop_loss_orders[symbol] = order_id
            
            if symbol in self.open_positions:
                self.open_positions[symbol]['current_stop_loss_price'] = stop_price
                self.open_positions[symbol]['trail_type'] = trail_type
                self.open_positions[symbol]['is_trailing'] = True
                self.open_positions[symbol]['trail_started_at'] = datetime.now(timezone.utc).isoformat()
            
            return True
            
        except Exception as e:
            print(f"Error creating stop loss order for {symbol}: {e}")
            return False
    
    def check_tp_hits_and_convert_tp3(self):
        """
        Check if TP2 has been hit, and if so, convert TP3 to trailing stop
        This runs periodically to monitor TP execution
        """
        try:
            positions = self.get_open_positions()
            
            for pos in positions:
                symbol = pos['symbol']
                side = pos['side']
                entry_price = pos.get('entry_price', 0)
                current_price = pos.get('current_price', 0)
                
                if not entry_price or not current_price:
                    continue
                
                # Check if TP2 hit flag is already set
                if symbol in self.open_positions:
                    if self.open_positions[symbol].get('tp2_hit', False):
                        # TP2 already hit, check if we need to update trailing stop for TP3
                        self._manage_tp3_trailing_stop(pos)
                        continue
                
                # Calculate current profit
                if side == 'LONG':
                    profit_percent = ((current_price - entry_price) / entry_price) * 100
                else:  # SHORT
                    profit_percent = ((entry_price - current_price) / entry_price) * 100
                
                # Check if TP2 (12%) has been hit
                if profit_percent >= 12.0 and symbol in self.open_positions:
                    if not self.open_positions[symbol].get('tp2_hit', False):
                        # TP2 hit! Convert TP3 to trailing stop
                        print(f"   🎉 TP2 hit for {symbol}! Converting TP3 to trailing stop...")
                        self.open_positions[symbol]['tp2_hit'] = True
                        self._convert_tp3_to_trailing_stop(symbol, pos)
                        
        except Exception as e:
            print(f"Error checking TP hits: {e}")
    
    def _convert_tp3_to_trailing_stop(self, symbol: str, position: Dict):
        """
        Convert TP3 order to trailing stop when TP2 is hit
        Uses aggressive trailing (1.5% distance) for remaining 30% position
        """
        try:
            # Cancel existing TP3 order (should be the 3rd order in list)
            tp_orders = self.take_profit_orders.get(symbol, [])
            if len(tp_orders) >= 3:
                tp3_order_id = tp_orders[2]  # Third TP order
                try:
                    self.client.futures_cancel_order(symbol=symbol, orderId=tp3_order_id)
                    print(f"   ✅ Canceled TP3 order {tp3_order_id} for {symbol}")
                    
                    # Remove from tracking
                    if symbol in self.take_profit_orders:
                        self.take_profit_orders[symbol] = tp_orders[:2]  # Keep only TP1 and TP2
                except Exception as e:
                    print(f"   ⚠️ Could not cancel TP3 order: {e}")
            
            # Set aggressive trailing flag for remaining 30% position
            if symbol in self.open_positions:
                self.open_positions[symbol]['aggressive_trailing'] = True
                self.open_positions[symbol]['trail_type'] = 'aggressive'
                print(f"   🔄 TP3 converted to AGGRESSIVE trailing stop for {symbol} (1.5% distance, 30% remaining)")
                
        except Exception as e:
            print(f"Error converting TP3 to trailing stop for {symbol}: {e}")
    
    def _manage_tp3_trailing_stop(self, position: Dict):
        """
        Manage trailing stop for TP3 position (30% remaining after TP2 hit)
        This is now handled by update_dynamic_trailing_stop() with aggressive_trailing flag
        Keeping this method for compatibility but it's deprecated
        """
        # Aggressive trailing is now handled in update_dynamic_trailing_stop()
        # when aggressive_trailing flag is True
        pass

    def close_stale_positions(self):
        """Close positions that haven't moved (flat PnL) for a while to free capital."""
        try:
            positions = self.get_open_positions()
            if not positions:
                return
            # Fetch recent account trades times as proxy for last activity
            now = datetime.utcnow()
            for pos in positions:
                symbol = pos['symbol']
                try:
                    trades = self.client.futures_account_trades(symbol=symbol, limit=1)
                    if trades:
                        # time in ms
                        t = int(trades[-1].get('time', 0))
                        last_ms = max(t, 0)
                    else:
                        last_ms = 0
                except Exception:
                    last_ms = 0

                minutes_since = 9999
                if last_ms:
                    minutes_since = max(0, int((now.timestamp()*1000 - last_ms) / 60000))

                if minutes_since >= STALE_POSITION_MINUTES and abs(pos.get('pnl_percent', 0)) <= (STALE_PNL_BAND):
                    print(f"⏳ Closing stale position {symbol} (pnl {pos.get('pnl_percent', 0):+.2f}% for {minutes_since}m)")
                    self.close_position(symbol)
        except Exception as e:
            print(f"Error closing stale positions: {e}")
    
    def _update_stop_to_breakeven(self, position: Dict):
        """Move stop loss to breakeven"""
        try:
            symbol = position['symbol']
            side = position['side']
            entry_price = position['entry_price']
            quantity = position['quantity']
            
            # Cancel existing stop loss
            if symbol in self.stop_loss_orders:
                try:
                    self.client.futures_cancel_order(
                        symbol=symbol,
                        orderId=self.stop_loss_orders[symbol]
                    )
                except:
                    pass
            
            # Set new stop at breakeven (entry price)
            if side == 'LONG':
                stop_price = entry_price * 1.001  # Slightly above entry to lock in tiny profit
                order_side = 'SELL'
            else:
                stop_price = entry_price * 0.999  # Slightly below entry
                order_side = 'BUY'
            
            order = self.client.futures_create_order(
                symbol=symbol,
                side=order_side,
                type='STOP_MARKET',
                stopPrice=round(stop_price, 2),
                quantity=quantity,
                timeInForce='GTC'
            )
            
            self.stop_loss_orders[symbol] = str(order['orderId'])
            print(f"   🔄 Trailing stop activated for {symbol} @ breakeven")
            
        except Exception as e:
            print(f"Error updating stop to breakeven for {symbol}: {e}")
    
    def close_all_positions(self):
        """Close all open positions (emergency or end of competition)"""
        print("🚨 Closing all open positions...")
        
        positions = self.get_open_positions()
        
        for pos in positions:
            result = self.close_position(pos['symbol'])
            if result['status'] == 'SUCCESS':
                print(f"   ✅ Closed {pos['symbol']}")
            else:
                print(f"   ❌ Failed to close {pos['symbol']}: {result.get('message')}")


# Global executor instance
_executor_instance = None

def get_executor() -> Executor:
    """Get or create executor instance"""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = Executor()
    return _executor_instance

