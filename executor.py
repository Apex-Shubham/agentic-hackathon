"""
Order Execution Engine
Handles trade execution, position management, stop-loss and take-profit orders
"""
from typing import Dict, List, Optional
import math
from datetime import datetime, timezone
from binance.client import Client
from binance.exceptions import BinanceAPIException
from config import (
    BINANCE_API_KEY, BINANCE_API_SECRET, TRAILING_STOP_ACTIVATION,
    SCALED_TP_LEVELS, INITIAL_CAPITAL, STALE_POSITION_MINUTES, STALE_PNL_BAND
)


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
            
            # Store position info
            self.open_positions[symbol] = {
                'symbol': symbol,
                'side': side,
                'entry_price': fill_price,
                'quantity': quantity,
                'leverage': leverage,
                'entry_time': datetime.now(timezone.utc).isoformat(),
                'order_id': order['orderId']
            }
            
            # Set stop loss
            sl_order_id = self.set_stop_loss(
                symbol, side, fill_price, quantity, decision['stop_loss_percent'], price_precision
            )
            
            # Set take profit levels
            tp_order_ids = self.set_take_profit(
                symbol, side, fill_price, quantity, decision['take_profit_percent'], price_precision
            )

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
        price_precision: int
    ) -> Optional[str]:
        """Set stop loss order"""
        try:
            # Calculate stop price
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
        """Set scaled take profit orders"""
        order_ids = []
        
        try:
            # Fetch symbol filters for proper rounding
            exchange_info = self.client.futures_exchange_info()
            symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
            if not symbol_info:
                raise ValueError(f"Symbol info not found for {symbol}")
            # LOT_SIZE
            lot_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
            step_size = float(lot_filter['stepSize'])
            min_qty = float(lot_filter['minQty'])
            # PRICE precision
            price_precision_local = int(symbol_info.get('pricePrecision', price_precision))
            
            # Calculate TP levels (50%, 30%, 20% of position)
            tp_quantities = [
                quantity * SCALED_TP_LEVELS[0],
                quantity * SCALED_TP_LEVELS[1],
                quantity * SCALED_TP_LEVELS[2]
            ]
            
            # TP prices at different levels
            tp_percents = [
                take_profit_percent * 0.5,  # First TP at 50% of target
                take_profit_percent * 0.75,  # Second TP at 75% of target
                take_profit_percent  # Final TP at full target
            ]
            
            for i, (tp_qty, tp_pct) in enumerate(zip(tp_quantities, tp_percents)):
                if side == 'LONG':
                    tp_price = entry_price * (1 + tp_pct / 100)
                    order_side = 'SELL'
                else:  # SHORT
                    tp_price = entry_price * (1 - tp_pct / 100)
                    order_side = 'BUY'
                
                if tp_price <= 0:
                    raise ValueError("Computed take-profit price <= 0")
                # Round price to precision
                tp_price = round(tp_price, price_precision_local)
                # Round quantity down to nearest step size increment
                if step_size <= 0:
                    raise ValueError("Invalid step size from LOT_SIZE filter")
                tp_qty = math.floor(tp_qty / step_size) * step_size
                # Skip if below minimum quantity
                if tp_qty < min_qty or tp_qty <= 0:
                    continue
                
                # Place take profit order
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=order_side,
                    type='TAKE_PROFIT_MARKET',
                    stopPrice=tp_price,
                    quantity=tp_qty,
                    timeInForce='GTC'
                )
                
                order_ids.append(str(order['orderId']))
                print(f"   🎯 Take Profit {i+1} set @ ${tp_price:,.2f} ({tp_pct:.1f}%) | qty={tp_qty}")
            
            self.take_profit_orders[symbol] = order_ids
            
        except Exception as e:
            print(f"Error setting take profit for {symbol}: {e}")
        
        return order_ids
    
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
                    
                    # Update local tracking
                    if symbol not in self.open_positions:
                        self.open_positions[symbol] = {
                            'symbol': symbol,
                            'side': side,
                            'entry_price': entry_price,
                            'quantity': abs(position_amt),
                            'leverage': leverage
                        }
            
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
        """Update trailing stops for profitable positions"""
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

