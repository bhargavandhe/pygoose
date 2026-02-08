# Examples

Common patterns and use cases with Pygoose.

## Building a blog API

Here's a complete example of a blog API with posts, comments, and users:

```python
from fastapi import FastAPI, HTTPException
from pygoose import (
    connect,
    disconnect,
    Document,
    Ref,
    TimestampsMixin,
    init_app,
)
from pydantic import Field
from datetime import datetime
from bson import ObjectId

app = FastAPI()
init_app(app)

# Models
class User(Document, TimestampsMixin):
    name: str
    email: str
    bio: str = ""

class Comment(Document, TimestampsMixin):
    author: Ref[User]
    content: str
    post: Ref["Post"]

class Post(Document, TimestampsMixin):
    title: str
    content: str
    author: Ref[User]
    published: bool = False

# Startup and shutdown
@app.on_event("startup")
async def startup():
    await connect("mongodb://localhost:27017/blog")

@app.on_event("shutdown")
async def shutdown():
    await disconnect()

# User endpoints
@app.post("/users")
async def create_user(user: User):
    await user.save()
    return user

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await User.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Post endpoints
@app.post("/posts")
async def create_post(post: Post):
    await post.save()
    return post

@app.get("/posts")
async def list_posts(published_only: bool = True):
    query = Post.find()
    if published_only:
        query = query.filter(published=True)
    posts = await query.sort("-created_at").all()
    return posts

@app.get("/posts/{post_id}")
async def get_post(post_id: str):
    post = await (
        Post
        .find({"_id": ObjectId(post_id)})
        .populate("author")
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@app.put("/posts/{post_id}")
async def update_post(post_id: str, data: dict):
    post = await Post.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    for key, value in data.items():
        if hasattr(post, key):
            setattr(post, key, value)

    await post.save()
    return post

# Comment endpoints
@app.post("/posts/{post_id}/comments")
async def add_comment(post_id: str, comment: Comment):
    post = await Post.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    comment.post = post.id
    await comment.save()
    return comment

@app.get("/posts/{post_id}/comments")
async def list_comments(post_id: str):
    comments = await (
        Comment
        .find({"post": ObjectId(post_id)})
        .populate("author")
        .sort("-created_at")
        .all()
    )
    return comments
```

## User authentication with password hashing

Implement secure user authentication with password hashing:

```python
from pygoose import Document, pre_save
import bcrypt

class User(Document):
    email: str
    password_hash: str
    password: str = ""  # Transient, not stored

    @pre_save
    async def hash_password(self):
        # Only hash if password was changed
        if self.password and ("password" not in self._dirty_fields):
            self.password_hash = bcrypt.hashpw(
                self.password.encode(),
                bcrypt.gensalt()
            ).decode()
            # Clear the plain password
            self.password = ""

    def verify_password(self, password: str) -> bool:
        return bcrypt.checkpw(
            password.encode(),
            self.password_hash.encode()
        )

# Usage
user = User(email="alice@example.com", password="securepassword")
await user.save()

# Verify password
user = await User.find_one({"email": "alice@example.com"})
if user.verify_password("securepassword"):
    print("Password is correct!")
```

## Category hierarchy with self-references

Create hierarchical data with self-references:

```python
from pygoose import Document, Ref
from typing import Optional

class Category(Document):
    name: str
    parent: Optional[Ref["Category"]] = None
    description: str = ""

    async def get_children(self):
        """Get all subcategories."""
        return await Category.find({"parent": self.id}).all()

    async def get_parent(self):
        """Get the parent category."""
        if not self.parent:
            return None
        return await Category.find_one({"_id": self.parent})

    async def get_breadcrumbs(self):
        """Get the full path from root to this category."""
        breadcrumbs = [self.name]
        current = self
        while current.parent:
            parent = await current.get_parent()
            if parent:
                breadcrumbs.insert(0, parent.name)
                current = parent
            else:
                break
        return breadcrumbs

# Usage
root = Category(name="Products")
await root.save()

electronics = Category(name="Electronics", parent=root.id)
await electronics.save()

laptops = Category(name="Laptops", parent=electronics.id)
await laptops.save()

breadcrumbs = await laptops.get_breadcrumbs()
print(breadcrumbs)  # ['Products', 'Electronics', 'Laptops']
```

## Soft delete with audit trail

Track deletions without actually removing data:

```python
from pygoose import Document, SoftDeleteMixin, AuditMixin, set_audit_context

class Document(Document, SoftDeleteMixin, AuditMixin):
    title: str
    content: str

# Set audit context
set_audit_context(user_id="user123", request_id="req456")

# Delete a document
doc = await Document.find_one({"title": "My Document"})
await doc.delete()  # Soft delete

# Query excludes deleted documents
docs = await Document.find().all()  # Does not include the deleted doc

# Admin can see all documents including deleted
all_docs = await Document.find().include_deleted().all()
```

## Pagination patterns

Implement different pagination strategies:

```python
from pygoose import Page

async def paginate_offset(page: int = 1, page_size: int = 10):
    """Offset-based pagination (simple, works for small datasets)."""
    skip = (page - 1) * page_size
    items = await (
        User
        .find()
        .skip(skip)
        .limit(page_size)
        .all()
    )
    total = await User.find().count()
    return Page(items=items, total=total, skip=skip, limit=page_size)

async def paginate_cursor(cursor: str | None = None, limit: int = 10):
    """Cursor-based pagination (efficient for large datasets)."""
    query = User.find().sort("_id").limit(limit + 1)

    if cursor:
        query = query.filter({"_id": {"$gt": ObjectId(cursor)}})

    items = await query.all()
    has_more = len(items) > limit
    items = items[:limit]

    next_cursor = None
    if has_more and items:
        next_cursor = str(items[-1].id)

    return {"items": items, "cursor": cursor, "next_cursor": next_cursor}
```

## Bulk operations

Perform efficient bulk updates:

```python
async def update_user_subscriptions():
    """Update all inactive users to expired status."""
    result = await User.update_many(
        {
            "subscription_status": "inactive",
            "last_login": {"$lt": datetime.now() - timedelta(days=30)}
        },
        {
            "$set": {
                "subscription_status": "expired",
                "updated_at": datetime.now()
            }
        }
    )
    print(f"Updated {result.modified_count} users")

async def archive_old_posts():
    """Move old posts to an archive collection."""
    old_posts = await (
        Post
        .find({"created_at": {"$lt": datetime.now() - timedelta(days=365)}})
        .all()
    )

    # Archive them (example: could save to different collection)
    for post in old_posts:
        post.archived = True
        await post.save()
```

## Transaction simulation

Simulate transactions with error handling:

```python
async def transfer_balance(from_user_id: str, to_user_id: str, amount: float):
    """Transfer balance between users with rollback on error."""
    from_user = await User.find_one({"_id": ObjectId(from_user_id)})
    to_user = await User.find_one({"_id": ObjectId(to_user_id)})

    if not from_user or not to_user:
        raise ValueError("User not found")

    if from_user.balance < amount:
        raise ValueError("Insufficient balance")

    # Deduct from source
    from_user.balance -= amount

    # Add to destination
    to_user.balance += amount

    try:
        # Save both (in practice, use MongoDB transactions for true ACID)
        await from_user.save()
        await to_user.save()
    except Exception as e:
        # Reload if save fails
        await from_user.reload()
        await to_user.reload()
        raise e
```

## Next steps

- [FastAPI integration](FASTAPI_INTEGRATION.md) — More FastAPI patterns
- [Advanced features](ADVANCED_FEATURES.md) — Hooks, encryption, and plugins
