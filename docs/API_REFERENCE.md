# API reference

Complete reference for Pygoose's public API.

## Connection management

### connect()

```python
async def connect(uri: str, *, alias: str = "default") -> AsyncDatabase
```

Establish a connection to MongoDB.

**Parameters:**

- `uri` (str) — MongoDB connection URI, must include database name
- `alias` (str, optional) — Connection alias for multi-database setups, defaults
  to `"default"`

**Returns:** `AsyncDatabase` instance for the connected database

**Example:**

```python
from pygoose import connect

db = await connect("mongodb://localhost:27017/my_database")
```

### disconnect()

```python
async def disconnect(alias: str = "default") -> None
```

Close a MongoDB connection and remove it from the registry.

**Parameters:**

- `alias` (str, optional) — Connection alias to disconnect, defaults to
  `"default"`

**Example:**

```python
from pygoose import disconnect

await disconnect()
```

### get_database()

```python
def get_database(alias: str = "default") -> AsyncDatabase
```

Retrieve a registered database connection.

**Parameters:**

- `alias` (str, optional) — Connection alias, defaults to `"default"`

**Returns:** `AsyncDatabase` instance

**Raises:** `NotConnected` if the alias is not registered

### get_client()

```python
def get_client(alias: str = "default") -> AsyncMongoClient
```

Retrieve a registered MongoDB client.

**Parameters:**

- `alias` (str, optional) — Connection alias, defaults to `"default"`

**Returns:** `AsyncMongoClient` instance

**Raises:** `NotConnected` if the alias is not registered

## Document class

### save()

```python
async def save(self) -> ObjectId
```

Save the document to MongoDB. If the document is new, it's inserted. If it
already exists, only dirty fields are updated.

**Returns:** The document's ObjectId

**Example:**

```python
user = User(name="Alice", email="alice@example.com")
await user.save()
```

### delete()

```python
async def delete(self) -> None
```

Delete the document from MongoDB.

**Example:**

```python
user = await User.find_one({"name": "Alice"})
await user.delete()
```

### find()

```python
@classmethod
def find(cls, filter: FilterSpec | None = None, **kwargs) -> QuerySet[Self]
```

Create a query to find documents of this type.

**Parameters:**

- `filter` (dict, optional) — MongoDB filter criteria
- `**kwargs` — Additional filter criteria as keyword arguments

**Returns:** `QuerySet` instance for fluent query building

**Example:**

```python
users = await User.find({"age": {"$gte": 18}}).all()
```

### find_one()

```python
@classmethod
async def find_one(cls, filter: FilterSpec | None = None, **kwargs) -> Self | None
```

Find a single document matching the filter.

**Parameters:**

- `filter` (dict, optional) — MongoDB filter criteria
- `**kwargs` — Additional filter criteria

**Returns:** Document instance or `None` if not found

**Example:**

```python
user = await User.find_one({"email": "alice@example.com"})
```

### update_many()

```python
@classmethod
async def update_many(cls, filter: FilterSpec, update: dict) -> UpdateResult
```

Update multiple documents matching the filter.

**Parameters:**

- `filter` (dict) — MongoDB filter criteria
- `update` (dict) — MongoDB update operators and values

**Returns:** `UpdateResult` with `modified_count` and other metadata

**Example:**

```python
result = await User.update_many(
    {"active": False},
    {"$set": {"active": True}}
)
print(result.modified_count)
```

### delete_many()

```python
@classmethod
async def delete_many(cls, filter: FilterSpec) -> DeleteResult
```

Delete multiple documents matching the filter.

**Parameters:**

- `filter` (dict) — MongoDB filter criteria

**Returns:** `DeleteResult` with `deleted_count`

**Example:**

```python
result = await User.delete_many({"archived": True})
print(result.deleted_count)
```

### create_indexes()

```python
@classmethod
async def create_indexes(cls) -> None
```

Create all indexes defined in the document's `Settings.indexes`.

**Example:**

```python
await User.create_indexes()
```

## QuerySet methods

### filter()

```python
def filter(self, filter: FilterSpec | None = None, **kwargs) -> QuerySet[T]
```

Add filter conditions. Merges with existing filters.

**Parameters:**

- `filter` (dict, optional) — MongoDB filter criteria
- `**kwargs` — Filter criteria as keyword arguments

**Returns:** New `QuerySet` instance

### sort()

```python
def sort(self, *fields: str) -> QuerySet[T]
```

Set sort order. Prefix field names with `-` for descending order.

**Parameters:**

- `*fields` — Field names to sort by

**Returns:** New `QuerySet` instance

**Example:**

```python
users = await User.find().sort("name", "-created_at").all()
```

