# Getting started with Pygoose

Pygoose is an async-first MongoDB object-document mapper (ODM) for Python,
inspired by Mongoose. It provides a clean, Pydantic-native API for working with
MongoDB collections as typed Python classes.

## Installation

Install Pygoose using your package manager:

```bash
pip install pygoose
```

For optional features, you can install extras:

```bash
# For field-level encryption
pip install pygoose[encryption]

# For FastAPI integration
pip install pygoose[fastapi]

# For development
pip install pygoose[dev]
```

## Prerequisites

You'll need a MongoDB instance running locally or accessible via a connection
URI. Pygoose requires Python 3.11 or higher.

## Your first document

Create a Pydantic model that extends the `Document` base class to define a
MongoDB collection:

```python
from pygoose import Document
from pydantic import Field
from typing import Optional

class User(Document):
    name: str
    email: str
    age: Optional[int] = None
```

Pygoose automatically derives the collection name from your class name using
naive pluralization. `User` becomes `users`.

## Connect to MongoDB

Before you can use your documents, establish a connection to MongoDB:

```python
import asyncio
from pygoose import connect, disconnect

async def main():
    # Connect to MongoDB
    db = await connect("mongodb://localhost:27017/my_database")

    # Your code here...

    # Disconnect when done
    await disconnect()

asyncio.run(main())
```

The connection URI must include a database name. Pass the `alias` parameter to
manage multiple connections:

```python
await connect("mongodb://localhost:27017/db1", alias="db1")
await connect("mongodb://localhost:27017/db2", alias="db2")
```

## Create and save documents

Create instances of your document class and save them to MongoDB:

```python
async def main():
    await connect("mongodb://localhost:27017/my_database")

    # Create a new user
    user = User(name="Alice", email="alice@example.com", age=30)

    # Save to MongoDB
    await user.save()

    # The id field is now populated
    print(user.id)  # ObjectId(...)

    await disconnect()

asyncio.run(main())
```

## Query documents

Use the fluent `QuerySet` API to find documents:

```python
async def main():
    await connect("mongodb://localhost:27017/my_database")

    # Find a single document
    user = await User.find_one({"email": "alice@example.com"})

    # Find multiple documents
    users = await User.find().all()

    # Chain query methods
    active_adults = await (
        User
        .find(age={"$gte": 18})
        .sort("name")
        .limit(10)
        .all()
    )

    await disconnect()

asyncio.run(main())
```

## Update documents

Modify documents and persist changes:

```python
async def main():
    await connect("mongodb://localhost:27017/my_database")

    user = await User.find_one({"email": "alice@example.com"})
    user.age = 31

    # Save the updated document
    await user.save()

    # Or update directly using operators
    result = await User.update_many(
        {"age": {"$lt": 18}},
        {"$set": {"age": 18}}
    )

    await disconnect()

asyncio.run(main())
```

## Delete documents

Remove documents from your collection:

```python
async def main():
    await connect("mongodb://localhost:27017/my_database")

    user = await User.find_one({"email": "alice@example.com"})
    await user.delete()

    # Or delete multiple documents
    await User.delete_many({"age": {"$lt": 18}})

    await disconnect()

asyncio.run(main())
```

## Custom collection names

Override the auto-generated collection name using the `Settings` inner class:

```python
class User(Document):
    name: str
    email: str

    class Settings:
        collection = "users_v2"
```

## Next steps

Learn more about Pygoose's features:

- [Core concepts](CORE_CONCEPTS.md) — Understand Documents, QuerySet, and
  references
- [Advanced features](ADVANCED_FEATURES.md) — Hooks, encryption, and plugins
- [FastAPI integration](FASTAPI_INTEGRATION.md) — Use Pygoose in FastAPI
  applications
