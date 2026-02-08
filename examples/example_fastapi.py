"""
Pygoose with FastAPI Example

Demonstrates building a production-ready REST API with Pygoose and FastAPI.

Features covered:
- FastAPI integration with proper Pydantic models
- Request/response schemas with OpenAPI docs
- ObjectId handling and validation
- Async MongoDB operations
- Exception handling
- Pagination
- Reference population

Run with:
  uv add fastapi uvicorn
  uv run uvicorn example_fastapi:app --reload

Then visit: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Optional

from bson import ObjectId
from fastapi import Body, FastAPI, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field, field_validator

from pygoose import Document, Ref, connect, disconnect
from pygoose.plugins import TimestampsMixin
from pygoose.utils.exceptions import DocumentNotFound


# ============================================================================
# 1. DOCUMENT MODELS
# ============================================================================


class Author(TimestampsMixin, Document):
    """Blog author document."""

    name: str
    email: str
    bio: Optional[str] = None

    class Settings:
        collection = "authors"


class BlogPost(TimestampsMixin, Document):
    """Blog post document with author reference."""

    title: str
    content: str
    author: Ref["Author"]
    published: bool = False
    tags: list[str] = []
    views: int = 0

    class Settings:
        collection = "blog_posts"


# ============================================================================
# 2. PYDANTIC REQUEST/RESPONSE SCHEMAS
# ============================================================================

# Note: Pygoose's PyObjectId already handles JSON serialization automatically,
# converting ObjectId -> string in JSON mode and preserving ObjectId in Python mode.
# You can use model_dump(mode="json") to get string IDs for API responses.


# Author Schemas
class AuthorCreate(BaseModel):
    """Request schema for creating an author."""

    name: str = Field(..., min_length=1, max_length=100,
                      description="Author's name")
    email: str = Field(..., description="Author's email address")
    bio: Optional[str] = Field(
        None, max_length=500, description="Author biography")


class AuthorUpdate(BaseModel):
    """Request schema for updating an author."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=500)


class AuthorResponse(BaseModel):
    """Response schema for author data."""

    id: str = Field(..., description="Author ID")
    name: str
    email: str
    bio: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_document(cls, doc: Author) -> "AuthorResponse":
        # Use Pygoose's built-in JSON serialization
        data = doc.model_dump(mode="json")
        return cls(
            id=data["id"],  # PyObjectId already serialized to string
            name=data["name"],
            email=data["email"],
            bio=data.get("bio"),
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )


# BlogPost Schemas
class BlogPostCreate(BaseModel):
    """Request schema for creating a blog post."""

    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    author_id: str = Field(..., description="Author's ObjectId")
    published: bool = False
    tags: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("author_id")
    @classmethod
    def validate_author_id(cls, v: str) -> str:
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid author_id format")
        return v


class BlogPostUpdate(BaseModel):
    """Request schema for updating a blog post."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    published: Optional[bool] = None
    tags: Optional[list[str]] = Field(None, max_length=10)


class BlogPostResponse(BaseModel):
    """Response schema for blog post data."""

    id: str
    title: str
    content: str
    author_id: str
    published: bool
    tags: list[str]
    views: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    author: Optional[AuthorResponse] = None

    @classmethod
    def from_document(cls, doc: BlogPost, populate_author: bool = False) -> "BlogPostResponse":
        author_response = None
        if populate_author and isinstance(doc.author, Author):
            author_response = AuthorResponse.from_document(doc.author)

        return cls(
            id=str(doc.id),
            title=doc.title,
            content=doc.content,
            author_id=str(doc.author.id if isinstance(
                doc.author, Author) else doc.author),
            published=doc.published,
            tags=doc.tags,
            views=doc.views,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            author=author_response,
        )


# Pagination Schemas
class PaginatedResponse(BaseModel):
    """Generic paginated response."""

    items: list
    total: int
    skip: int
    limit: int
    has_more: bool


class AuthorListResponse(BaseModel):
    """Paginated author list response."""

    items: list[AuthorResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


class BlogPostListResponse(BaseModel):
    """Paginated blog post list response."""

    items: list[BlogPostResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


# Generic Response Schemas
class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    details: Optional[dict] = None


class StatsResponse(BaseModel):
    """Statistics response."""

    total_authors: int
    total_posts: int
    published_posts: int
    draft_posts: int


# ============================================================================
# 3. APP LIFECYCLE
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage MongoDB connection lifecycle."""
    # Startup
    print("🚀 Starting Pygoose Blog API...")
    await connect("mongodb://localhost:27017/pygoose_api")
    print("✅ Connected to MongoDB")
    yield
    # Shutdown
    print("🛑 Shutting down...")
    await disconnect()
    print("✅ Disconnected from MongoDB")


