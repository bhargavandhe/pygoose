"""
Pygoose Quick Start Example

A simple example to get you started with Pygoose in 5 minutes.

Features covered:
- Define documents
- CRUD operations
- Querying
- References

Run with: python example_quickstart.py
"""

import asyncio
from typing import Optional

from pygoose import Document, Ref, connect, disconnect


# ============================================================================
# 1. DEFINE YOUR DOCUMENTS
# ============================================================================


class Author(Document):
    """An author of blog posts."""

    name: str
    email: str

    class Settings:
        collection = "authors"


class BlogPost(Document):
    """A blog post with a reference to an author."""

    title: str
    content: str
    author: Ref["Author"]
    views: int = 0

    class Settings:
        collection = "blog_posts"


# ============================================================================
# 2. ASYNC MAIN FUNCTION
# ============================================================================


async def main():
    """Run the quickstart example."""

    # Connect to MongoDB
    await connect("mongodb://localhost:27017/pygoose_demo")
    print("✅ Connected to MongoDB\n")

    try:
        # ====== CREATE ======
        print("1️⃣  CREATE - Adding an author")
        author = await Author.create(
            name="Alice Johnson",
            email="alice@example.com",
        )
        print(f"   Created author: {author.name} (ID: {author.id})")

        # ====== CREATE WITH REFERENCE ======
        print("\n2️⃣  CREATE - Adding a blog post with author reference")
        post = await BlogPost.create(
            title="Getting Started with Pygoose",
            content="Pygoose is an async MongoDB ODM for Python...",
            author=Ref(Author, author.id),
        )
        print(f"   Created post: {post.title}")

        # ====== READ ======
        print("\n3️⃣  READ - Fetching the post by ID")
        fetched_post = await BlogPost.get(post.id)
        print(f"   Title: {fetched_post.title}")
        print(f"   Views: {fetched_post.views}")

        # ====== POPULATE REFERENCE ======
        print("\n4️⃣  POPULATE - Loading the author reference")
        await fetched_post.populate("author")
        print(f"   Author: {fetched_post.author.name}")
        print(f"   Email: {fetched_post.author.email}")

        # ====== UPDATE ======
        print("\n5️⃣  UPDATE - Incrementing view count")
        fetched_post.views = 42
        await fetched_post.save()
        print(f"   Updated views: {fetched_post.views}")

        # ====== QUERY ======
        print("\n6️⃣  QUERY - Finding all posts")
        all_posts = await BlogPost.find().all()
        print(f"   Found {len(all_posts)} posts")

        # ====== QUERY WITH FILTER ======
        print("\n7️⃣  QUERY - Finding posts with >20 views")
        popular = await BlogPost.find(views={"$gte": 20}).all()
        print(f"   Found {len(popular)} popular posts")

        # ====== COUNT ======
        print("\n8️⃣  COUNT - Total posts in database")
        count = await BlogPost.find().count()
        print(f"   Total posts: {count}")

        # ====== DELETE ======
        print("\n9️⃣  DELETE - Removing a post")
        await fetched_post.delete()
        print(f"   Post deleted")

        # ====== VERIFY DELETION ======
        print("\n🔟 VERIFY - Checking deletion")
        remaining = await BlogPost.find().count()
        print(f"   Remaining posts: {remaining}")

        print("\n✅ All operations completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Always disconnect
        await disconnect()
        print("\n✅ Disconnected from MongoDB")


# ============================================================================
# 3. RUN THE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PYGOOSE QUICKSTART EXAMPLE")
    print("=" * 60 + "\n")

    asyncio.run(main())
