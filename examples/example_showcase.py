"""
Comprehensive Pygoose Showcase Example

This example demonstrates all major features of Pygoose:
- CRUD operations
- QuerySet fluent API
- Type-safe document references
- Reference population
- Field-level encryption
- Lifecycle hooks
- Plugin system (timestamps, soft delete, audit)
- FastAPI integration
- Pagination

Run with: python example_showcase.py
"""

import asyncio
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import EmailStr

from pygoose import (
    Document,
    Ref,
    Encrypted,
    connect,
    disconnect,
    encryption,
    generate_encryption_key,
)
from pygoose.plugins import TimestampsMixin, SoftDeleteMixin, AuditMixin
from pygoose.lifecycle.hooks import pre_save, post_save, pre_delete
from pygoose.integrations import init_app
from pygoose.utils.pagination import Page


# ============================================================================
# 1. DEFINE DOCUMENTS WITH VARIOUS FEATURES
# ============================================================================


class User(TimestampsMixin, AuditMixin, Document):
    """User document with timestamps and audit trail.

    Features demonstrated:
    - Timestamps plugin (created_at, updated_at)
    - Audit mixin (tracks who modified)
    - Encrypted email field
    - Lifecycle hooks
    """

    name: str
    email: Encrypted[str]
    age: Optional[int] = None
    is_active: bool = True

    class Settings:
        collection = "users"


class Post(SoftDeleteMixin, TimestampsMixin, Document):
    """Blog post with soft delete and timestamps.

    Features demonstrated:
    - Soft delete mixin (is_deleted flag)
    - Timestamps plugin
    - References to other documents
    - Dirty field tracking
    """

    title: str
    content: str
    author: Ref["User"]
    tags: List[str] = []
    views: int = 0

    class Settings:
        collection = "posts"


class Comment(Document):
    """Comment on a post.

    Features demonstrated:
    - Nested references (Post -> User)
    - Lifecycle hooks
    """

    text: str
    author: Ref["User"]
    post: Ref["Post"]
    likes: int = 0

    class Settings:
        collection = "comments"

    @pre_save
    async def validate_comment(self):
        """Hook: Validate comment before saving."""
        if len(self.text) < 3:
            raise ValueError("Comment must be at least 3 characters")


class Product(Document):
    """E-commerce product with indexed fields."""

    name: str
    price: float
    stock: int
    description: Optional[str] = None
    seller: Ref["User"]

    class Settings:
        collection = "products"
        indexes = [
            {"keys": [("name", 1)], "unique": False},
            {"keys": [("seller", 1)], "unique": False},
        ]


# ============================================================================
# 2. LIFECYCLE HOOKS
# ============================================================================


@pre_save(User)
async def encrypt_user_email(user: User):
    """Hook: Log before saving user."""
    print(f"  [HOOK] Pre-saving user: {user.name}")


@post_save(User)
async def log_user_saved(user: User):
    """Hook: Log after saving user."""
    print(f"  [HOOK] User saved successfully: {user.id}")


@pre_delete(Post)
async def log_post_delete(post: Post):
    """Hook: Log before deleting post."""
    print(f"  [HOOK] Deleting post: {post.title}")


# ============================================================================
# 3. EXAMPLE WORKFLOWS
# ============================================================================


async def example_1_basic_crud():
    """Example 1: Basic CRUD Operations"""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic CRUD Operations")
    print("=" * 70)

    # CREATE
    print("\n1️⃣  Creating a user...")
    user = await User.create(
        name="Alice Johnson",
        email="alice@example.com",
        age=28,
    )
    print(f"   Created user: {user.name} (ID: {user.id})")

    # READ
    print("\n2️⃣  Reading user by ID...")
    fetched_user = await User.get(user.id)
    print(f"   Fetched: {fetched_user.name}, Age: {fetched_user.age}")

    # UPDATE
    print("\n3️⃣  Updating user (dirty tracking)...")
    fetched_user.age = 29
    print(f"   Dirty fields: {fetched_user.dirty_fields}")
    await fetched_user.save()
    print(f"   Saved! New age: {fetched_user.age}")

    # DELETE
    print("\n4️⃣  Deleting user...")
    await user.delete()
    print(f"   User deleted!")

    return user


