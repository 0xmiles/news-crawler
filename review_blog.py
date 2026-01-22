"""Script to review existing blog post using BlogReviewer agent."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from blog_agents.config.agent_config import get_config
from blog_agents.agents.blog_reviewer import BlogReviewer
from blog_agents.utils.file_manager import FileManager


async def main():
    """Review existing blog post."""

    # Load configuration
    config = get_config("config.yaml")

    # Initialize BlogReviewer
    reviewer = BlogReviewer(config)

    # File to review
    blog_filename = "spring-boot-caffeine-cache-실전-캐싱-전략과-성능-최적화-2026-01-22.md"

    # Initialize file manager
    file_manager = FileManager(config.blog_agents.output_dir)

    # Read blog content
    print(f"📖 Reading blog file: {blog_filename}")
    blog_content = await file_manager.read_text(blog_filename)

    if not blog_content:
        print(f"❌ Error: Could not read file {blog_filename}")
        return

    # Extract sources from content
    sources = [
        {
            "title": "Spring Boot with Caffeine Cache",
            "url": "https://blog.yevgnenll.me/posts/spring-boot-with-caffeine-cache"
        },
        {
            "title": "캐시를 활용하여 부하를 줄이고 성능을 개선하자",
            "url": "https://velog.io/@komment/%EC%BA%90%EC%8B%9C%EB%A5%BC-%ED%99%9C%EC%9A%A9%ED%95%98%EC%97%AC-%EB%B6%80%ED%95%98%EB%A5%BC-%EC%A4%84%EC%9D%B4%EA%B3%A0-%EC%84%B1%EB%8A%A5%EC%9D%84-%EA%B0%9C%EC%84%A0%ED%95%98%EC%9E%90"
        },
        {
            "title": "Spring Boot Caffeine Cache 성능 최적화",
            "url": "https://80000coding.oopy.io/d2d626ba-6f4f-4684-8f4d-5603da6c3f56"
        }
    ]

    # Prepare input data
    input_data = {
        "title": "Spring Boot Caffeine Cache: 실전 캐싱 전략과 성능 최적화",
        "content": blog_content,
        "sources": sources,
        "filename": blog_filename
    }

    print("\n🔍 Starting blog review...")
    print("=" * 60)

    # Execute review
    result = await reviewer.run(input_data)

    if result.status.value == "completed":
        print("\n✅ Review completed successfully!")
        print("=" * 60)

        # Print corrections made
        corrections = result.data.get("corrections_made", [])
        if corrections:
            print(f"\n📝 Corrections made ({len(corrections)}):")
            for i, correction in enumerate(corrections[:10], 1):  # Show first 10
                print(f"  {i}. {correction}")
            if len(corrections) > 10:
                print(f"  ... and {len(corrections) - 10} more corrections")
        else:
            print("\n✨ No corrections needed!")

        # Print reliability score
        reliability_score = result.data.get("reliability_score", 0)
        print(f"\n📊 Reliability Score: {reliability_score:.2%}")

        # Print reliability notes
        reliability_notes = result.data.get("reliability_notes", [])
        if reliability_notes:
            print(f"\n📌 Reliability Notes ({len(reliability_notes)}):")
            for i, note in enumerate(reliability_notes[:5], 1):  # Show first 5
                print(f"  {i}. {note}")
            if len(reliability_notes) > 5:
                print(f"  ... and {len(reliability_notes) - 5} more notes")

        # Print learning result
        learning_result = result.data.get("learning_result", {})
        if learning_result:
            key_concepts = learning_result.get("key_concepts", [])
            print(f"\n🧠 Key Concepts Learned ({len(key_concepts)}):")
            for i, concept in enumerate(key_concepts[:5], 1):
                print(f"  {i}. {concept}")
            if len(key_concepts) > 5:
                print(f"  ... and {len(key_concepts) - 5} more concepts")

        print(f"\n💾 Reviewed blog saved to: outputs/{blog_filename}")
        print(f"📄 Review report saved to: outputs/review_report.json")

    else:
        print(f"\n❌ Review failed: {result.error}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
