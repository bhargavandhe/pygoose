"""
Comprehensive Pygoose + FastAPI Example

Demonstrates ALL major Pygoose features with a production-ready REST API:
- ✅ CRUD operations
- ✅ Reference population
- ✅ Timestamps mixin
- ✅ Soft delete
- ✅ Audit logging
- ✅ Encrypted fields
- ✅ Indexed fields
- ✅ Lifecycle hooks
- ✅ Advanced querying (MongoDB operators)
- ✅ Exception handling
- ✅ Pagination

Run with:
  uv add fastapi uvicorn
  uv run uvicorn example_fastapi_full:app --reload

Then visit: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated, Optional

from bson import ObjectId
from fastapi import FastAPI, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field, field_validator

from pygoose import (
    Document,
    Ref,
    connect,
    disconnect,
    Encrypted,
    encryption,
    Indexed,
    pre_save,
    post_save,
    set_audit_context,
)
from pygoose.plugins import TimestampsMixin, SoftDeleteMixin, AuditMixin
from pygoose.utils.exceptions import DocumentNotFound


# ============================================================================
# 1. DOCUMENT MODELS - Full Feature Set
# ============================================================================


class Author(AuditMixin, TimestampsMixin, Document):
    """Blog author with audit logging and timestamps."""

    name: str  # Indexed for fast searching
    email: Encrypted[str]  # Encrypted email for privacy
    bio: Optional[str] = None
    verified: bool = False

    class Settings:
        collection = "authors"
        indexes = [
            {"fields": [("name", 1)], "unique": True},
        ]

    @pre_save
    def validate_name(self):
        """Lifecycle hook: validate name before saving."""
        if len(self.name) < 2:
            raise ValueError("Author name must be at least 2 characters")
        self.name = self.name.strip()

    @post_save
    def log_author_saved(self):
        """Lifecycle hook: log when author is saved."""
        print(f"✅ Author '{self.name}' saved with audit context")


class BlogPost(SoftDeleteMixin, AuditMixin, TimestampsMixin, Document):
    """Blog post with soft delete and audit logging.

    SoftDeleteMixin adds:
    - deleted_at (Optional[datetime]) - timestamp when soft-deleted
    - deleted (bool property) - True if soft-deleted
    - delete() - soft delete method
    - restore() - restore deleted document
    - hard_delete() - permanently delete

    AuditMixin:
    - Logs all operations (insert, update, delete) to _audit_log collection
    - Does NOT add fields to the document itself
    - Audit logs include: user_id, timestamp, operation, changes

    TimestampsMixin adds:
    - created_at, updated_at (auto-managed timestamps)
    """

    title: str  # Indexed for fast searching
    content: str
    author: Ref["Author"]
    published: bool = False
    tags: list[str] = []
    views: int = 0
    status: str = "draft"  # draft, published, archived
    summary: Optional[str] = None

    class Settings:
        collection = "blog_posts"
        indexes = [
            {"fields": [("title", 1)]},
            {"fields": [("status", 1)]},
        ]

    @pre_save
    def auto_generate_summary(self):
        """Lifecycle hook: auto-generate summary from content."""
        if not self.summary and self.content:
            if len(self.content) > 100:
                self.summary = self.content[:100] + "..."
            else:
                self.summary = self.content

    @pre_save
    def validate_status(self):
        """Lifecycle hook: validate status values."""
        if self.status not in ["draft", "published", "archived"]:
            raise ValueError(
                "Invalid status. Must be: draft, published, or archived")


# ============================================================================
# 2. PYDANTIC SCHEMAS
# ============================================================================


class AuthorCreate(BaseModel):
    """Request schema for creating an author."""

    name: str = Field(..., min_length=2, max_length=100,
                      description="Author's name")
    email: str = Field(..., description="Author's email (will be encrypted)")
    bio: Optional[str] = Field(None, max_length=500)
    verified: bool = False


class AuthorUpdate(BaseModel):
    """Request schema for updating an author."""

    name: Optional[str] = Field(None, min_length=2, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    verified: Optional[bool] = None


class AuthorResponse(BaseModel):
    """Response schema for author data."""

    id: str
    name: str
    email: str  # Will be decrypted for display
    bio: Optional[str] = None
    verified: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_document(cls, doc: Author) -> "AuthorResponse":
        data = doc.model_dump(mode="json")
        return cls(
            id=data["id"],
            name=data["name"],
            email=data["email"],  # Decrypted
            bio=data.get("bio"),
            verified=data.get("verified", False),
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )


class BlogPostCreate(BaseModel):
    """Request schema for creating a blog post."""

    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    author_id: str = Field(..., description="Author's ObjectId")
    published: bool = False
    tags: list[str] = Field(default_factory=list, max_length=10)
    status: str = "draft"
    summary: Optional[str] = None

    @field_validator("author_id")
    @classmethod
    def validate_author_id(cls, v: str) -> str:
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid author_id format")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ["draft", "published", "archived"]:
            raise ValueError("Status must be: draft, published, or archived")
        return v


class BlogPostUpdate(BaseModel):
    """Request schema for updating a blog post."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    published: Optional[bool] = None
    tags: Optional[list[str]] = Field(None, max_length=10)
    status: Optional[str] = None
    summary: Optional[str] = None