async def example_2_queryset_api():
    """Example 2: QuerySet Fluent API"""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: QuerySet Fluent API")
    print("=" * 70)

    # Create test users
    print("\n1️⃣  Creating test users...")
    users = []
    for i in range(5):
        user = await User.create(
            name=f"User {i}",
            email=f"user{i}@example.com",
            age=20 + i,
        )
        users.append(user)
        print(f"   Created: {user.name} (age {user.age})")

    # FIND
    print("\n2️⃣  Find all users...")
    all_users = await User.find().all()
    print(f"   Found {len(all_users)} users")

    # FIND WITH FILTER
    print("\n3️⃣  Find users aged 22 or older...")
    older_users = await User.find(age={"$gte": 22}).all()
    print(f"   Found {len(older_users)} users: {[u.name for u in older_users]}")

    # FIND_ONE
    print("\n4️⃣  Find first user named 'User 2'...")
    user = await User.find_one(name="User 2")
    print(f"   Found: {user.name if user else 'Not found'}")

    # COUNT
    print("\n5️⃣  Count users...")
    count = await User.find().count()
    print(f"   Total users: {count}")

    # EXISTS
    print("\n6️⃣  Check if user exists...")
    exists = await User.find(name="User 1").exists()
    print(f"   User 1 exists: {exists}")

    # SORT & LIMIT
    print("\n7️⃣  Find users sorted by age, limit 2...")
    top_users = await User.find().sort("age", -1).limit(2).all()
    print(f"   Top 2 by age: {[(u.name, u.age) for u in top_users]}")

    # PAGINATION
    print("\n8️⃣  Paginate through users (page size 2)...")
    page = await User.find().paginate(page=1, page_size=2)
    print(f"   Page 1: {[u.name for u in page.items]} (total: {page.total})")

    return users


async def example_3_references_population():
    """Example 3: References and Population"""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: References and Population")
    print("=" * 70)

    # Create author
    print("\n1️⃣  Creating author...")
    author = await User.create(name="Bob Smith", email="bob@example.com")
    print(f"   Author: {author.name}")

    # Create posts referencing the author
    print("\n2️⃣  Creating posts...")
    posts = []
    for i in range(3):
        post = await Post.create(
            title=f"Post {i}",
            content=f"Content of post {i}",
            author=Ref(User, author.id),
            tags=["python", "mongodb"],
        )
        posts.append(post)
        print(f"   Created: {post.title}")

    # Load without population (reference is ObjectId)
    print("\n3️⃣  Fetch post without population...")
    post = await Post.get(posts[0].id)
    print(f"   Post: {post.title}")
    print(f"   Author (unpopulated): {post.author} (type: {type(post.author).__name__})")

    # Load with population (reference is full document)
    print("\n4️⃣  Fetch post WITH population...")
    populated_post = await Post.get(posts[0].id)
    await populated_post.populate("author")
    print(f"   Post: {populated_post.title}")
    print(f"   Author (populated): {populated_post.author.name}")

    # Batch population (efficient)
    print("\n5️⃣  Batch populate multiple posts...")
    all_posts = await Post.find().all()
    await Post.find().populate("author").all()
    print(f"   Populated {len(all_posts)} posts")

    # Nested population (Post -> Comment -> User)
    print("\n6️⃣  Create comments and nested populate...")
    comment = await Comment.create(
        text="Great post!",
        author=Ref(User, author.id),
        post=Ref(Post, posts[0].id),
    )
    await comment.populate("author", "post")
    print(f"   Comment: {comment.text}")
    print(f"   By: {comment.author.name}")
    print(f"   On: {comment.post.title}")

    # Deep nested population
    print("\n7️⃣  Deep nested population (Post -> User)...")
    deep_post = await Post.get(posts[0].id)
    await deep_post.populate("author")
    print(f"   Post author: {deep_post.author.name} ({deep_post.author.email})")

    return posts, author


async def example_4_encryption():
    """Example 4: Field-Level Encryption"""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Field-Level Encryption")
    print("=" * 70)

    # Generate and set encryption key
    print("\n1️⃣  Setting up encryption...")
    key = generate_encryption_key()
    encryption.set_key(key)
    print(f"   Encryption key set")

    # Create user with encrypted email
    print("\n2️⃣  Creating user with encrypted email...")
    user = await User.create(
        name="Charlie Brown",
        email="charlie@example.com",
    )
    print(f"   User created: {user.name}")

    # Check raw data in database (encrypted)
    print("\n3️⃣  Raw data in database (encrypted)...")
    raw = await User.get_collection().find_one({"_id": user.id})
    print(f"   Stored email (encrypted): {raw['email'][:30]}...")

    # Load and decrypt
    print("\n4️⃣  Loading user (auto-decrypted)...")
    loaded = await User.get(user.id)
    print(f"   User email (decrypted): {loaded.email}")

    # Update encrypted field
    print("\n5️⃣  Updating encrypted field...")
    loaded.email = "charlie.new@example.com"
    await loaded.save()
    print(f"   Email updated and encrypted")

    # Cannot query encrypted fields by plaintext
    print("\n6️⃣  Encrypted fields are not queryable...")
    result = await User.find_one(email="charlie.new@example.com")
    print(f"   Find by plaintext: {result} (None because encrypted)")

    return user