### skip()

```python
def skip(self, n: int) -> QuerySet[T]
```

Skip the first n documents.

**Parameters:**

- `n` (int) — Number of documents to skip

**Returns:** New `QuerySet` instance

### limit()

```python
def limit(self, n: int) -> QuerySet[T]
```

Limit results to n documents.

**Parameters:**

- `n` (int) — Maximum number of documents to return

**Returns:** New `QuerySet` instance

### project()

```python
def project(self, **fields: int) -> QuerySet[T]
```

Select specific fields in results.

**Parameters:**

- `**fields` — Field names mapped to 1 (include) or 0 (exclude)

**Returns:** New `QuerySet` instance

### populate()

```python
def populate(self, *fields: str) -> QuerySet[T]
```

Resolve references by fetching referenced documents.

**Parameters:**

- `*fields` — Field names to populate, supports dot notation for nested fields

**Returns:** New `QuerySet` instance

**Example:**

```python
order = await Order.find().populate("user", "user.orders").first()
```

### all()

```python
async def all(self) -> list[T]
```

Execute the query and return all matching documents.

**Returns:** List of documents

### first()

```python
async def first(self) -> T | None
```

Execute the query and return the first document or `None`.

**Returns:** Document instance or `None`

### count()

```python
async def count(self) -> int
```

Execute the query and return the number of matching documents.

**Returns:** Document count

### exists()

```python
async def exists(self) -> bool
```

Execute the query and return whether any documents match.

**Returns:** `True` if at least one document matches, `False` otherwise

## Encryption functions

### generate_encryption_key()

```python
def generate_encryption_key() -> str
```

Generate a new encryption key.

**Returns:** Base64-encoded encryption key

**Example:**

```python
from pygoose import generate_encryption_key

key = generate_encryption_key()
# Save key securely!
```

### set_encryption_key()

```python
def set_encryption_key(key: str) -> None
```

Set the global encryption key for encrypted fields.

**Parameters:**

- `key` (str) — Base64-encoded encryption key

**Example:**

```python
from pygoose import set_encryption_key

set_encryption_key("your-base64-encoded-key")
```

## Hook decorators

All hook decorators have the same signature:

```python
def hook_decorator(fn: Callable) -> Callable
```

Available decorators:

- `@pre_validate` — Runs before field validation
- `@pre_save` — Runs before saving to MongoDB
- `@post_save` — Runs after successful save
- `@pre_delete` — Runs before deleting from MongoDB
- `@post_delete` — Runs after successful delete
- `@post_update` — Runs after update operations

All hooks are async functions.

## Plugin mixins

### TimestampsMixin

Adds `created_at` and `updated_at` fields automatically.

```python
from pygoose import Document, TimestampsMixin

class Article(Document, TimestampsMixin):
    title: str
```

### SoftDeleteMixin

Marks documents as deleted without removing them from MongoDB.

```python
from pygoose import Document, SoftDeleteMixin

class User(Document, SoftDeleteMixin):
    name: str
```

Additional method: `include_deleted()` on `QuerySet` to include soft-deleted
documents.

### AuditMixin

Tracks who created and modified documents.

```python
from pygoose import Document, AuditMixin

class Article(Document, AuditMixin):
    title: str
```

Functions:

- `set_audit_context(user_id: str, request_id: str)` — Set current request
  context
- `get_audit_context()` — Get current context
- `clear_audit_context()` — Clear current context

## Observability

### enable_tracing()

```python
def enable_tracing() -> None
```

Enable query tracing for all operations.

### disable_tracing()

```python
def disable_tracing() -> None
```

Disable query tracing.

### add_listener()

```python
def add_listener(callback: Callable[[QueryEvent], None]) -> None
```

Add a callback to receive query events when tracing is enabled.

**Parameters:**

- `callback` — Function that receives `QueryEvent` objects

### QueryEvent

Event fired for each MongoDB operation when tracing is enabled.

**Attributes:**

- `operation` (str) — Operation type (find, insert, update, delete, etc.)
- `collection` (str) — Collection name
- `filter` (dict) — Query filter (if applicable)
- `duration_ms` (float) — Operation duration in milliseconds

## Exceptions

### PygooseError

Base exception for all Pygoose errors.

### DocumentNotFound

Raised when a document query returns no results but one was expected.

### MultipleDocumentsFound

Raised when a single-document operation finds multiple documents.

### NotConnected

Raised when a document operation runs without an active connection.

## Next steps

- [FastAPI integration](FASTAPI_INTEGRATION.md) — Integrate with FastAPI
- [Advanced features](ADVANCED_FEATURES.md) — Lifecycle hooks and plugins
