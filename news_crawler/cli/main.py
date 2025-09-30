"""
Main CLI interface for the news crawler.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional, List
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from news_crawler.core.config import Config
from news_crawler.core.crawler import Crawler
from news_crawler.integrations.notion_client import NotionClient


console = Console()


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config: Optional[str], verbose: bool):
    """News Crawler - A comprehensive web crawler for dev blogs and YouTube video summarization."""
    ctx.ensure_object(dict)
    
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    try:
        if config:
            ctx.obj['config'] = Config.from_file(config)
        else:
            ctx.obj['config'] = Config.from_env()
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('url')
@click.option('--type', '-t', type=click.Choice(['auto', 'blog', 'youtube', 'pattern']), 
              default='auto', help='Content type to crawl')
@click.option('--notion-db', help='Notion database ID for uploading')
@click.option('--summarize', is_flag=True, help='Summarize content using AI')
@click.pass_context
def crawl(ctx, url: str, type: str, notion_db: Optional[str], summarize: bool):
    """Crawl a single URL."""
    config = ctx.obj['config']
    crawler = Crawler(config.dict())
    
    async def _crawl():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Crawling...", total=None)
            
            # Crawl content
            contents = await crawler.crawl_url(url, type)
            
            if not contents:
                console.print("[yellow]No content found or crawled.[/yellow]")
                return
            
            console.print(f"[green]Successfully crawled {len(contents)} items[/green]")
            
            # Display results
            table = Table(title="Crawled Content")
            table.add_column("Title", style="cyan")
            table.add_column("URL", style="blue")
            table.add_column("Author", style="magenta")
            table.add_column("Length", style="green")
            
            for content in contents:
                table.add_row(
                    content.title[:50] + "..." if len(content.title) > 50 else content.title,
                    content.url,
                    content.author or "Unknown",
                    str(len(content.content))
                )
            
            console.print(table)
            
            # Upload to Notion if specified
            if notion_db and contents:
                progress.update(task, description="Uploading to Notion...")
                page_ids = await crawler.summarize_and_upload(contents, notion_db)
                console.print(f"[green]Uploaded {len(page_ids)} items to Notion[/green]")
    
    asyncio.run(_crawl())


@cli.command()
@click.argument('base_url')
@click.option('--start', default=1, help='Start number for pattern')
@click.option('--end', default=10, help='End number for pattern')
@click.option('--template', default='{base_url}/{number}', help='URL template')
@click.option('--notion-db', help='Notion database ID for uploading')
@click.option('--notion-page', help='Notion page URL to add summaries to')
@click.option('--summarize', is_flag=True, help='Summarize content using AI')
@click.pass_context
def crawl_pattern(ctx, base_url: str, start: int, end: int, template: str, 
                  notion_db: Optional[str], notion_page: Optional[str], summarize: bool):
    """Crawl URLs based on patterns."""
    config = ctx.obj['config']
    crawler = Crawler(config.dict())
    
    pattern_config = {
        'patterns': [{
            'type': 'numeric_range',
            'start': start,
            'end': end,
            'template': template
        }]
    }
    
    async def _crawl_pattern():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Crawling pattern URLs...", total=None)
            
            # Crawl pattern URLs
            contents = await crawler.crawl_pattern_urls(base_url, pattern_config)
            
            if not contents:
                console.print("[yellow]No content found or crawled.[/yellow]")
                return
            
            console.print(f"[green]Successfully crawled {len(contents)} items[/green]")
            
            # Display results
            table = Table(title="Pattern Crawled Content")
            table.add_column("Title", style="cyan")
            table.add_column("URL", style="blue")
            table.add_column("Author", style="magenta")
            table.add_column("Length", style="green")
            
            for content in contents:
                table.add_row(
                    content.title[:50] + "..." if len(content.title) > 50 else content.title,
                    content.url,
                    content.author or "Unknown",
                    str(len(content.content))
                )
            
            console.print(table)
            
            # Upload to Notion if specified
            if notion_db and contents:
                progress.update(task, description="Uploading to Notion database...")
                page_ids = await crawler.summarize_and_upload(contents, notion_db)
                console.print(f"[green]Uploaded {len(page_ids)} items to Notion database[/green]")
            elif notion_page and contents:
                progress.update(task, description="Adding to Notion page...")
                results = await crawler.add_summary_to_notion_page(notion_page, contents)
                successful = sum(results)
                console.print(f"[green]Added {successful}/{len(contents)} summaries to Notion page[/green]")
    
    asyncio.run(_crawl_pattern())


@cli.command()
@click.argument('url')
@click.option('--notion-db', help='Notion database ID for uploading')
@click.pass_context
def summarize(ctx, url: str, notion_db: Optional[str]):
    """Summarize a single URL and optionally upload to Notion."""
    config = ctx.obj['config']
    crawler = Crawler(config.dict())
    
    async def _summarize():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Summarizing...", total=None)
            
            # Crawl and summarize
            contents = await crawler.crawl_url(url)
            
            if not contents:
                console.print("[yellow]No content found to summarize.[/yellow]")
                return
            
            if notion_db:
                progress.update(task, description="Uploading to Notion...")
                page_ids = await crawler.summarize_and_upload(contents, notion_db)
                console.print(f"[green]Uploaded {len(page_ids)} summaries to Notion[/green]")
            else:
                # Just display summaries
                for content in contents:
                    console.print(f"\n[bold cyan]Title:[/bold cyan] {content.title}")
                    console.print(f"[bold blue]URL:[/bold blue] {content.url}")
                    
                    # Get summary
                    summary = await crawler.summarizer.summarize(content.content)
                    console.print(f"\n[bold green]Summary:[/bold green]")
                    console.print(summary)
                    
                    # Get key points
                    key_points = await crawler.summarizer.extract_key_points(content.content)
                    if key_points:
                        console.print(f"\n[bold yellow]Key Points:[/bold yellow]")
                        for i, point in enumerate(key_points, 1):
                            console.print(f"{i}. {point}")
    
    asyncio.run(_summarize())


@cli.command()
@click.argument('page_url')
@click.option('--notion-page', help='Notion page URL to add summaries to')
@click.pass_context
def add_to_page(ctx, page_url: str, notion_page: Optional[str]):
    """Add summary to a specific Notion page."""
    config = ctx.obj['config']
    crawler = Crawler(config.dict())
    
    async def _add_to_page():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Adding to Notion page...", total=None)
            
            # Crawl content
            contents = await crawler.crawl_url(page_url)
            
            if not contents:
                console.print("[yellow]No content found to add.[/yellow]")
                return
            
            if notion_page:
                # Add to specific Notion page
                results = await crawler.add_summary_to_notion_page(notion_page, contents)
                successful = sum(results)
                console.print(f"[green]Successfully added {successful}/{len(contents)} summaries to Notion page[/green]")
            else:
                console.print("[yellow]No Notion page URL provided. Use --notion-page option.[/yellow]")
    
    asyncio.run(_add_to_page())


@cli.command()
@click.pass_context
def test(ctx):
    """Test all service connections."""
    config = ctx.obj['config']
    crawler = Crawler(config.dict())
    
    async def _test():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Testing connections...", total=None)
            
            results = await crawler.test_connections()
            
            # Display results
            table = Table(title="Connection Test Results")
            table.add_column("Service", style="cyan")
            table.add_column("Status", style="green")
            
            for service, status in results.items():
                status_text = "✓ Connected" if status else "✗ Failed"
                status_style = "green" if status else "red"
                table.add_row(service.title(), f"[{status_style}]{status_text}[/{status_style}]")
            
            console.print(table)
    
    asyncio.run(_test())


@cli.command()
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.pass_context
def config(ctx, output: Optional[str]):
    """Generate configuration file."""
    config = ctx.obj['config']
    
    if output:
        config.save_to_file(output)
        console.print(f"[green]Configuration saved to {output}[/green]")
    else:
        # Display current configuration
        console.print("[bold cyan]Current Configuration:[/bold cyan]")
        console.print(config.dict())


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()
