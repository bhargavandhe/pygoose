# FastAPI Examples - Complete Pygoose Feature Showcase

This directory contains two comprehensive FastAPI examples demonstrating all Pygoose features.

## Overview

### 📝 `example_fastapi.py` - Basic Example
A simple, beginner-friendly blog API covering core features.

**Features:**
- ✅ CRUD Operations
- ✅ Reference Population (Ref[Author])
- ✅ Timestamps (TimestampsMixin)
- ✅ Pagination with has_more flag
- ✅ Search/Filtering
- ✅ Exception handling
- ✅ Proper Pydantic schemas

**Endpoints:** 14 main endpoints

**Test Script:** `test_api_endpoints.py` (30+ tests)

---

### 🚀 `example_fastapi_full.py` - Full Feature Example
A production-ready blog API showcasing ALL Pygoose features.

**Additional Features:**
- 🔒 **Encrypted Fields** - Field-level encryption (email)
- 🗑️ **Soft Delete** - Soft delete with restore capability
- 📋 **Audit Logging** - Automatic audit trail via AuditMixin
- 🪝 **Lifecycle Hooks** - @pre_save, @post_save validation
- 📑 **Indexed Fields** - Automatic indexing for performance
- 🔍 **Advanced Querying** - MongoDB regex operators ($regex, $options)
- 👤 **Audit Middleware** - Captures user context from HTTP headers
- 📊 **Status Workflow** - Draft, published, archived states
- 📈 **Rich Statistics** - Views, deleted posts, verified authors

**Endpoints:** 30+ specialized endpoints

**Test Script:** `test_api_full.py` (40+ tests)

---

## Installation

### 1. Install Dependencies

```bash
# Core dependencies
uv add fastapi uvicorn

# For encryption support
uv add cryptography

# For testing
uv add httpx
```

Or use the convenience command:
```bash
uv add fastapi uvicorn cryptography httpx
```

### 2. Ensure MongoDB is Running

```bash
mongod
```

---

## Quick Start

### Run Basic Example

**Terminal 1 - Start server:**
```bash
uv run uvicorn example_fastapi:app --reload
```

**Terminal 2 - Run tests:**
```bash
uv run python test_api_endpoints.py
```

**Browser:**
- Open http://localhost:8000/docs for interactive API docs

---

### Run Full Feature Example

**Terminal 1 - Start server:**
```bash
uv run uvicorn example_fastapi_full:app --reload
```

**Terminal 2 - Run tests:**
```bash
uv run python test_api_full.py
```

**Browser:**
- Open http://localhost:8000/docs for interactive API docs

---

## Feature Comparison

| Feature | Basic | Full |
|---------|-------|------|
| **Core** | | |
| CRUD Operations | ✅ | ✅ |
| References (Ref[T]) | ✅ | ✅ |
| Reference Population | ✅ | ✅ |
| Timestamps | ✅ | ✅ |
| Pagination | ✅ | ✅ |
| Search/Filtering | ✅ | ✅ |
| Exception Handling | ✅ | ✅ |
| **Advanced** | | |
| Soft Delete | ❌ | ✅ |
| Soft Delete Restore | ❌ | ✅ |
| Audit Logging | ❌ | ✅ |
| Encryption | ❌ | ✅ |
| Indexed Fields | ❌ | ✅ |
| Lifecycle Hooks | ❌ | ✅ |
| MongoDB Operators | ❌ | ✅ |
| Audit Middleware | ❌ | ✅ |
| Status Workflow | ❌ | ✅ |

---

## Example API Calls

### Basic Example - Create Author

```bash
curl -X POST "http://localhost:8000/authors" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Johnson",
    "email": "alice@example.com",
    "bio": "Tech writer"
  }'
```

### Full Example - Create Author (with encryption)

```bash
curl -X POST "http://localhost:8000/authors" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: user123" \
  -d '{
    "name": "Alice Johnson",
    "email": "alice@example.com",
    "bio": "Tech writer",
    "verified": true
  }'
```

Note: Email is automatically encrypted. X-User-ID header is captured for audit logging.

### Full Example - Soft Delete & Restore

```bash
# Soft delete a post (preserves data)
curl -X POST "http://localhost:8000/posts/{post_id}/soft-delete"

# Restore a deleted post
curl -X POST "http://localhost:8000/posts/{post_id}/restore"

# Permanently delete a post
curl -X DELETE "http://localhost:8000/posts/{post_id}"
```

### Full Example - Advanced Search

