#!/bin/bash

# Blog Agents Setup Script
# This script helps set up the Blog Agents environment

set -e  # Exit on error

echo "================================"
echo "Blog Agents - Setup Script"
echo "================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.9 or higher is required"
    echo "Current version: $python_version"
    exit 1
fi

echo "✓ Python version: $python_version"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Skipping..."
else
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r blog_agents_requirements.txt
echo "✓ Dependencies installed"
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p outputs
mkdir -p references
echo "✓ Directories created"
echo ""

# Setup environment file
if [ -f ".env" ]; then
    echo ".env file already exists. Skipping..."
else
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "IMPORTANT: Please edit .env and add your API keys:"
    echo "  - ANTHROPIC_API_KEY (required)"
    echo "  - GOOGLE_SEARCH_API_KEY (optional)"
    echo "  - GOOGLE_SEARCH_ENGINE_ID (optional)"
    echo "  - BING_SEARCH_API_KEY (optional)"
fi
echo ""

# Test installation
echo "Testing installation..."
python3 -c "import blog_agents; print('✓ Blog Agents package imported successfully')"
echo ""

# Display next steps
echo "================================"
echo "Setup Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. (Optional) Customize config.yaml"
echo "3. (Optional) Add reference content to references/reference.md"
echo ""
echo "Try it out:"
echo "  python -m blog_agents.cli.blog_cli generate --keywords \"Python testing\""
echo ""
echo "For more information:"
echo "  - README.md for full documentation"
echo "  - QUICKSTART.md for quick start guide"
echo "  - examples/blog_generation_example.py for code examples"
echo ""
