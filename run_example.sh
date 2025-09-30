#!/bin/bash

# News Crawler Example Runner
echo "🕷️ News Crawler Example Runner"
echo "================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please run setup.sh first."
    exit 1
fi

echo ""
echo "📋 Available commands:"
echo "1. Test connections: news-crawler test"
echo "2. Crawl single URL: news-crawler crawl --url 'https://example.com'"
echo "3. Crawl pattern URLs: news-crawler crawl-pattern --base-url 'https://www.maeil-mail.kr' --start 1 --end 5"
echo "4. Summarize URL: news-crawler summarize --url 'https://example.com'"
echo ""

# Interactive menu
while true; do
    echo "What would you like to do?"
    echo "1) Test connections"
    echo "2) Crawl maeil-mail.kr pattern (questions 1-5)"
    echo "3) Crawl single URL"
    echo "4) Summarize single URL"
    echo "5) Exit"
    echo ""
    read -p "Enter your choice (1-5): " choice
    
    case $choice in
        1)
            echo "🧪 Testing connections..."
            news-crawler test
            ;;
        2)
            echo "🕷️ Crawling maeil-mail.kr pattern..."
            read -p "Enter Notion Database ID (or press Enter to skip): " notion_db
            if [ -n "$notion_db" ]; then
                news-crawler crawl-pattern --base-url "https://www.maeil-mail.kr" --start 1 --end 5 --notion-db "$notion_db"
            else
                news-crawler crawl-pattern --base-url "https://www.maeil-mail.kr" --start 1 --end 5
            fi
            ;;
        3)
            read -p "Enter URL to crawl: " url
            read -p "Enter Notion Database ID (or press Enter to skip): " notion_db
            if [ -n "$notion_db" ]; then
                news-crawler crawl --url "$url" --notion-db "$notion_db"
            else
                news-crawler crawl --url "$url"
            fi
            ;;
        4)
            read -p "Enter URL to summarize: " url
            read -p "Enter Notion Database ID (or press Enter to skip): " notion_db
            if [ -n "$notion_db" ]; then
                news-crawler summarize --url "$url" --notion-db "$notion_db"
            else
                news-crawler summarize --url "$url"
            fi
            ;;
        5)
            echo "👋 Goodbye!"
            break
            ;;
        *)
            echo "❌ Invalid choice. Please enter 1-5."
            ;;
    esac
    echo ""
done
