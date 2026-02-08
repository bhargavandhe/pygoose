# Pygoose documentation

Welcome to Pygoose, an async-first MongoDB object-document mapper (ODM) for
Python. These docs guide you through installation, core concepts, and advanced
features.

## Getting started

New to Pygoose? Start here:

- [Getting started](GETTING_STARTED.md) — Install, connect, and create your
  first documents
- [Core concepts](CORE_CONCEPTS.md) — Understand Documents, QuerySet, and
  References

## Using Pygoose

Learn how to use Pygoose's features:

- [Advanced features](ADVANCED_FEATURES.md) — Lifecycle hooks, encryption,
  indexes, plugins, multi-database setups, and observability
- [API reference](API_REFERENCE.md) — Complete method and class documentation
- [FastAPI integration](FASTAPI_INTEGRATION.md) — Build REST APIs with FastAPI
- [Examples](EXAMPLES.md) — Real-world patterns and use cases

## Key features

- **Async-first:** Built for async/await from the ground up using PyMongo's
  async client
- **Pydantic-native:** Use Pydantic v2 models directly as your documents
- **Type-safe:** Full type hints for queries, documents, and relationships
- **QuerySet:** Fluent, lazy query builder inspired by Django
- **References:** Type-safe document references with automatic population
- **Hooks:** Lifecycle hooks for validation, encryption, and custom logic
- **Encryption:** Field-level encryption for sensitive data
- **Plugins:** Built-in plugins for timestamps, soft delete, and audit trails
- **FastAPI:** First-class FastAPI integration with exception handling and
  schema generation

## Installation

```bash
pip install pygoose
```

Optional dependencies:

```bash
# For field-level encryption
pip install pygoose[encryption]

# For FastAPI integration
pip install pygoose[fastapi]
```

## Quick start

```python
from fastapi import FastAPI
from pygoose import connect, disconnect, Document, init_app

app = FastAPI()
init_app(app)

class User(Document):
    name: str
    email: str

@app.on_event("startup")
async def startup():
    await connect("mongodb://localhost:27017/my_database")

@app.on_event("shutdown")
async def shutdown():
    await disconnect()

@app.post("/users")
async def create_user(user: User):
    await user.save()
    return user

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    from bson import ObjectId
    user = await User.find_one({"_id": ObjectId(user_id)})
    return user
```

## FAQ

### Can I use Pygoose with async frameworks other than FastAPI?

Yes, Pygoose is framework-agnostic. Use it with Starlette, AioHTTP, Quart, or
any async Python framework.

### Does Pygoose support transactions?

Pygoose doesn't wrap MongoDB transactions yet. For now, you can use the
underlying PyMongo async client for transaction support.

### How do I use MongoDB aggregation pipelines?

Access the underlying PyMongo collection to run aggregations:

```python
from pygoose import get_database

db = get_database()
pipeline = [
    {"$match": {"status": "active"}},
    {"$group": {"_id": "$category", "count": {"$sum": 1}}},
]
result = await db.users.aggregate(pipeline).to_list(None)
```

### Can I customize the collection name?

Yes, use the `Settings` inner class:

```python
class User(Document):
    name: str

    class Settings:
        collection = "users_v1"
```

### How do I run multiple queries in parallel?

Use Python's `asyncio.gather()`:

```python
import asyncio

users = await asyncio.gather(
    User.find_one({"_id": user_id1}),
    User.find_one({"_id": user_id2}),
    User.find_one({"_id": user_id3}),
)
```

## Support

For issues, feature requests, or questions, visit the GitHub repository or
check existing discussions.

## Next steps

- [Getting started](GETTING_STARTED.md) — Begin with the basics
- [API reference](API_REFERENCE.md) — Explore the full API
- [Examples](EXAMPLES.md) — See real-world use cases
