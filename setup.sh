#!/bin/bash

# Setup script for Autonomous AI Trading Bot

echo "=========================================="
echo "🤖 AI Trading Bot - Setup Script"
echo "=========================================="
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then 
    echo "✅ Python $python_version (OK)"
else
    echo "❌ Python 3.10+ required (found $python_version)"
    exit 1
fi
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp env.example .env
    echo "✅ Created .env file"
    echo "⚠️  IMPORTANT: Edit .env with your API keys!"
    echo ""
    echo "You need to add:"
    echo "  1. Binance Testnet API key and secret"
    echo "  2. DeepSeek API key"
    echo ""
    read -p "Press Enter to open .env in nano editor (or Ctrl+C to skip)..."
    nano .env
else
    echo "✅ .env file already exists"
fi
echo ""

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p logs
echo "✅ Logs directory created"
echo ""

# Run tests
echo "🧪 Running tests..."
python3 -m pytest tests/ -v
if [ $? -eq 0 ]; then
    echo "✅ All tests passed"
else
    echo "⚠️  Some tests failed (this is OK if APIs not configured yet)"
fi
echo ""

echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Test connection: python3 -c 'from data_pipeline import DataPipeline; DataPipeline().test_connection()'"
echo "  3. Run bot: python3 run_with_restart.py"
echo ""
echo "Good luck! 🚀"