app = FastAPI(
    title="Pygoose Blog API",
    description="A production-ready blog API built with Pygoose and FastAPI",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================================
# 3.5. EXCEPTION HANDLERS
# ============================================================================


@app.exception_handler(DocumentNotFound)
async def document_not_found_handler(request: Request, exc: DocumentNotFound):
    """Handle DocumentNotFound exceptions by returning 404."""
    raise HTTPException(status_code=404, detail=str(exc))


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors by returning 422."""
    raise HTTPException(status_code=422, detail=str(exc))


# ============================================================================
# 4. AUTHOR ENDPOINTS
# ============================================================================


@app.post(
    "/authors",
    response_model=AuthorResponse,
    status_code=201,
    tags=["Authors"],
    summary="Create a new author",
)
async def create_author(data: AuthorCreate) -> AuthorResponse:
    """Create a new author with the provided information."""
    author = await Author.create(
        name=data.name,
        email=data.email,
        bio=data.bio,
    )
    return AuthorResponse.from_document(author)


@app.get(
    "/authors/{author_id}",
    response_model=AuthorResponse,
    tags=["Authors"],
    summary="Get author by ID",
)
async def get_author(
    author_id: Annotated[str, Path(description="Author's ObjectId")]
) -> AuthorResponse:
    """Retrieve a single author by their ID."""
    if not ObjectId.is_valid(author_id):
        raise HTTPException(status_code=400, detail="Invalid author_id format")

    author = await Author.get(ObjectId(author_id))  # Raises DocumentNotFound if not found
    return AuthorResponse.from_document(author)


@app.get(
    "/authors",
    response_model=AuthorListResponse,
    tags=["Authors"],
    summary="List all authors",
)
async def list_authors(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> AuthorListResponse:
    """List all authors with pagination."""
    authors = await Author.find().skip(skip).limit(limit).all()
    total = await Author.find().count()

    return AuthorListResponse(
        items=[AuthorResponse.from_document(a) for a in authors],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total,
    )


@app.put(
    "/authors/{author_id}",
    response_model=AuthorResponse,
    tags=["Authors"],
    summary="Update an author",
)
async def update_author(
    author_id: Annotated[str, Path(description="Author's ObjectId")],
    data: AuthorUpdate,
) -> AuthorResponse:
    """Update an existing author's information."""
    if not ObjectId.is_valid(author_id):
        raise HTTPException(status_code=400, detail="Invalid author_id format")

    author = await Author.get(ObjectId(author_id))  # Raises DocumentNotFound if not found

    # Update only provided fields
    if data.name is not None:
        author.name = data.name
    if data.email is not None:
        author.email = data.email
    if data.bio is not None:
        author.bio = data.bio

    await author.save()
    return AuthorResponse.from_document(author)


@app.delete(
    "/authors/{author_id}",
    response_model=MessageResponse,
    tags=["Authors"],
    summary="Delete an author",
)
async def delete_author(
    author_id: Annotated[str, Path(description="Author's ObjectId")]
) -> MessageResponse:
    """Delete an author by their ID."""
    if not ObjectId.is_valid(author_id):
        raise HTTPException(status_code=400, detail="Invalid author_id format")

    author = await Author.get(ObjectId(author_id))  # Raises DocumentNotFound if not found

    # Check if author has posts
    post_count = await BlogPost.find({"author": author.id}).count()
    if post_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete author with {post_count} existing posts",
        )

    await author.delete()
    return MessageResponse(message="Author deleted successfully")


# ============================================================================
# 5. BLOG POST ENDPOINTS
# ============================================================================


@app.post(
    "/posts",
    response_model=BlogPostResponse,
    status_code=201,
    tags=["Posts"],
    summary="Create a new blog post",
)
async def create_post(data: BlogPostCreate) -> BlogPostResponse:
    """Create a new blog post."""
    # Verify author exists
    author = await Author.get(ObjectId(data.author_id))
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    # Create post with author reference (just pass the ObjectId)
    post = await BlogPost.create(
        title=data.title,
        content=data.content,
        author=author.id,  # Pass ObjectId directly, not Ref(Author, author.id)
        published=data.published,
        tags=data.tags,
    )

    return BlogPostResponse.from_document(post)


