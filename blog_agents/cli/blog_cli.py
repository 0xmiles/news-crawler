"""CLI interface for blog agents system."""

import asyncio
import logging
import sys
from pathlib import Path
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint
from dotenv import load_dotenv

from blog_agents.config.agent_config import get_config, reset_config
from blog_agents.core.orchestrator import BlogOrchestrator
from blog_agents.skills.tone_learner import ToneLearner

# Load environment variables
load_dotenv()

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('blog_agents.log'),
        logging.StreamHandler(sys.stdout)
    ]
)


@click.group()
@click.option('--config', default='config.yaml', help='Path to configuration file')
@click.pass_context
def cli(ctx, config):
    """Blog Agents - Multi-Agent Blog Content Generation System."""
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config


@cli.command()
@click.option('--keywords', '-k', required=True, help='Search keywords or topic')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def generate(ctx, keywords, verbose):
    """Generate a complete blog post from keywords."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    console.print(Panel.fit(
        f"[bold cyan]Generating Blog Post[/bold cyan]\n"
        f"Keywords: {keywords}",
        border_style="cyan"
    ))

    async def run_generation():
        try:
            # Initialize orchestrator
            config = get_config(ctx.obj['config_path'])
            orchestrator = BlogOrchestrator(config)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:

                # Step 1: Search
                task1 = progress.add_task("[cyan]Searching for articles...", total=100)
                search_result = await orchestrator.search_only(keywords)
                progress.update(task1, completed=100)

                console.print(f"[green]✓[/green] Found {search_result.get('total_found', 0)} results, "
                            f"selected {search_result.get('selected_count', 0)} articles")

                # Step 2: Plan
                task2 = progress.add_task("[cyan]Planning blog post...", total=100)
                plan_result = await orchestrator.plan_only()
                progress.update(task2, completed=100)

                console.print(f"[green]✓[/green] Generated outline with "
                            f"{len(plan_result.get('sections', []))} sections")

                # Step 3: Write
                task3 = progress.add_task("[cyan]Writing blog post...", total=100)
                write_result = await orchestrator.write_only()
                progress.update(task3, completed=100)

                console.print(f"[green]✓[/green] Blog written: {write_result.get('word_count', 0)} words")

            # Display results
            console.print("\n[bold green]✓ Blog generated successfully![/bold green]\n")

            result_table = Table(show_header=False, box=None)
            result_table.add_column("Key", style="cyan")
            result_table.add_column("Value", style="white")

            result_table.add_row("Title", plan_result.get('title', ''))
            result_table.add_row("File", write_result.get('filename', ''))
            result_table.add_row("Words", str(write_result.get('word_count', 0)))
            result_table.add_row("Sections", str(write_result.get('sections_count', 0)))
            result_table.add_row("Sources", str(search_result.get('selected_count', 0)))

            console.print(result_table)

        except Exception as e:
            console.print(f"[bold red]✗ Error:[/bold red] {e}")
            if verbose:
                console.print_exception()
            sys.exit(1)

    asyncio.run(run_generation())


@cli.command()
@click.option('--keywords', '-k', required=True, help='Search keywords')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def search_only(ctx, keywords, verbose):
    """Execute only the search step."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    console.print(f"[cyan]Searching for:[/cyan] {keywords}")

    async def run_search():
        try:
            config = get_config(ctx.obj['config_path'])
            orchestrator = BlogOrchestrator(config)

            with console.status("[cyan]Searching...", spinner="dots"):
                result = await orchestrator.search_only(keywords)

            # Display results
            console.print(f"\n[green]✓[/green] Found {result.get('total_found', 0)} results")
            console.print(f"[green]✓[/green] Selected {result.get('selected_count', 0)} articles")
            console.print(f"\nResults saved to: outputs/search_results.json")

            # Show top articles
            articles = result.get('selected_articles', [])
            if articles:
                console.print("\n[bold]Top Articles:[/bold]")
                for idx, article in enumerate(articles[:5], 1):
                    console.print(f"{idx}. {article['title']}")
                    console.print(f"   [dim]{article['url']}[/dim]")

        except Exception as e:
            console.print(f"[bold red]✗ Error:[/bold red] {e}")
            if verbose:
                console.print_exception()
            sys.exit(1)

    asyncio.run(run_search())


@cli.command()
@click.option('--file', '-f', default='references/reference.md', help='Reference file to analyze')
@click.pass_context
def analyze_tone(ctx, file):
    """Analyze tone from reference file."""
    console.print(f"[cyan]Analyzing tone from:[/cyan] {file}")

    try:
        config = get_config(ctx.obj['config_path'])
        tone_learner = ToneLearner(config)

        with console.status("[cyan]Analyzing...", spinner="dots"):
            profile = tone_learner.analyze_tone(file)

        # Display results
        console.print("\n[bold green]✓ Tone analysis completed![/bold green]\n")

        console.print("[bold]Characteristics:[/bold]")
        console.print(profile.get('characteristics', ''))

        console.print("\n[bold]Vocabulary:[/bold]")
        console.print(profile.get('vocabulary', ''))

        console.print("\n[bold]Patterns:[/bold]")
        console.print(profile.get('patterns', ''))

        console.print("\n[bold]Style:[/bold]")
        console.print(profile.get('style', ''))

    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        console.print_exception()
        sys.exit(1)


@cli.command()
@click.option('--workflow-id', '-w', required=True, help='Workflow ID to resume')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def resume(ctx, workflow_id, verbose):
    """Resume a workflow from checkpoint."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    console.print(f"[cyan]Resuming workflow:[/cyan] {workflow_id}")

    async def run_resume():
        try:
            config = get_config(ctx.obj['config_path'])
            orchestrator = BlogOrchestrator(config)

            # This would need the original keywords - in a real implementation,
            # we'd store this in the checkpoint
            console.print("[yellow]Note: Resume functionality requires original keywords[/yellow]")
            console.print("[yellow]Consider using individual step commands instead[/yellow]")

        except Exception as e:
            console.print(f"[bold red]✗ Error:[/bold red] {e}")
            if verbose:
                console.print_exception()
            sys.exit(1)

    asyncio.run(run_resume())


@cli.command()
@click.pass_context
def list_workflows(ctx):
    """List all workflow checkpoints."""
    from blog_agents.utils.file_manager import FileManager

    try:
        config = get_config(ctx.obj['config_path'])
        file_manager = FileManager(config.blog_agents.output_dir)

        checkpoints = file_manager.list_files("checkpoint_*.json")

        if not checkpoints:
            console.print("[yellow]No workflow checkpoints found[/yellow]")
            return

        console.print(f"\n[bold]Found {len(checkpoints)} workflow(s):[/bold]\n")

        for checkpoint_file in checkpoints:
            console.print(f"• {checkpoint_file.name}")

    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
def version():
    """Show version information."""
    console.print("[bold cyan]Blog Agents[/bold cyan] - Multi-Agent Blog Generation System")
    console.print("Version: 1.0.0")
    console.print("Python-based AI Agent System for Automated Blog Content Generation")


if __name__ == '__main__':
    cli(obj={})