class BlogPostResponse(BaseModel):
    """Response schema for blog post data."""

    id: str
    title: str
    content: str
    author_id: str
    published: bool
    status: str
    summary: Optional[str] = None
    tags: list[str]
    views: int
    deleted: bool = False  # From SoftDeleteMixin.deleted property
    deleted_at: Optional[datetime] = None  # From SoftDeleteMixin
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
            status=doc.status,
            summary=doc.summary,
            tags=doc.tags,
            views=doc.views,
            deleted=doc.deleted,
            deleted_at=doc.deleted_at,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            author=author_response,
        )


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


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    details: Optional[dict] = None


class StatsResponse(BaseModel):
    """Statistics response."""

    total_authors: int
    verified_authors: int
    total_posts: int
    published_posts: int
    draft_posts: int
    archived_posts: int
    deleted_posts: int
    total_views: int


# ============================================================================
# 3. APP LIFECYCLE
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage MongoDB connection and encryption lifecycle."""
    print("🚀 Starting Pygoose Blog API...")

    # Initialize encryption with FIXED key for development
    # IMPORTANT: In production, use environment variables!
    # Example: encryption.set_key(os.getenv("ENCRYPTION_KEY"))
    dev_key = "L9Zj3yKvN8Qw5tRp2sXm6fBnHgDcVaUe4iOlMkPj7zA="  # Fixed key for dev
    encryption.set_key(dev_key)

    # Connect to MongoDB
    await connect("mongodb://localhost:27017/pygoose_api")
    print("✅ Connected to MongoDB")
    print("🔐 Encryption initialized (using fixed dev key)")
    print("⚠️  WARNING: Using fixed key for development. Use env vars in production!")

    yield

    print("🛑 Shutting down...")
    await disconnect()
    print("✅ Disconnected from MongoDB")


app = FastAPI(
    title="Pygoose Blog API (Full Feature Set)",
    description="Comprehensive blog API showcasing all Pygoose features",
    version="2.0.0",
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
# 4. MIDDLEWARE & AUDIT CONTEXT
# ============================================================================


@app.middleware("http")
async def set_audit_context_middleware(request: Request, call_next):
    """Set audit context for database operations."""
    # Get user info from request (in real app, from JWT token)
    user_id = request.headers.get("X-User-ID", "anonymous")
    ip_address = request.client.host if request.client else "unknown"

    # Set audit context with keyword arguments
    set_audit_context(user_id=user_id, ip_address=ip_address)

    try:
        response = await call_next(request)
        return response
    finally:
        # Clear audit context after request
        from pygoose import clear_audit_context
        clear_audit_context()


# ============================================================================
# 5. AUTHOR ENDPOINTS
# ============================================================================


@app.post(
    "/authors",
    response_model=AuthorResponse,
    status_code=201,
    tags=["Authors"],
    summary="Create a new author",
)
async def create_author(data: AuthorCreate) -> AuthorResponse:
    """Create a new author with encrypted email and audit logging."""
    try:
        author = await Author.create(
            name=data.name,
            email=data.email,  # Will be encrypted
            bio=data.bio,
            verified=data.verified,
        )
        return AuthorResponse.from_document(author)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


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

    author = await Author.get(ObjectId(author_id))
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
    verified_only: Annotated[bool, Query(
        description="Show only verified authors")] = False,
) -> AuthorListResponse:
    """List all authors with optional filtering."""
    filter_dict = {"verified": True} if verified_only else {}

    authors = await Author.find(filter_dict).skip(skip).limit(limit).all()
    total = await Author.find(filter_dict).count()

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
    """Update an author with audit logging."""
    if not ObjectId.is_valid(author_id):
        raise HTTPException(status_code=400, detail="Invalid author_id format")

    author = await Author.get(ObjectId(author_id))

    if data.name is not None:
        author.name = data.name
    if data.bio is not None:
        author.bio = data.bio
    if data.verified is not None:
        author.verified = data.verified

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
    """Delete an author permanently."""
    if not ObjectId.is_valid(author_id):
        raise HTTPException(status_code=400, detail="Invalid author_id format")

    author = await Author.get(ObjectId(author_id))

    # Check if author has active posts
    post_count = await BlogPost.find({"author": author.id}).count()
    if post_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete author with {post_count} existing posts",
        )

    await author.delete()
    return MessageResponse(message="Author deleted successfully")


# ============================================================================
# 6. BLOG POST ENDPOINTS
# ============================================================================


@app.post(
    "/posts",
    response_model=BlogPostResponse,
    status_code=201,
    tags=["Posts"],
    summary="Create a new blog post",
)
async def create_post(data: BlogPostCreate) -> BlogPostResponse:
    """Create a new blog post with lifecycle hooks and audit logging."""
    author = await Author.get(ObjectId(data.author_id))

    try:
        post = await BlogPost.create(
            title=data.title,
            content=data.content,
            author=author.id,
            published=data.published,
            tags=data.tags,
            status=data.status,
            summary=data.summary,
        )
        return BlogPostResponse.from_document(post)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


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
    """Retrieve a single blog post by ID (excludes soft-deleted posts)."""
    if not ObjectId.is_valid(post_id):
        raise HTTPException(status_code=400, detail="Invalid post_id format")

    post = await BlogPost.get(ObjectId(post_id))

    if post.deleted:
        raise HTTPException(status_code=404, detail="Post has been deleted")

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
    status: Annotated[Optional[str], Query(
        description="Filter by status: draft, published, archived")] = None,
    tag: Annotated[Optional[str], Query(description="Filter by tag")] = None,
    search: Annotated[Optional[str], Query(
        description="Search in title/content")] = None,
    populate: Annotated[bool, Query(
        description="Populate author details")] = True,
) -> BlogPostListResponse:
    """List blog posts with advanced filtering (MongoDB operators)."""
    filter_dict = {}  # SoftDeleteMixin automatically excludes soft-deleted posts

    # Apply status filter
    if status:
        filter_dict["status"] = status

    # Apply tag filter
    if tag:
        filter_dict["tags"] = tag

    # Apply search filter using MongoDB regex
    if search:
        filter_dict["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},  # Case-insensitive
            {"content": {"$regex": search, "$options": "i"}},
        ]

    posts = await BlogPost.find(filter_dict).skip(skip).limit(limit).all()
    total = await BlogPost.find(filter_dict).count()

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
    """Update a blog post with lifecycle hooks."""
    if not ObjectId.is_valid(post_id):
        raise HTTPException(status_code=400, detail="Invalid post_id format")

    post = await BlogPost.get(ObjectId(post_id))

    if post.deleted:
        raise HTTPException(status_code=404, detail="Post has been deleted")

    if data.title is not None:
        post.title = data.title
    if data.content is not None:
        post.content = data.content
    if data.status is not None:
        post.status = data.status
    if data.tags is not None:
        post.tags = data.tags
    if data.summary is not None:
        post.summary = data.summary

    try:
        await post.save()
        await post.populate("author")
        return BlogPostResponse.from_document(post, populate_author=True)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post(
    "/posts/{post_id}/soft-delete",
    response_model=MessageResponse,
    tags=["Posts"],
    summary="Soft delete a blog post",
)
async def soft_delete_post(
    post_id: Annotated[str, Path(description="Post's ObjectId")]
) -> MessageResponse:
    """Soft delete a blog post (marks as deleted but preserves data)."""
    if not ObjectId.is_valid(post_id):
        raise HTTPException(status_code=400, detail="Invalid post_id format")

    post = await BlogPost.get(ObjectId(post_id))

    if post.deleted:
        raise HTTPException(status_code=400, detail="Post is already deleted")

    # Use SoftDeleteMixin's built-in delete() method
    await post.delete()

    return MessageResponse(message="Post soft-deleted successfully")


@app.post(
    "/posts/{post_id}/restore",
    response_model=MessageResponse,
    tags=["Posts"],
    summary="Restore a soft-deleted blog post",
)
async def restore_post(
    post_id: Annotated[str, Path(description="Post's ObjectId")]
) -> MessageResponse:
    """Restore a soft-deleted blog post."""
    if not ObjectId.is_valid(post_id):
        raise HTTPException(status_code=400, detail="Invalid post_id format")

    # Need to use find_with_deleted to get soft-deleted posts
    post = await BlogPost.find_with_deleted({"_id": ObjectId(post_id)}).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if not post.deleted:
        raise HTTPException(status_code=400, detail="Post is not deleted")

    # Use SoftDeleteMixin's built-in restore() method
    await post.restore()

    return MessageResponse(message="Post restored successfully")


@app.delete(
    "/posts/{post_id}",
    response_model=MessageResponse,
    tags=["Posts"],
    summary="Permanently delete a blog post",
)
async def delete_post(
    post_id: Annotated[str, Path(description="Post's ObjectId")]
) -> MessageResponse:
    """Permanently delete a blog post."""
    if not ObjectId.is_valid(post_id):
        raise HTTPException(status_code=400, detail="Invalid post_id format")

    post = await BlogPost.get(ObjectId(post_id))
    await post.delete()

    return MessageResponse(message="Post permanently deleted")


@app.post(
    "/posts/{post_id}/publish",
    response_model=BlogPostResponse,
    tags=["Posts"],
    summary="Publish a blog post",
)
async def publish_post(
    post_id: Annotated[str, Path(description="Post's ObjectId")]
) -> BlogPostResponse:
    """Publish a blog post and update its status."""
    if not ObjectId.is_valid(post_id):
        raise HTTPException(status_code=400, detail="Invalid post_id format")

    post = await BlogPost.get(ObjectId(post_id))

    if post.deleted:
        raise HTTPException(status_code=404, detail="Post has been deleted")

    if post.published:
        raise HTTPException(
            status_code=400, detail="Post is already published")

    post.published = True
    post.status = "published"
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

    post = await BlogPost.get(ObjectId(post_id))
    post.views += 1
    await post.save()

    return MessageResponse(
        message="View count incremented",
        details={"views": post.views},
    )


# ============================================================================
# 7. SEARCH ENDPOINTS
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

    author = await Author.get(ObjectId(author_id))

    posts = (
        await BlogPost.find({"author": author.id})
        .skip(skip)
        .limit(limit)
        .all()
    )
    total = await BlogPost.find({"author": author.id, "deleted": False}).count()

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
    total = await BlogPost.find({"tags": tag, "deleted": False}).count()

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
# 8. STATISTICS ENDPOINTS
# ============================================================================


@app.get(
    "/stats",
    response_model=StatsResponse,
    tags=["Statistics"],
    summary="Get blog statistics",
)
async def get_statistics() -> StatsResponse:
    """Get comprehensive blog statistics."""
    total_authors = await Author.find().count()
    verified_authors = await Author.find({"verified": True}).count()

    # SoftDeleteMixin automatically excludes soft-deleted posts
    total_posts = await BlogPost.find().count()
    published_posts = await BlogPost.find({"published": True}).count()
    draft_posts = await BlogPost.find({"status": "draft"}).count()
    archived_posts = await BlogPost.find({"status": "archived"}).count()

    # To count soft-deleted posts, use find_deleted()
    deleted_posts = await BlogPost.find_deleted().count()

    # Calculate total views
    posts_with_views = await BlogPost.find().all()
    total_views = sum(p.views for p in posts_with_views)

    return StatsResponse(
        total_authors=total_authors,
        verified_authors=verified_authors,
        total_posts=total_posts,
        published_posts=published_posts,
        draft_posts=draft_posts,
        archived_posts=archived_posts,
        deleted_posts=deleted_posts,
        total_views=total_views,
    )


# ============================================================================
# 9. HEALTH & ROOT ENDPOINTS
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
        details={
            "service": "Pygoose Blog API (Full Features)",
            "version": "2.0.0",
            "features": [
                "CRUD operations",
                "Reference population",
                "Timestamps",
                "Soft delete",
                "Audit logging",
                "Encrypted fields",
                "Indexed fields",
                "Lifecycle hooks",
                "Advanced querying",
            ],
        },
    )


@app.get("/")
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "service": "Pygoose Blog API (Full Feature Set)",
        "version": "2.0.0",
        "description": "Production-ready blog API showcasing all Pygoose features",
        "features": {
            "core": ["CRUD", "Querying", "Pagination"],
            "advanced": [
                "Soft Delete (SoftDeleteMixin)",
                "Audit Logging (AuditMixin)",
                "Timestamps (TimestampsMixin)",
                "Field Encryption (Encrypted)",
                "Field Indexing (Indexed)",
                "Lifecycle Hooks (pre_save, post_save, etc.)",
                "MongoDB Operators (regex, comparison)",
                "Reference Population (Ref, LazyRef)",
            ],
        },
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
# 10. USAGE INSTRUCTIONS
# ============================================================================

"""
FEATURES DEMONSTRATED:

