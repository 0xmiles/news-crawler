#!/bin/bash

# News Crawler Setup Script
echo "🚀 Setting up News Crawler..."

# Check if Python 3.8+ is installed
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8+ is required. Current version: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create .env file from example
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file with your API keys!"
else
    echo "✅ .env file already exists"
fi

# Create data directory
echo "📁 Creating data directory..."
mkdir -p data

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p logs

# Make CLI executable
echo "🔧 Making CLI executable..."
chmod +x news_crawler/cli/main.py

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your API keys:"
echo "   - ANTHROPIC_API_KEY=your_anthropic_api_key"
echo "   - NOTION_API_KEY=your_notion_api_key"
echo ""
echo "2. Test the installation:"
echo "   source venv/bin/activate"
echo "   news-crawler test"
echo ""
echo "3. Start crawling:"
echo "   news-crawler crawl-pattern --base-url 'https://www.maeil-mail.kr' --start 1 --end 10"
echo ""
echo "Happy crawling! 🕷️"
