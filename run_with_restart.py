"""
Deprecated: Auto-Restart Wrapper (DISABLED)
This wrapper is intentionally disabled to prevent any auto-restart behavior.
Run the bot directly with: `python main.py`.
"""
import subprocess
import sys
import time
from datetime import datetime, timezone


def run_with_auto_restart():
    print("🛑 Auto-restart wrapper is disabled. Run the bot directly: python main.py")
    sys.exit(1)


if __name__ == "__main__":
    run_with_auto_restart()

