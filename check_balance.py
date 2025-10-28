from binance.client import Client
from binance.enums import *

# === Initialize client ===
api_key = "DdvEYmocUpvdApqohQFMZqo5F7mhzjQhU6T4GSueL0JrPpjGw1O5YJQZYzvwY2Zk"
api_secret = "hLtw5wHCkGv6i3oIr9MWcwMbJ7nKmBRc811gBSDYMwEz3wN5yhzC3Ci9TKmE371p"

client = Client(api_key, api_secret, testnet=True)

print("🔍 Checking open positions...\n")

positions = client.futures_position_information()
open_positions = [p for p in positions if float(p['positionAmt']) != 0.0]

if not open_positions:
    print("✅ No open positions found. You're all clear!")
else:
    for pos in open_positions:
        symbol = pos['symbol']
        amt = float(pos['positionAmt'])
        side = SIDE_SELL if amt > 0 else SIDE_BUY  # Reverse the position to close
        qty = abs(amt)

        print(f"⚙️ Closing {symbol} position | Side: {side} | Qty: {qty}")

        try:
            order = client.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=qty,
                reduceOnly=True
            )
            print(f"✅ Closed position for {symbol}")
        except Exception as e:
            print(f"❌ Error closing {symbol}: {e}")

    print("\n🏁 All done! All open positions should now be closed.")
