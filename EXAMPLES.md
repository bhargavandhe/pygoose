# Pygoose Examples

This directory contains comprehensive examples demonstrating all features of Pygoose.

## Quick Links

- **5-minute quickstart:** [example_quickstart.py](#quick-start)
- **All features showcase:** [example_showcase.py](#comprehensive-showcase)
- **Real-world REST API:** [example_fastapi.py](#fastapi-rest-api)

---

## Prerequisites

Before running any examples, ensure:

1. **MongoDB is running:**
   ```bash
   # macOS with Homebrew
   brew services start mongodb-community

   # Or using Docker
   docker run -d -p 27017:27017 mongo:latest
   ```

2. **Pygoose is installed:**
   ```bash
   pip install pygoose
   ```

3. **For FastAPI example, install uvicorn:**
   ```bash
   pip install uvicorn
   ```

---

## Quick Start

**File:** `example_quickstart.py`

The fastest way to learn Pygoose basics (5 minutes).

### What it covers:
- Defining documents
- Creating and reading documents
- Updating documents
- Querying with filters
- Counting documents
- Deleting documents
- References between documents

### Run it:
```bash
python example_quickstart.py
```

### Expected output:
```
============================================================
PYGOOSE QUICKSTART EXAMPLE
============================================================

✅ Connected to MongoDB

1️⃣  CREATE - Adding an author
   Created author: Alice Johnson (ID: 65a1b2c3d4e5f6g7h8i9j0k1)

2️⃣  CREATE - Adding a blog post with author reference
   Created post: Getting Started with Pygoose

3️⃣  READ - Fetching the post by ID
   Title: Getting Started with Pygoose
   Views: 0

...and more
```

---

## Comprehensive Showcase

**File:** `example_showcase.py`

Demonstrates **every feature** of Pygoose with detailed examples.

### What it covers:

#### 1. Basic CRUD Operations
- Create documents
- Read by ID
- Update fields
- Delete documents

#### 2. QuerySet Fluent API
- `find()` - Query with filters
- `find_one()` - Get single document
- `sort()` - Order results
- `limit()` - Limit results
- `skip()` - Pagination offset
- `count()` - Count matches
- `exists()` - Check existence
- `all()` - Fetch all results
- `paginate()` - Page-based pagination

#### 3. References & Population
- Single reference population
- Batch population (efficient)
- Nested population (Post -> User)
- Deep population

#### 4. Field-Level Encryption
- Generate encryption keys
- Encrypt sensitive fields
- Automatic decryption on load
- Update encrypted fields
- Limitations (not queryable)

#### 5. Lifecycle Hooks
- `@pre_save` - Before saving
- `@post_save` - After saving
- `@pre_delete` - Before deletion
- Field validation in hooks

#### 6. Soft Delete Plugin
- Mark as deleted (not removed)
- Filter deleted records automatically
- Query with `include_deleted()`

#### 7. Timestamps Plugin
- Automatic `created_at` field
- Automatic `updated_at` field
- Track document history

#### 8. Dirty Field Tracking
- Only save modified fields
- Track which fields changed
- Efficient database updates

#### 9. Pagination
- Page-based pagination
- Sort while paginating
- Metadata (total, pages)

#### 10. FastAPI Integration
- Lifespan management
- Create REST endpoints
- Reference resolution
- Exception handling

### Run it:
```bash
python example_showcase.py
```

### Example output:
```
╔════════════════════════════════════════════════════════════════╗
║           PYGOOSE - COMPREHENSIVE SHOWCASE                    ║
╚════════════════════════════════════════════════════════════════╝

✅ Connected to MongoDB
✅ Encryption configured

======================================================================
EXAMPLE 1: Basic CRUD Operations
======================================================================

1️⃣  Creating a user...
   Created user: Alice Johnson (ID: 65a1b2c3d4e5f6g7h8i9j0k1)

2️⃣  Reading user by ID...
   Fetched: Alice Johnson, Age: 28

3️⃣  Updating user (dirty tracking)...
   Dirty fields: {'age'}
   Saved! New age: 29

...and 8 more examples
```

---

## FastAPI REST API

**File:** `example_fastapi.py`

A production-ready blog API demonstrating Pygoose with FastAPI.

### What it covers:

#### Models
- Author document
- BlogPost document with references
- Automatic timestamps

#### REST Endpoints

**Authors:**
- `POST /authors` - Create author
- `GET /authors` - List all authors
- `GET /authors/{id}` - Get specific author
- `PUT /authors/{id}` - Update author
- `DELETE /authors/{id}` - Delete author

**Posts:**
- `POST /posts` - Create post
- `GET /posts` - List posts
- `GET /posts/{id}` - Get post with author
- `PUT /posts/{id}` - Update post
- `DELETE /posts/{id}` - Delete post
- `POST /posts/{id}/publish` - Publish post

**Search:**
- `GET /posts/search/by-author/{id}` - Posts by author
- `GET /posts/search/by-tag/{tag}` - Posts by tag

**Stats:**
- `GET /stats` - Blog statistics
- `GET /health` - Health check

### Run it:
```bash
uvicorn example_fastapi:app --reload
```

### Access the API:

1. **Interactive API Docs (Swagger UI):**
   http://localhost:8000/docs

2. **Alternative Docs (ReDoc):**
   http://localhost:8000/redoc

3. **OpenAPI Schema:**
   http://localhost:8000/openapi.json

### Example requests:

**Create an author:**
```bash
curl -X POST "http://localhost:8000/authors" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Johnson",
    "email": "alice@example.com",
    "bio": "Tech writer"
  }'
```

**Create a post:**
```bash
curl -X POST "http://localhost:8000/posts" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My First Post",
    "content": "Hello, world!",
    "author_id": "<author_id>",
    "tags": ["python", "mongodb"]
  }'
```

**List posts:**
```bash
curl "http://localhost:8000/posts?skip=0&limit=10"
```

**Get a post with author:**
```bash
curl "http://localhost:8000/posts/<post_id>"
```

**Publish a post:**
```bash
curl -X POST "http://localhost:8000/posts/<post_id>/publish"
```

**Search by tag:**
```bash
curl "http://localhost:8000/posts/search/by-tag/python"
```

---

## Feature Comparison

| Feature | Quickstart | Showcase | FastAPI |
|---------|-----------|----------|---------|
| CRUD | ✅ | ✅ | ✅ |
| QuerySet | ✅ | ✅ | ✅ |
| References | ✅ | ✅ | ✅ |
| Population | ✅ | ✅ | ✅ |
| Encryption | ❌ | ✅ | ❌ |
| Hooks | ❌ | ✅ | ✅ |
| Soft Delete | ❌ | ✅ | ❌ |
| Timestamps | ❌ | ✅ | ✅ |
| Pagination | ❌ | ✅ | ✅ |
| FastAPI | ❌ | ✅ | ✅ |
| Complexity | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Time to read | 5 min | 30 min | 20 min |

---

## Learning Path

1. **Start here:** Run `example_quickstart.py` to understand basics
2. **Explore features:** Run `example_showcase.py` to see all capabilities
3. **Build APIs:** Use `example_fastapi.py` as a template for your REST APIs

---

## Common Issues

### MongoDB connection error
```
❌ Connection failed: [Errno 111] Connection refused
```

**Solution:** Ensure MongoDB is running
```bash
# Check if running
mongosh

# Or start it
brew services start mongodb-community
```

### Module not found error
```
ModuleNotFoundError: No module named 'pygoose'
```

**Solution:** Install Pygoose
```bash
pip install pygoose
```

### Invalid ObjectId error
```
InvalidId: invalid ObjectId hex string
```

**Solution:** Ensure you're using valid ObjectId strings or convert them:
```python
from bson import ObjectId
user_id = ObjectId(string_id)  # Convert string to ObjectId
```

---

## Tips & Best Practices

### 1. Always use async/await
```python
# ❌ Wrong
user = User.get(user_id)

# ✅ Correct
user = await User.get(user_id)
```

### 2. Populate references for nested access
```python
# ❌ Without population (author is ObjectId)
post = await Post.get(post_id)
print(post.author.name)  # AttributeError

# ✅ With population
post = await Post.get(post_id)
await post.populate("author")
print(post.author.name)  # Works!
```

### 3. Use QuerySet for efficient queries
```python
# ❌ Inefficient (loads all documents)
posts = await Post.find().all()
popular = [p for p in posts if p.views > 100]

# ✅ Efficient (filters in database)
popular = await Post.find(views={"$gte": 100}).all()
```

### 4. Set encryption before use
```python
from pygoose import encryption, generate_encryption_key

# Must be done before creating encrypted documents
encryption.set_key(generate_encryption_key())
```

### 5. Use dirty tracking for updates
```python
# Pygoose automatically tracks changes
user = await User.get(user_id)
user.age = 30  # Mark as dirty
await user.save()  # Only updates age field
```

---

## Next Steps

- Read the [full documentation](docs/INDEX.md)
- Check the [API reference](docs/API_REFERENCE.md)
- Explore the [advanced features guide](docs/ADVANCED_FEATURES.md)
- Build your own project!

---

## Questions?

- Check the [documentation](docs/)
- Open an issue on [GitHub](https://github.com/bhargavandhe/pygoose/issues)
- See [examples](.) for more use cases

Happy coding! 🚀