@app.get(
    "/posts/{post_id}",
    response_model=BlogPostResponse,
    tags=["Posts"],
    summary="Get blog post by ID",
)
async def get_post(
    post_id: Annotated[str, Path(description="Post's ObjectId")],
    populate: Annotated[bool, Query(
        description="Populate author details")] = True,
) -> BlogPostResponse:
    """Retrieve a single blog post by ID, optionally with author details."""
    if not ObjectId.is_valid(post_id):
        raise HTTPException(status_code=400, detail="Invalid post_id format")

    post = await BlogPost.get(ObjectId(post_id))  # Raises DocumentNotFound if not found

    if populate:
        await post.populate("author")

    return BlogPostResponse.from_document(post, populate_author=populate)


@app.get(
    "/posts",
    response_model=BlogPostListResponse,
    tags=["Posts"],
    summary="List all blog posts",
)
async def list_posts(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    published_only: Annotated[bool, Query(
        description="Show only published posts")] = False,
    populate: Annotated[bool, Query(
        description="Populate author details")] = True,
) -> BlogPostListResponse:
    """List all blog posts with pagination and optional filtering."""
    filter_dict = {"published": True} if published_only else {}

    posts = await BlogPost.find(filter_dict).skip(skip).limit(limit).all()
    total = await BlogPost.find(filter_dict).count()

    # Populate authors if requested
    if populate and posts:
        for post in posts:
            await post.populate("author")

    return BlogPostListResponse(
        items=[BlogPostResponse.from_document(
            p, populate_author=populate) for p in posts],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total,
    )


@app.put(
    "/posts/{post_id}",
    response_model=BlogPostResponse,
    tags=["Posts"],
    summary="Update a blog post",
)
async def update_post(
    post_id: Annotated[str, Path(description="Post's ObjectId")],
    data: BlogPostUpdate,
) -> BlogPostResponse:
    """Update an existing blog post."""
    if not ObjectId.is_valid(post_id):
        raise HTTPException(status_code=400, detail="Invalid post_id format")

    post = await BlogPost.get(ObjectId(post_id))  # Raises DocumentNotFound if not found

    # Update only provided fields
    if data.title is not None:
        post.title = data.title
    if data.content is not None:
        post.content = data.content
    if data.published is not None:
        post.published = data.published
    if data.tags is not None:
        post.tags = data.tags

    await post.save()
    await post.populate("author")

    return BlogPostResponse.from_document(post, populate_author=True)


@app.delete(
    "/posts/{post_id}",
    response_model=MessageResponse,
    tags=["Posts"],
    summary="Delete a blog post",
)
async def delete_post(
    post_id: Annotated[str, Path(description="Post's ObjectId")]
) -> MessageResponse:
    """Delete a blog post by ID."""
    if not ObjectId.is_valid(post_id):
        raise HTTPException(status_code=400, detail="Invalid post_id format")

    post = await BlogPost.get(ObjectId(post_id))  # Raises DocumentNotFound if not found

    await post.delete()
    return MessageResponse(message="Post deleted successfully")


@app.post(
    "/posts/{post_id}/publish",
    response_model=BlogPostResponse,
    tags=["Posts"],
    summary="Publish a blog post",
)
async def publish_post(
    post_id: Annotated[str, Path(description="Post's ObjectId")]
) -> BlogPostResponse:
    """Publish a draft blog post."""
    if not ObjectId.is_valid(post_id):
        raise HTTPException(status_code=400, detail="Invalid post_id format")

    post = await BlogPost.get(ObjectId(post_id))  # Raises DocumentNotFound if not found

    if post.published:
        raise HTTPException(
            status_code=400, detail="Post is already published")

    post.published = True
    await post.save()
    await post.populate("author")

    return BlogPostResponse.from_document(post, populate_author=True)


@app.post(
    "/posts/{post_id}/view",
    response_model=MessageResponse,
    tags=["Posts"],
    summary="Increment post view count",
)
async def increment_view_count(
    post_id: Annotated[str, Path(description="Post's ObjectId")]
) -> MessageResponse:
    """Increment the view count for a blog post."""
    if not ObjectId.is_valid(post_id):
        raise HTTPException(status_code=400, detail="Invalid post_id format")

    post = await BlogPost.get(ObjectId(post_id))  # Raises DocumentNotFound if not found

    post.views += 1
    await post.save()

    return MessageResponse(
        message="View count incremented",
        details={"views": post.views},
    )


# ============================================================================
# 6. SEARCH ENDPOINTS
# ============================================================================


