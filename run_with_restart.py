"""
Auto-Restart Wrapper
Automatically restarts the trading bot if it crashes, ensuring 14-day uptime
"""
import subprocess
import sys
import time
from datetime import datetime, timezone


def run_with_auto_restart():
    """
    Wrapper to auto-restart bot on crash
    Ensures bot runs continuously for the full 14-day competition
    """
    restart_count = 0
    max_restarts = 100  # Prevent infinite restart loop
    
    print("=" * 70)
    print("🔄 AUTO-RESTART WRAPPER ACTIVE")
    print("=" * 70)
    print("Bot will automatically restart on crashes")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    while restart_count < max_restarts:
        try:
            print(f"🚀 Starting trading bot... (Attempt #{restart_count + 1})")
            print(f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print()
            
            # Run the main bot
            result = subprocess.run(
                [sys.executable, "main.py"],
                check=True
            )
            
            # If we get here, bot completed normally (14 days finished)
            print("\n✅ Bot completed successfully!")
            print("🏁 Competition period finished")
            break
            
        except subprocess.CalledProcessError as e:
            restart_count += 1
            print(f"\n💥 Bot crashed with error code: {e.returncode}")
            print(f"🔄 Restart #{restart_count}/{max_restarts}")
            
            if restart_count >= max_restarts:
                print(f"\n❌ Maximum restart limit reached ({max_restarts})")
                print("⚠️  Manual intervention required")
                sys.exit(1)
            
            # Exponential backoff (but cap at 2 minutes)
            wait_time = min(30 * (2 ** min(restart_count - 1, 3)), 120)
            print(f"⏳ Waiting {wait_time}s before restart...")
            print(f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print()
            
            time.sleep(wait_time)
            
        except KeyboardInterrupt:
            print("\n⚠️  Keyboard interrupt received")
            print("🛑 Stopping auto-restart wrapper")
            sys.exit(0)
            
        except Exception as e:
            restart_count += 1
            print(f"\n💥 Unexpected error: {e}")
            print(f"🔄 Restart #{restart_count}/{max_restarts}")
            
            if restart_count >= max_restarts:
                print(f"\n❌ Maximum restart limit reached ({max_restarts})")
                sys.exit(1)
            
            wait_time = 60
            print(f"⏳ Waiting {wait_time}s before restart...")
            time.sleep(wait_time)
    
    print("\n" + "=" * 70)
    print("🏁 AUTO-RESTART WRAPPER TERMINATED")
    print("=" * 70)


if __name__ == "__main__":
    run_with_auto_restart()

