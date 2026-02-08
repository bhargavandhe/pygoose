"""
Pygoose with FastAPI Example

Demonstrates building a REST API with Pygoose and FastAPI.

Features covered:
- FastAPI integration
- Document models as request/response schemas
- Async MongoDB operations
- Exception handling
- Pagination

Run with:
  pip install uvicorn
  uvicorn example_fastapi:app --reload

Then visit: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from typing import Optional
from bson import ObjectId

from fastapi import FastAPI, HTTPException, Query
from pydantic import EmailStr

from pygoose import (
    Document,
    Ref,
    connect,
    disconnect,
    encryption,
    generate_encryption_key,
)
from pygoose.plugins import TimestampsMixin
from pygoose.integrations import init_app


# ============================================================================
# 1. DEFINE MODELS
# ============================================================================


class Author(TimestampsMixin, Document):
    """Blog author."""

    name: str
    email: str
    bio: Optional[str] = None

    class Settings:
        collection = "authors"


class BlogPost(TimestampsMixin, Document):
    """Blog post with timestamps."""

    title: str
    content: str
    author: Ref["Author"]
    published: bool = False
    tags: list[str] = []

    class Settings:
        collection = "blog_posts"


# ============================================================================
# 2. PYDANTIC SCHEMAS FOR API
# ============================================================================


class AuthorSchema:
    """API schema for author responses."""

    def __init__(self, author: Author):
        self.id = str(author.id)
        self.name = author.name
        self.email = author.email
        self.bio = author.bio

    def dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "bio": self.bio,
        }


class BlogPostSchema:
    """API schema for post responses."""

    def __init__(self, post: BlogPost, author: Optional[Author] = None):
        self.id = str(post.id)
        self.title = post.title
        self.content = post.content
        self.published = post.published
        self.tags = post.tags
        self.created_at = post.created_at
        self.updated_at = post.updated_at
        self.author = (
            AuthorSchema(author).dict() if author else None
        )

    def dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "published": self.published,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "author": self.author,
        }


# ============================================================================
# 3. APP LIFECYCLE
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown."""
    # Startup
    print("Starting up...")
    await connect("mongodb://localhost:27017/pygoose_api")
    encryption.set_key(generate_encryption_key())
    print("✅ Connected to MongoDB")
    yield
    # Shutdown
    print("Shutting down...")
    await disconnect()
    print("✅ Disconnected from MongoDB")


app = FastAPI(
    title="Pygoose Blog API",
    description="A blog API built with Pygoose and FastAPI",
    version="1.0.0",
    lifespan=lifespan,
)

# Initialize Pygoose with FastAPI
init_app(app)


# ============================================================================
# 4. AUTHOR ENDPOINTS
# ============================================================================


@app.post("/authors", tags=["Authors"])
async def create_author(name: str, email: str, bio: Optional[str] = None):
    """Create a new author."""
    author = await Author.create(name=name, email=email, bio=bio)
    return {
        "id": str(author.id),
        "name": author.name,
        "email": author.email,
        "message": "Author created successfully",
    }


@app.get("/authors/{author_id}", tags=["Authors"])
async def get_author(author_id: str):
    """Get author by ID."""
    try:
        author = await Author.get(ObjectId(author_id))
        return AuthorSchema(author).dict()
    except Exception:
        raise HTTPException(status_code=404, detail="Author not found")


