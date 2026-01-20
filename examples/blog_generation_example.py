"""Example script for using Blog Agents system."""

import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

from blog_agents.config.agent_config import get_config
from blog_agents.core.orchestrator import BlogOrchestrator
from blog_agents.skills.tone_learner import ToneLearner

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def example_full_generation():
    """Example: Generate a complete blog post."""
    print("\n" + "="*60)
    print("Example 1: Full Blog Generation")
    print("="*60 + "\n")

    # Initialize orchestrator
    config = get_config()
    orchestrator = BlogOrchestrator(config)

    # Generate blog
    keywords = "Python asyncio best practices"
    logger.info(f"Generating blog for keywords: {keywords}")

    result = await orchestrator.generate_blog(keywords)

    print("\n✓ Blog generation completed!")
    print(f"  Title: {result['blog_plan']['title']}")
    print(f"  File: {result['blog_file']}")
    print(f"  Word Count: {result['word_count']}")
    print(f"  Sections: {result['sections_count']}")


async def example_step_by_step():
    """Example: Execute each step individually."""
    print("\n" + "="*60)
    print("Example 2: Step-by-Step Execution")
    print("="*60 + "\n")

    config = get_config()
    orchestrator = BlogOrchestrator(config)

    keywords = "Machine Learning in Production"

    # Step 1: Search
    print("Step 1: Searching for articles...")
    search_result = await orchestrator.search_only(keywords)
    print(f"  ✓ Found {search_result['total_found']} results")
    print(f"  ✓ Selected {search_result['selected_count']} articles")

    # Step 2: Plan
    print("\nStep 2: Planning blog post...")
    plan_result = await orchestrator.plan_only()
    print(f"  ✓ Title: {plan_result['title']}")
    print(f"  ✓ Sections: {len(plan_result['sections'])}")

    # Step 3: Write
    print("\nStep 3: Writing blog post...")
    write_result = await orchestrator.write_only()
    print(f"  ✓ Written: {write_result['word_count']} words")
    print(f"  ✓ Saved to: {write_result['filename']}")


def example_tone_analysis():
    """Example: Analyze tone from reference file."""
    print("\n" + "="*60)
    print("Example 3: Tone Analysis")
    print("="*60 + "\n")

    config = get_config()
    tone_learner = ToneLearner(config)

    # Analyze tone
    reference_file = "references/reference.md"
    print(f"Analyzing tone from: {reference_file}")

    tone_profile = tone_learner.analyze_tone(reference_file)

    print("\n✓ Tone Analysis Results:")
    print(f"\nCharacteristics:\n{tone_profile['characteristics']}")
    print(f"\nVocabulary:\n{tone_profile['vocabulary']}")
    print(f"\nPatterns:\n{tone_profile['patterns']}")
    print(f"\nStyle:\n{tone_profile['style']}")

    # Test tone application
    sample_text = """
    This is a sample paragraph. It demonstrates the basic functionality
    of our system. The implementation is straightforward and efficient.
    """

    print("\n\nApplying tone to sample text...")
    adjusted_text = tone_learner.apply_tone(sample_text)

    print(f"\nOriginal:\n{sample_text}")
    print(f"\nAdjusted:\n{adjusted_text}")

    # Validate tone match
    score = tone_learner.validate_tone_match(adjusted_text)
    print(f"\nTone match score: {score:.2f}")


async def example_with_custom_config():
    """Example: Using custom configuration."""
    print("\n" + "="*60)
    print("Example 4: Custom Configuration")
    print("="*60 + "\n")

    # Load custom config
    config = get_config("config.yaml")

    # Override specific settings
    config.blog_agents.target_blog_length = 2000
    config.blog_agents.post_searcher.max_articles = 5

    print(f"Target blog length: {config.blog_agents.target_blog_length}")
    print(f"Max articles to analyze: {config.blog_agents.post_searcher.max_articles}")

    # Generate blog with custom config
    orchestrator = BlogOrchestrator(config)
    result = await orchestrator.generate_blog("Cloud Computing Security")

    print(f"\n✓ Generated blog with custom settings")
    print(f"  Word count: {result['word_count']}")


async def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("Blog Agents - Usage Examples")
    print("="*60)

    # Example 1: Full generation (uncomment to run)
    # await example_full_generation()

    # Example 2: Step-by-step (uncomment to run)
    # await example_step_by_step()

    # Example 3: Tone analysis (uncomment to run)
    # example_tone_analysis()

    # Example 4: Custom config (uncomment to run)
    # await example_with_custom_config()

    print("\n" + "="*60)
    print("Examples completed!")
    print("Uncomment the examples you want to run in the main() function.")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
