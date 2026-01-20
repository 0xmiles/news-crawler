# Quick Start Guide - Blog Agents

Get started with Blog Agents in 5 minutes.

## Prerequisites

- Python 3.9+
- Anthropic API key

## Installation

```bash
# 1. Install dependencies
pip install -r blog_agents_requirements.txt

# 2. Setup environment
cp .env.example .env
```

## Configure API Keys

Edit `.env` file:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Optional (for web search)
GOOGLE_SEARCH_API_KEY=your_key
GOOGLE_SEARCH_ENGINE_ID=your_engine_id
```

## Generate Your First Blog

```bash
python -m blog_agents.cli.blog_cli generate --keywords "Python testing best practices"
```

That's it! Your blog will be saved in `outputs/` directory.

## What Happens?

1. **Searches** for relevant articles (10 results)
2. **Selects** top 3 articles
3. **Analyzes** content and creates outline
4. **Writes** blog post (~1500 words)
5. **Applies** tone from `references/reference.md`
6. **Saves** to `outputs/python-testing-best-practices-2026-01-20.md`

## Customize Writing Style

1. Create or edit `references/reference.md`
2. Add 2-3 sample blog posts in your preferred style
3. Run generation - the system will learn and apply your tone!

## View Progress

```bash
# Verbose mode shows detailed progress
python -m blog_agents.cli.blog_cli generate -k "Docker containers" -v
```

## CLI Commands

```bash
# Generate blog
generate --keywords "your topic"

# Search only
search-only --keywords "your topic"

# Analyze tone
analyze-tone --file references/reference.md

# List workflows
list-workflows

# Show help
--help
```

## Python API

```python
import asyncio
from blog_agents.core.orchestrator import BlogOrchestrator

async def main():
    orchestrator = BlogOrchestrator()
    result = await orchestrator.generate_blog("Python asyncio")
    print(f"Done! {result['blog_file']}")

asyncio.run(main())
```

## Output Files

After generation, you'll find:

```
outputs/
├── search_results.json      # Search results
├── blog_plan.json           # Blog outline
├── your-topic-2026-01-20.md # Final blog post
└── checkpoint_xxx.json      # Workflow checkpoint
```

## Next Steps

- Read `README.md` for detailed documentation
- Check `examples/blog_generation_example.py` for advanced usage
- Customize `config.yaml` for your needs

## Common Issues

**No search results?**
- Make sure you have configured Google/Bing API keys
- Or use a different search provider in `config.yaml`

**Tone not applied?**
- Check `references/reference.md` exists
- Add more content to the reference file (500+ words recommended)

**Generation fails?**
- Check `blog_agents.log` for detailed error messages
- Verify API keys are correct
- Try with `--verbose` flag

## Getting Help

```bash
python -m blog_agents.cli.blog_cli --help
python -m blog_agents.cli.blog_cli generate --help
```

Happy blogging! 🎉
