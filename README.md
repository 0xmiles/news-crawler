# News Crawler

A comprehensive Python-based web crawler for dev blogs and YouTube video summarization with AI-powered content processing.

## Features

- **Dev Blog Crawling**: Automatically crawl and extract content from development blogs
- **YouTube Summarization**: Extract and summarize YouTube videos using AI
- **Pattern-Based Crawling**: Crawl URLs with numeric patterns (e.g., maeil-mail.kr/question/50)
- **AI Integration**: Support for OpenAI, Anthropic, and other AI providers
- **Notion Integration**: Direct upload of summaries to Notion databases
- **Content Filtering**: Backend-focused content filtering with keyword detection
- **CLI Interface**: Easy-to-use command-line interface
- **Extensible Architecture**: Plugin system for custom crawlers

## Installation

### Quick Setup (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd news-crawler

# Run setup script
./setup.sh
```

### Manual Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd news-crawler
```

2. Create virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up environment variables:

```bash
cp env.example .env
# Edit .env with your API keys
```

📖 **For detailed setup instructions, see [QUICKSTART.md](QUICKSTART.md)**

## Quick Start

### Basic Usage

```bash
# Crawl a specific dev blog
news-crawler crawl "https://example-blog.com" --type blog

# Summarize a YouTube video
news-crawler summarize "https://youtube.com/watch?v=VIDEO_ID"

# Crawl pattern-based URLs (like maeil-mail.kr)
news-crawler crawl-pattern --base-url "https://www.maeil-mail.kr" --start 1 --end 50

# Upload to Notion database
news-crawler crawl "https://example-blog.com" --notion-db "your-database-id"

# Add summaries to specific Notion page
news-crawler add-to-page "https://example.com" --notion-page "https://notion.so/your-page-id"

# Test all connections
news-crawler test
```

### Pattern-Based Crawling Example

For the specific use case mentioned (maeil-mail.kr with numeric patterns):

```bash
# Crawl maeil-mail.kr questions 1-50
# To Notion database
news-crawler crawl-pattern \
  --base-url "https://www.maeil-mail.kr" \
  --start 1 \
  --end 50 \
  --template "https://www.maeil-mail.kr/question/{number}" \
  --notion-db "your-notion-database-id"

# To specific Notion page
news-crawler crawl-pattern \
  --base-url "https://www.maeil-mail.kr" \
  --start 1 \
  --end 50 \
  --template "https://www.maeil-mail.kr/question/{number}" \
  --notion-page "https://notion.so/your-page-id"
```

### Python Script Example

```python
import asyncio
from news_crawler.core.config import Config
from news_crawler.core.crawler import Crawler

async def main():
    # Load configuration
    config = Config.from_file("config.yaml")

    # Initialize crawler
    crawler = Crawler(config.dict())

    # Crawl pattern URLs
    pattern_config = {
        'patterns': [{
            'type': 'numeric_range',
            'start': 1,
            'end': 50,
            'template': 'https://www.maeil-mail.kr/question/{number}'
        }]
    }

    contents = await crawler.crawl_pattern_urls(
        "https://www.maeil-mail.kr",
        pattern_config
    )

    # Upload to Notion
    page_ids = await crawler.summarize_and_upload(
        contents,
        "your-notion-database-id"
    )

    print(f"Uploaded {len(page_ids)} items to Notion")

asyncio.run(main())
```

### Configuration

Create a `config.yaml` file:

```yaml
# AI Configuration
ai:
  provider: "anthropic" # or "openai"
  model: "claude-3-sonnet-20240229"
  api_key: "${ANTHROPIC_API_KEY}"

# Notion Integration
notion:
  api_key: "${NOTION_API_KEY}"

# Content Filters (Backend-focused)
filters:
  keywords:
    required: ["백엔드", "서버", "API", "데이터베이스"]
    excluded: ["프론트엔드", "UI", "UX"]

# Pattern-based crawling
pattern:
  patterns:
    - type: "numeric_range"
      start: 1
      end: 50
      template: "https://www.maeil-mail.kr/question/{number}"
```

## Architecture

```
news_crawler/
├── core/           # Core functionality
├── crawlers/       # Web crawler implementations
├── ai/            # AI integration
├── storage/       # Data storage
├── scheduler/     # Scheduling system
├── cli/           # Command-line interface
└── utils/         # Utility functions
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black news_crawler/
flake8 news_crawler/
```

## License

MIT License - see LICENSE file for details.