@app.get(
    "/authors/{author_id}/posts",
    response_model=BlogPostListResponse,
    tags=["Search"],
    summary="Get posts by author",
)
async def get_posts_by_author(
    author_id: Annotated[str, Path(description="Author's ObjectId")],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> BlogPostListResponse:
    """Get all blog posts by a specific author."""
    if not ObjectId.is_valid(author_id):
        raise HTTPException(status_code=400, detail="Invalid author_id format")

    author = await Author.get(ObjectId(author_id))  # Raises DocumentNotFound if not found

    posts = (
        await BlogPost.find({"author": author.id})
        .skip(skip)
        .limit(limit)
        .all()
    )
    total = await BlogPost.find({"author": author.id}).count()

    # Populate authors
    for post in posts:
        await post.populate("author")

    return BlogPostListResponse(
        items=[BlogPostResponse.from_document(
            p, populate_author=True) for p in posts],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total,
    )


@app.get(
    "/posts/search/by-tag/{tag}",
    response_model=BlogPostListResponse,
    tags=["Search"],
    summary="Search posts by tag",
)
async def search_posts_by_tag(
    tag: Annotated[str, Path(description="Tag to search for")],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> BlogPostListResponse:
    """Search blog posts by tag."""
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

    return BlogPostListResponse(
        items=[BlogPostResponse.from_document(
            p, populate_author=True) for p in posts],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total,
    )


# ============================================================================
# 7. STATISTICS ENDPOINTS
# ============================================================================


@app.get(
    "/stats",
    response_model=StatsResponse,
    tags=["Statistics"],
    summary="Get blog statistics",
)
async def get_statistics() -> StatsResponse:
    """Get overall blog statistics."""
    total_authors = await Author.find().count()
    total_posts = await BlogPost.find().count()
    published_posts = await BlogPost.find({"published": True}).count()

    return StatsResponse(
        total_authors=total_authors,
        total_posts=total_posts,
        published_posts=published_posts,
        draft_posts=total_posts - published_posts,
    )


# ============================================================================
# 8. HEALTH & ROOT ENDPOINTS
# ============================================================================


@app.get(
    "/health",
    response_model=MessageResponse,
    tags=["Health"],
    summary="Health check",
)
async def health_check() -> MessageResponse:
    """Health check endpoint to verify API is running."""
    return MessageResponse(
        message="healthy",
        details={"service": "Pygoose Blog API", "version": "1.0.0"},
    )


@app.get(
    "/",
    tags=["Root"],
    summary="API information",
)
async def root() -> dict:
    """Root endpoint with API information and available endpoints."""
    return {
        "service": "Pygoose Blog API",
        "version": "1.0.0",
        "description": "Production-ready blog API built with Pygoose and FastAPI",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
        },
        "endpoints": {
            "authors": "/authors",
            "posts": "/posts",
            "search": {
                "by_author": "/authors/{author_id}/posts",
                "by_tag": "/posts/search/by-tag/{tag}",
            },
            "stats": "/stats",
            "health": "/health",
        },
    }


# ============================================================================
# 9. USAGE INSTRUCTIONS
# ============================================================================

"""
QUICK START:

1. Install dependencies:
   uv add fastapi uvicorn

2. Start MongoDB:
   mongod

3. Run the API server:
   uv run uvicorn example_fastapi:app --reload

4. Open interactive docs:
   http://localhost:8000/docs

5. Test the API:

   # Create an author
   curl -X POST "http://localhost:8000/authors" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Alice Johnson",
       "email": "alice@example.com",
       "bio": "Tech writer and blogger"
     }'

   # Create a blog post (use the author ID from above)
   curl -X POST "http://localhost:8000/posts" \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Getting Started with Pygoose",
       "content": "Pygoose is an async MongoDB ODM...",
       "author_id": "507f1f77bcf86cd799439011",
       "published": false,
       "tags": ["python", "mongodb"]
     }'

   # List all posts with authors populated
   curl "http://localhost:8000/posts?populate=true"

   # Get a specific post
   curl "http://localhost:8000/posts/{post_id}?populate=true"

   # Publish a post
   curl -X POST "http://localhost:8000/posts/{post_id}/publish"

   # Search by tag
   curl "http://localhost:8000/posts/search/by-tag/python"

   # Get statistics
   curl "http://localhost:8000/stats"

KEY FEATURES DEMONSTRATED:

✅ Proper Pydantic request/response models
✅ OpenAPI schema generation with full validation
✅ ObjectId validation and error handling
✅ Reference population (Ref[Author])
✅ Pagination with has_more flag
✅ Proper HTTP status codes (201 for creation, etc.)
✅ Type hints and documentation
✅ Lifecycle management for MongoDB connection
✅ Search and filtering
✅ Statistics and health checks
"""
