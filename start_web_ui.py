#!/usr/bin/env python3
"""
Start the web UI for Apex Trading Bot
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    from web_ui import app
    app.run(host='0.0.0.0', port=5000, debug=False)