async def example_5_lifecycle_hooks():
    """Example 5: Lifecycle Hooks"""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Lifecycle Hooks")
    print("=" * 70)

    print("\n1️⃣  Creating user (triggers pre_save and post_save)...")
    user = await User.create(name="Diana Prince", email="diana@example.com")
    print(f"   User created successfully")

    print("\n2️⃣  Updating user (triggers hooks)...")
    user.age = 30
    await user.save()
    print(f"   User updated")

    print("\n3️⃣  Creating invalid comment (triggers pre_save validation)...")
    try:
        comment = Comment(text="x", author=Ref(User, user.id), post=Ref(Post, None))
        await comment.insert()
    except ValueError as e:
        print(f"   ❌ Validation error: {e}")

    print("\n4️⃣  Creating valid comment...")
    comment = Comment(text="Great content!", author=Ref(User, user.id), post=Ref(Post, None))
    # Note: Not inserting to avoid foreign key issues in this demo
    print(f"   Comment ready (not inserted)")


async def example_6_soft_delete():
    """Example 6: Soft Delete Plugin"""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Soft Delete Plugin")
    print("=" * 70)

    # Create author for posts
    author = await User.create(name="Eve Adams", email="eve@example.com")

    print("\n1️⃣  Creating posts...")
    post1 = await Post.create(
        title="Post 1",
        content="Content 1",
        author=Ref(User, author.id),
    )
    post2 = await Post.create(
        title="Post 2",
        content="Content 2",
        author=Ref(User, author.id),
    )
    print(f"   Created 2 posts")

    print("\n2️⃣  Finding all active posts...")
    active = await Post.find().all()
    print(f"   Active posts: {len(active)}")

    print("\n3️⃣  Soft deleting post 1...")
    await post1.delete()  # Sets is_deleted=True
    print(f"   Post soft-deleted")

    print("\n4️⃣  Querying active posts (soft-deleted excluded)...")
    active = await Post.find().all()
    print(f"   Active posts: {len(active)} (post 1 excluded)")

    print("\n5️⃣  Querying with include_deleted...")
    all_posts = await Post.find().include_deleted().all()
    print(f"   All posts (including deleted): {len(all_posts)}")


async def example_7_timestamps():
    """Example 7: Timestamps Plugin"""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Timestamps Plugin")
    print("=" * 70)

    print("\n1️⃣  Creating user...")
    user = await User.create(name="Frank Castle", email="frank@example.com")
    print(f"   User: {user.name}")
    print(f"   Created at: {user.created_at}")
    print(f"   Updated at: {user.updated_at}")

    print("\n2️⃣  Waiting 1 second and updating...")
    await asyncio.sleep(1)
    user.age = 35
    await user.save()
    print(f"   Updated at: {user.updated_at}")

    print("\n3️⃣  Fetching from database...")
    fetched = await User.get(user.id)
    print(f"   Created at: {fetched.created_at}")
    print(f"   Updated at: {fetched.updated_at}")
    print(f"   Updated > Created: {fetched.updated_at > fetched.created_at}")


async def example_8_dirty_tracking():
    """Example 8: Dirty Field Tracking"""
    print("\n" + "=" * 70)
    print("EXAMPLE 8: Dirty Field Tracking")
    print("=" * 70)

    print("\n1️⃣  Creating user...")
    user = await User.create(
        name="Grace Hopper",
        email="grace@example.com",
        age=25,
    )
    print(f"   Dirty fields: {user.dirty_fields}")

    print("\n2️⃣  Loading from database...")
    loaded = await User.get(user.id)
    print(f"   Is new: {loaded._is_new}")
    print(f"   Dirty fields: {loaded.dirty_fields}")

    print("\n3️⃣  Modifying multiple fields...")
    loaded.name = "Grace M. Hopper"
    loaded.age = 26
    print(f"   Dirty fields: {loaded.dirty_fields}")

    print("\n4️⃣  Saving only dirty fields...")
    await loaded.save()  # Uses $set with only dirty fields
    print(f"   Dirty fields: {loaded.dirty_fields}")