✅ CORE FEATURES:
   - CRUD operations (Create, Read, Update, Delete)
   - Async MongoDB operations
   - Reference population (Ref[Author])
   - Pagination with has_more flag
   - Exception handling

✅ PLUGIN FEATURES:
   - TimestampsMixin: Automatic created_at/updated_at
   - SoftDeleteMixin: Soft delete with restore capability
   - AuditMixin: Track who created/updated each document

✅ FIELD FEATURES:
   - Encrypted[str]: Field-level encryption for sensitive data
   - Indexed(): Indexed fields with unique constraints

✅ LIFECYCLE FEATURES:
   - @pre_save: Validation and auto-generation before save
   - @post_save: Logging and side effects after save

✅ QUERY FEATURES:
   - Advanced filtering with MongoDB operators ($regex, $options)
   - Complex queries with multiple conditions
   - Text search capabilities

TESTING THE API:

1. Create an author:
   POST /authors
   {
     "name": "Alice Johnson",
     "email": "alice@example.com",
     "bio": "Tech writer",
     "verified": true
   }

2. Create a blog post:
   POST /posts
   {
     "title": "Pygoose Features",
     "content": "Full-featured MongoDB ODM...",
     "author_id": "{author_id}",
     "tags": ["python", "mongodb"],
     "status": "draft"
   }

3. Search with filters:
   GET /posts?status=published&tag=python&search=mongodb

4. Soft delete (preserves data):
   POST /posts/{post_id}/soft-delete

5. Restore soft-deleted post:
   POST /posts/{post_id}/restore

6. Get comprehensive stats:
   GET /stats

7. Advanced audit tracking:
   - All operations logged to _audit_log collection
   - Set X-User-ID header for audit context
   - View audit logs in MongoDB: db._audit_log.find()
"""