@app.get("/authors", tags=["Authors"])
async def list_authors(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    """List all authors with pagination."""
    authors = await Author.find().skip(skip).limit(limit).all()
    total = await Author.find().count()

    return {
        "items": [AuthorSchema(a).dict() for a in authors],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@app.put("/authors/{author_id}", tags=["Authors"])
async def update_author(author_id: str, name: Optional[str] = None, bio: Optional[str] = None):
    """Update an author."""
    try:
        author = await Author.get(ObjectId(author_id))

        if name:
            author.name = name
        if bio:
            author.bio = bio

        await author.save()

        return {
            "message": "Author updated",
            "author": AuthorSchema(author).dict(),
        }
    except Exception:
        raise HTTPException(status_code=404, detail="Author not found")


@app.delete("/authors/{author_id}", tags=["Authors"])
async def delete_author(author_id: str):
    """Delete an author."""
    try:
        author = await Author.get(ObjectId(author_id))
        await author.delete()
        return {"message": "Author deleted successfully"}
    except Exception:
        raise HTTPException(status_code=404, detail="Author not found")


# ============================================================================
# 5. BLOG POST ENDPOINTS
# ============================================================================


@app.post("/posts", tags=["Posts"])
async def create_post(
    title: str,
    content: str,
    author_id: str,
    published: bool = False,
    tags: Optional[list[str]] = None,
):
    """Create a new blog post."""
    try:
        author = await Author.get(ObjectId(author_id))

        post = await BlogPost.create(
            title=title,
            content=content,
            author=Ref(Author, author.id),
            published=published,
            tags=tags or [],
        )

        return {
            "id": str(post.id),
            "title": post.title,
            "message": "Post created successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/posts/{post_id}", tags=["Posts"])
async def get_post(post_id: str):
    """Get a blog post with author details."""
    try:
        post = await BlogPost.get(ObjectId(post_id))
        await post.populate("author")
        return BlogPostSchema(post, post.author).dict()
    except Exception:
        raise HTTPException(status_code=404, detail="Post not found")


@app.get("/posts", tags=["Posts"])
async def list_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    published_only: bool = False,
):
    """List blog posts with pagination."""
    filter_dict = {"published": True} if published_only else {}

    posts = await BlogPost.find(filter_dict).skip(skip).limit(limit).all()
    total = await BlogPost.find(filter_dict).count()

    # Populate all authors efficiently
    if posts:
        for post in posts:
            await post.populate("author")

    return {
        "items": [BlogPostSchema(p, p.author).dict() for p in posts],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@app.put("/posts/{post_id}", tags=["Posts"])
async def update_post(
    post_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    published: Optional[bool] = None,
):
    """Update a blog post."""
    try:
        post = await BlogPost.get(ObjectId(post_id))

        if title:
            post.title = title
        if content:
            post.content = content
        if published is not None:
            post.published = published

        await post.save()

        await post.populate("author")
        return BlogPostSchema(post, post.author).dict()
    except Exception:
        raise HTTPException(status_code=404, detail="Post not found")


@app.delete("/posts/{post_id}", tags=["Posts"])
async def delete_post(post_id: str):
    """Delete a blog post."""
    try:
        post = await BlogPost.get(ObjectId(post_id))
        await post.delete()
        return {"message": "Post deleted successfully"}
    except Exception:
        raise HTTPException(status_code=404, detail="Post not found")


@app.post("/posts/{post_id}/publish", tags=["Posts"])
async def publish_post(post_id: str):
    """Publish a blog post."""
    try:
        post = await BlogPost.get(ObjectId(post_id))
        post.published = True
        await post.save()

        await post.populate("author")
        return {
            "message": "Post published",
            "post": BlogPostSchema(post, post.author).dict(),
        }
    except Exception:
        raise HTTPException(status_code=404, detail="Post not found")


# ============================================================================
# 6. SEARCH ENDPOINTS
# ============================================================================


@app.get("/posts/search/by-author/{author_id}", tags=["Search"])
async def posts_by_author(author_id: str, skip: int = 0, limit: int = 10):
    """Get all posts by a specific author."""
    try:
        author = await Author.get(ObjectId(author_id))

        posts = (
            await BlogPost.find({"author": author.id})
            .skip(skip)
            .limit(limit)
            .all()
        )

        total = await BlogPost.find({"author": author.id}).count()

        return {
            "author": AuthorSchema(author).dict(),
            "posts": [BlogPostSchema(p).dict() for p in posts],
            "total": total,
        }
    except Exception:
        raise HTTPException(status_code=404, detail="Author not found")


@app.get("/posts/search/by-tag/{tag}", tags=["Search"])
async def posts_by_tag(tag: str, skip: int = 0, limit: int = 10):
    """Get all posts with a specific tag."""
    posts = (
        await BlogPost.find({"tags": tag})
        .skip(skip)
        .limit(limit)
        .all()
    )

    total = await BlogPost.find({"tags": tag}).count()

    # Populate authors
    for post in posts:
        await post.populate("author")

    return {
        "tag": tag,
        "posts": [BlogPostSchema(p, p.author).dict() for p in posts],
        "total": total,
    }


# ============================================================================
# 7. STATISTICS ENDPOINTS
# ============================================================================


@app.get("/stats", tags=["Stats"])
async def get_stats():
    """Get blog statistics."""
    total_authors = await Author.find().count()
    total_posts = await BlogPost.find().count()
    published_posts = await BlogPost.find({"published": True}).count()

    return {
        "total_authors": total_authors,
        "total_posts": total_posts,
        "published_posts": published_posts,
        "draft_posts": total_posts - published_posts,
    }


# ============================================================================
# 8. HEALTH CHECK
# ============================================================================


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Pygoose Blog API",
    }


# ============================================================================
# 9. ROOT ENDPOINT
# ============================================================================


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Pygoose Blog API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "authors": "/authors",
            "posts": "/posts",
            "stats": "/stats",
        },
    }


# ============================================================================
# 10. EXAMPLE USAGE
# ============================================================================

"""
To use this API:

1. Start MongoDB:
   mongod

2. Run the server:
   uvicorn example_fastapi:app --reload

3. Visit interactive docs:
   http://localhost:8000/docs

4. Example requests:

   # Create an author
   POST /authors
   {
     "name": "Alice Johnson",
     "email": "alice@example.com",
     "bio": "Tech writer and blogger"
   }

   # Create a post
   POST /posts
   {
     "title": "Getting Started with Pygoose",
     "content": "Pygoose is...",
     "author_id": "<author_id>",
     "published": false,
     "tags": ["python", "mongodb"]
   }

   # Get all posts
   GET /posts?skip=0&limit=10

   # Get a specific post
   GET /posts/{post_id}

   # Update a post
   PUT /posts/{post_id}
   {
     "title": "New Title"
   }

   # Publish a post
   POST /posts/{post_id}/publish

   # Search by tag
   GET /posts/search/by-tag/python

   # Get stats
   GET /stats
"""
