# Advanced features

Pygoose provides several advanced capabilities for complex application needs.

## Lifecycle hooks

Hooks let you run custom code at key points in a document's lifecycle. Define
hooks as methods decorated with hook decorators.

### Available hooks

Pygoose supports six lifecycle hooks that run at different stages:

- `@pre_validate` — Runs before Pydantic validation
- `@pre_save` — Runs before a document is saved to MongoDB
- `@post_save` — Runs after a document is successfully saved
- `@pre_delete` — Runs before a document is deleted
- `@post_delete` — Runs after a document is successfully deleted
- `@post_update` — Runs after an update operation completes

### Using hooks

Define hooks as async methods in your document class:

```python
from pygoose import Document, pre_save, post_save, pre_delete

class User(Document):
    name: str
    email: str
    password_hash: str

    @pre_save
    async def hash_password(self):
        # Hash the password before saving
        import bcrypt
        self.password_hash = bcrypt.hashpw(
            self.password.encode(),
            bcrypt.gensalt()
        ).decode()

    @post_save
    async def log_creation(self):
        if self._is_new:
            print(f"User {self.name} created with id {self.id}")

    @pre_delete
    async def cleanup(self):
        print(f"Deleting user {self.name}")
```

Hooks are always async. If your hook doesn't need async operations, use `async
def` and implement your logic synchronously.

### Hook execution order

Hooks run in method resolution order (MRO), so parent class hooks run before
child class hooks. Multiple hooks of the same type run in definition order.

## Field-level encryption

Encrypt sensitive fields at the document level using the `Encrypted[T]` type.
Encrypted fields are automatically encrypted before saving and decrypted after
loading.

### Setup

First, generate an encryption key and set it globally:

```python
from pygoose import generate_encryption_key, set_encryption_key

# Generate a new key (save this securely!)
key = generate_encryption_key()
print(key)  # base64-encoded key

# Set the key globally
set_encryption_key(key)
```

### Using encrypted fields

Mark fields as encrypted using `Encrypted[T]`:

```python
from pygoose import Document, Encrypted

class User(Document):
    name: str
    email: Encrypted[str]  # This field is encrypted
    ssn: Encrypted[str]    # Social security number
    phone: str             # Not encrypted
```

Encrypted fields work like normal fields but are automatically encrypted before
MongoDB storage and decrypted when loaded:

```python
user = User(name="Alice", email="alice@example.com", ssn="123-45-6789")
await user.save()  # email and ssn are encrypted in MongoDB

user = await User.find_one()
print(user.email)  # Decrypted: alice@example.com
print(user.ssn)    # Decrypted: 123-45-6789
```

### Key rotation

To rotate encryption keys without decrypting all data:

1. Set the new key as the current key
2. Load and re-save your documents

Pygoose handles decryption with old keys automatically.

## Database indexes

Define indexes on your documents to improve query performance:

```python
from pygoose import Document, Indexed, IndexSpec

class User(Document):
    email: Indexed[str]  # Single-field index
    name: str
    created_at: Indexed[datetime]

    class Settings:
        # Compound index on name and created_at
        indexes = [
            IndexSpec(keys=[("name", 1), ("created_at", -1)])
        ]
```

Create indexes in MongoDB:

```python
await User.create_indexes()
```

## Plugins

Plugins extend document functionality. Pygoose ships with several built-in
plugins.

### Timestamps

Add `created_at` and `updated_at` fields automatically:

```python
from pygoose import Document, TimestampsMixin
from datetime import datetime

class Article(Document, TimestampsMixin):
    title: str
    content: str
```

The `created_at` field is set when the document is first saved. The `updated_at`
field updates every time you save.

```python
article = Article(title="My Article", content="...")
await article.save()
print(article.created_at)  # Current timestamp

article.content = "Updated content"
await article.save()
print(article.updated_at)  # Updated timestamp
```

### Soft delete

Mark documents as deleted without removing them from MongoDB:

```python
from pygoose import Document, SoftDeleteMixin

class User(Document, SoftDeleteMixin):
    name: str
    email: str
```

When you delete a user, it's marked as deleted but remains in the database:

```python
user = await User.find_one()
await user.delete()  # Marks user as deleted

# Queries automatically exclude soft-deleted documents
users = await User.find().all()  # Does not include the deleted user

# To include deleted documents, use include_deleted()
all_users = await User.find().include_deleted().all()
```

### Audit trail

Track who modified documents and when using the audit plugin:

```python
from pygoose import Document, AuditMixin, set_audit_context

class Article(Document, AuditMixin):
    title: str
    content: str
```

Set audit context in your request handler:

```python
from fastapi import Request
from pygoose import set_audit_context

@app.put("/articles/{article_id}")
async def update_article(article_id: str, data: ArticleUpdate):
    # Set audit context for this request
    set_audit_context(
        user_id="user123",
        request_id="req456"
    )

    article = await Article.find_one({"_id": ObjectId(article_id)})
    article.title = data.title
    await article.save()

    return article
```

The audit trail automatically records the user, request ID, and timestamp of
changes.

## Multi-database setups

Use multiple MongoDB databases by creating multiple connections with different
aliases:

```python
# Connect to multiple databases
await connect("mongodb://localhost:27017/db1", alias="db1")
await connect("mongodb://localhost:27017/db2", alias="db2")

# Use Settings to bind a document to a specific database
class User(Document):
    name: str

    class Settings:
        connection_alias = "db1"

class Product(Document):
    name: str
    price: float

    class Settings:
        connection_alias = "db2"
```

Now `User` queries hit `db1` and `Product` queries hit `db2`.

## Query observability

Monitor all MongoDB queries executed by your application:

```python
from pygoose import enable_tracing, add_listener, QueryEvent

# Enable tracing
enable_tracing()

# Add a listener
def on_query(event: QueryEvent):
    print(f"Operation: {event.operation}")
    print(f"Collection: {event.collection}")
    print(f"Duration: {event.duration_ms}ms")

add_listener(on_query)
```

This is useful for debugging, monitoring, and performance analysis.

## Next steps

- [API reference](API_REFERENCE.md) — Complete method documentation
- [FastAPI integration](FASTAPI_INTEGRATION.md) — Use Pygoose with FastAPI