async def example_9_pagination():
    """Example 9: Pagination"""
    print("\n" + "=" * 70)
    print("EXAMPLE 9: Pagination")
    print("=" * 70)

    print("\n1️⃣  Creating 10 test users...")
    for i in range(10):
        await User.create(
            name=f"User {i:02d}",
            email=f"user{i:02d}@example.com",
            age=20 + i,
        )
    print(f"   Created 10 users")

    print("\n2️⃣  Paginating (page 1, size 3)...")
    page1 = await User.find().paginate(page=1, page_size=3)
    print(f"   Page 1: {[u.name for u in page1.items]}")
    print(f"   Total: {page1.total}, Pages: {page1.pages}")

    print("\n3️⃣  Paginating (page 2, size 3)...")
    page2 = await User.find().paginate(page=2, page_size=3)
    print(f"   Page 2: {[u.name for u in page2.items]}")

    print("\n4️⃣  Paginating with sort...")
    page = await User.find().sort("age", -1).paginate(page=1, page_size=3)
    print(f"   Oldest users: {[(u.name, u.age) for u in page.items]}")


# ============================================================================
# 4. FASTAPI INTEGRATION
# ============================================================================


def create_fastapi_app():
    """Create FastAPI app with Pygoose integration."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage app lifecycle."""
        # Startup
        await connect("mongodb://localhost:27017/pygoose_demo")
        encryption.set_key(generate_encryption_key())
        print("✅ Connected to MongoDB")
        yield
        # Shutdown
        await disconnect()
        print("✅ Disconnected from MongoDB")

    app = FastAPI(title="Pygoose API Demo", lifespan=lifespan)
    init_app(app)

    # ==================== ROUTES ====================

    @app.post("/users", response_model=dict)
    async def create_user(name: str, email: str, age: Optional[int] = None):
        """Create a new user."""
        user = await User.create(name=name, email=email, age=age)
        return {"id": str(user.id), "name": user.name}

    @app.get("/users/{user_id}")
    async def get_user(user_id: str):
        """Get user by ID."""
        from bson import ObjectId

        user = await User.get(ObjectId(user_id))
        return {
            "id": str(user.id),
            "name": user.name,
            "age": user.age,
            "created_at": user.created_at,
        }

    @app.get("/users")
    async def list_users(skip: int = 0, limit: int = 10):
        """List users with pagination."""
        page = await User.find().skip(skip).limit(limit).all()
        total = await User.find().count()
        return {
            "items": [{"id": str(u.id), "name": u.name} for u in page],
            "total": total,
        }

    @app.post("/posts/{user_id}")
    async def create_post(user_id: str, title: str, content: str):
        """Create a post by user."""
        from bson import ObjectId

        post = await Post.create(
            title=title,
            content=content,
            author=Ref(User, ObjectId(user_id)),
        )
        return {"id": str(post.id), "title": post.title}

    @app.get("/posts/{post_id}")
    async def get_post(post_id: str):
        """Get post with author populated."""
        from bson import ObjectId

        post = await Post.get(ObjectId(post_id))
        await post.populate("author")
        return {
            "id": str(post.id),
            "title": post.title,
            "content": post.content,
            "author": {
                "id": str(post.author.id),
                "name": post.author.name,
            },
            "views": post.views,
        }

    return app


# ============================================================================
# 5. MAIN EXECUTION
# ============================================================================


async def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "PYGOOSE - COMPREHENSIVE SHOWCASE" + " " * 21 + "║")
    print("╚" + "═" * 68 + "╝")

    # Connect to MongoDB
    try:
        await connect("mongodb://localhost:27017/pygoose_demo")
        print("\n✅ Connected to MongoDB")
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("   Make sure MongoDB is running on localhost:27017")
        return

    # Set up encryption
    encryption.set_key(generate_encryption_key())
    print("✅ Encryption configured")

    try:
        # Run examples
        await example_1_basic_crud()
        await example_2_queryset_api()
        await example_3_references_population()
        await example_4_encryption()
        await example_5_lifecycle_hooks()
        await example_6_soft_delete()
        await example_7_timestamps()
        await example_8_dirty_tracking()
        await example_9_pagination()

        print("\n" + "=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70)

        print("\n" + "=" * 70)
        print("FastAPI Example")
        print("=" * 70)
        print("\nTo start the FastAPI server, run:")
        print("  python -c \"from example_showcase import create_fastapi_app; \\")
        print("  import uvicorn; \\")
        print("  app = create_fastapi_app(); \\")
        print("  uvicorn.run(app, host='0.0.0.0', port=8000)\"")
        print("\nThen visit:")
        print("  - API Docs: http://localhost:8000/docs")
        print("  - ReDoc: http://localhost:8000/redoc")

    finally:
        await disconnect()
        print("\n✅ Disconnected from MongoDB")


if __name__ == "__main__":
    asyncio.run(main())