```bash
# Search by status (draft, published, archived)
curl "http://localhost:8000/posts?status=published"

# Search by tag
curl "http://localhost:8000/posts?tag=python"

# Full-text search with regex
curl "http://localhost:8000/posts?search=encryption"

# Combine filters
curl "http://localhost:8000/posts?status=published&tag=python&search=async"
```

### Full Example - Set Audit Context

```bash
curl -X POST "http://localhost:8000/posts" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: alice@example.com" \
  -d '{
    "title": "Post Title",
    "content": "Post content...",
    "author_id": "507f1f77bcf86cd799439011",
    "tags": ["python"]
  }'
```

The audit context (user ID) is automatically captured and logged.

---

## Document Models Explained

### Basic Example

```python
class Author(TimestampsMixin, Document):
    name: str
    email: str
    bio: Optional[str] = None
    # Auto-generated: created_at, updated_at
```

### Full Example

```python
class Author(AuditMixin, TimestampsMixin, Document):
    name: str
    email: Encrypted  # Field-level encryption
    bio: Optional[str] = None
    verified: bool = False
    # Auto-generated: created_at, updated_at
    # Audit logged to: _audit_log collection
```

---

## Lifecycle Hooks Example

The full example demonstrates lifecycle hooks:

```python
@pre_save
def validate_name(self):
    """Validate before saving."""
    if len(self.name) < 2:
        raise ValueError("Name must be at least 2 characters")
    self.name = self.name.strip()

@post_save
def log_author_saved(self):
    """Perform action after save."""
    print(f"✅ Author '{self.name}' saved")
```

---

## Testing

### Basic Tests (30+ tests)
```bash
uv run python test_api_endpoints.py
```

Tests:
- CRUD operations
- Reference population
- Pagination
- Search/filtering
- Error handling (404, 400, 422)
- Data validation

### Full Tests (40+ tests)
```bash
uv run python test_api_full.py
```

Additional tests:
- Encryption/Decryption
- Soft delete & restore
- Audit context
- Lifecycle hooks
- Advanced search
- Status validation

---

## Production Considerations

### For Basic Example
- Good for learning and simple applications
- Sufficient for most use cases
- Lower complexity, easier to understand

### For Full Example
- **Encryption**: Perfect for sensitive data (PII, passwords)
- **Soft Delete**: Enables data recovery and audit trails
- **Audit Logging**: Compliance and security tracking
- **Lifecycle Hooks**: Data validation and business logic
- **Indexing**: Performance optimization for large datasets

---

## Files Structure

```
.
├── example_fastapi.py           # Basic example (14 endpoints)
├── example_fastapi_full.py      # Full example (30+ endpoints)
├── test_api_endpoints.py        # Basic tests (30+ tests)
├── test_api_full.py            # Full tests (40+ tests)
└── FASTAPI_EXAMPLES.md         # This file
```

---

## Common Issues

### "cryptography.fernet.InvalidToken" Error
This happens when the encryption key changes but encrypted data remains in the database.

**Quick Fix - Clear the database:**
```bash
# Connect to MongoDB
mongosh

# Switch to the database
use pygoose_api

# Drop all data
db.dropDatabase()
```

**Better Fix - Use fixed key for development:**
The full example now uses a fixed encryption key for development to avoid this issue.

**Production Fix - Use environment variables:**
```python
import os
encryption.set_key(os.getenv("ENCRYPTION_KEY"))
```

### "No module named 'cryptography'"
Install it:
```bash
uv add cryptography
```

### "ModuleNotFoundError: No module named 'httpx'"
Install it:
```bash
uv add httpx
```

### "Connection refused" or "Server not found"
Make sure MongoDB is running:
```bash
mongod
```

### Tests failing with 500 errors
Check the FastAPI server logs for detailed error messages.

---

## API Documentation

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Both examples provide full OpenAPI schemas with:
- Endpoint descriptions
- Request/response models
- Parameter documentation
- Example values

---

## Learn More

- **Pygoose Docs**: `docs/` directory
- **Examples**: `example_quickstart.py` for simple sync-like code
- **Tests**: `tests/` directory for more usage patterns

---

## Contributing Examples

To extend these examples:

1. **Add new features**: Update the Document models
2. **Add new endpoints**: Create new route handlers
3. **Add new tests**: Update the test scripts
4. **Document changes**: Update this file

Remember:
- Keep examples production-ready
- Include proper error handling
- Add type hints and docstrings
- Test thoroughly

---

Last Updated: Feb 8, 2026
Pygoose Version: 0.1.0
