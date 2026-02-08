# Pygoose

An async-first MongoDB object-document mapper (ODM) for Python, inspired by
Mongoose. Pygoose provides a clean, Pydantic-native API for working with
MongoDB collections as typed Python classes.

## Features

- **Async-first:** Built for async/await from the ground up using PyMongo's
  async client
- **Pydantic-native:** Use Pydantic v2 models directly as your documents
- **Type-safe:** Full type hints for queries, documents, and relationships
- **QuerySet:** Fluent, lazy query builder inspired by Django ORM
- **References:** Type-safe document references with automatic population
- **Lifecycle hooks:** Pre/post validation, save, delete, and update hooks
- **Encryption:** Field-level encryption for sensitive data
- **Plugins:** Built-in plugins for timestamps, soft delete, and audit trails
- **FastAPI:** First-class FastAPI integration with exception handlers and
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

# For development
pip install pygoose[dev]
```

## Quick start

Define your documents as Pydantic models:

```python
from pygoose import Document
from typing import Optional

class User(Document):
    name: str
    email: str
    age: Optional[int] = None
```

Connect to MongoDB and perform CRUD operations:

```python
import asyncio
from pygoose import connect, disconnect

async def main():
    # Connect to MongoDB
    await connect("mongodb://localhost:27017/my_database")

    # Create
    user = User(name="Alice", email="alice@example.com", age=30)
    await user.save()

    # Read
    user = await User.find_one({"email": "alice@example.com"})

    # Update
    user.age = 31
    await user.save()

    # Delete
    await user.delete()

    # Cleanup
    await disconnect()

asyncio.run(main())
```

Use the fluent QuerySet API:

```python
# Find multiple documents
users = await User.find(age={"$gte": 18}).sort("name").limit(10).all()

# Count documents
count = await User.find(age={"$gte": 18}).count()

# Check existence
exists = await User.find({"email": "alice@example.com"}).exists()
```

## FastAPI integration

Pygoose works seamlessly with FastAPI:

```python
from fastapi import FastAPI
from pygoose import connect, disconnect, init_app

app = FastAPI()
init_app(app)

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

## Documentation

Complete documentation is available in the `/docs` directory:

- [Getting started](docs/GETTING_STARTED.md) — Installation and basic usage
- [Core concepts](docs/CORE_CONCEPTS.md) — Documents, QuerySet, and references
- [Advanced features](docs/ADVANCED_FEATURES.md) — Hooks, encryption, and
  plugins
- [API reference](docs/API_REFERENCE.md) — Complete method documentation
- [FastAPI integration](docs/FASTAPI_INTEGRATION.md) — Building REST APIs
- [Examples](docs/EXAMPLES.md) — Real-world patterns and use cases

## Requirements

- Python 3.11 or higher
- MongoDB 4.4 or higher
- PyMongo 4.8 or higher (async driver)
- Pydantic v2 or higher

## License

MIT
