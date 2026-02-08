# FastAPI integration

Pygoose provides first-class FastAPI integration for building REST APIs on top of
MongoDB.

## Setup

First, initialize Pygoose in your FastAPI application:

```python
from fastapi import FastAPI
from pygoose import connect, disconnect, init_app

app = FastAPI()

# Initialize Pygoose for FastAPI
init_app(app)

@app.on_event("startup")
async def startup():
    await connect("mongodb://localhost:27017/my_database")

@app.on_event("shutdown")
async def shutdown():
    await disconnect()
```

`init_app()` sets up exception handlers and other FastAPI-specific features.

## Exception handling

Pygoose automatically converts exceptions to appropriate HTTP responses:

- `DocumentNotFound` — 404 Not Found
- `MultipleDocumentsFound` — 500 Internal Server Error
- `NotConnected` — 503 Service Unavailable
- `ValidationError` — 422 Unprocessable Entity

You don't need to manually handle these exceptions in your route handlers.

## Path parameters

Use document IDs in path parameters:

```python
from fastapi import FastAPI, Path
from bson import ObjectId

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: str = Path(...)):
    # Convert string ID to ObjectId
    user = await User.find_one({"_id": ObjectId(user_id)})
    return user
```

## Request/response models

Use Pygoose documents directly as request and response models:

```python
from fastapi import FastAPI

app = FastAPI()

@app.post("/users")
async def create_user(user: User):
    await user.save()
    return user

@app.put("/users/{user_id}")
async def update_user(user_id: str, data: User):
    user = await User.find_one({"_id": ObjectId(user_id)})
    # Update fields from request
    user.name = data.name
    user.email = data.email
    await user.save()
    return user
```

## Pagination

Use the `Page` and `CursorPage` classes for pagination:

```python
from fastapi import FastAPI, Query
from pygoose import Page, CursorPage

app = FastAPI()

@app.get("/users", response_model=Page[User])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    users = await User.find().skip(skip).limit(limit).all()
    total = await User.find().count()
    return Page(items=users, total=total, skip=skip, limit=limit)

@app.get("/users/paginated", response_model=CursorPage[User])
async def list_users_cursor(
    cursor: str | None = Query(None),
    limit: int = Query(10, ge=1, le=100)
):
    # Cursor-based pagination for better performance
    query = User.find().sort("_id").limit(limit + 1)
    if cursor:
        query = query.filter({"_id": {"$gt": ObjectId(cursor)}})

    users = await query.all()
    has_more = len(users) > limit
    items = users[:limit]

    next_cursor = None
    if has_more and items:
        next_cursor = str(items[-1].id)

    return CursorPage(items=items, cursor=cursor, next_cursor=next_cursor)
```

## Dependency injection

Use FastAPI dependencies with Pygoose:

```python
from fastapi import Depends

async def get_current_user(user_id: str) -> User:
    user = await User.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise DocumentNotFound(f"User {user_id} not found")
    return user

@app.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    return user
```

## Schema generation

Generate OpenAPI schemas from your documents:

```python
from pygoose.fastapi import get_model_schema

user_schema = get_model_schema(User)
print(user_schema)  # OpenAPI schema dict
```

Pygoose automatically generates schemas for all Pydantic fields.

## Handling relationships

When returning documents with references, use population:

```python
@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    order = await (
        Order
        .find({"_id": ObjectId(order_id)})
        .populate("user", "items")
        .first()
    )
    return order
```

The response includes fully resolved references.

## Audit context in requests

Set audit context for tracking changes:

```python
from fastapi import FastAPI, Request
from pygoose import set_audit_context

@app.middleware("http")
async def add_audit_context(request: Request, call_next):
    # Extract user ID from token or session
    user_id = request.headers.get("X-User-ID")
    request_id = request.headers.get("X-Request-ID")

    set_audit_context(user_id=user_id, request_id=request_id)

    response = await call_next(request)
    return response
```

Now all document changes in this request are automatically tracked with the user
and request IDs.

## Error handling

Handle Pygoose exceptions explicitly:

```python
from fastapi import FastAPI, HTTPException
from pygoose import DocumentNotFound

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    try:
        user = await User.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise DocumentNotFound(f"User {user_id} not found")
        return user
    except DocumentNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
```

Or rely on the automatic exception handlers registered by `init_app()`.

## CORS and middleware

Pygoose works seamlessly with FastAPI middleware:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Testing

Test your FastAPI app with Pygoose documents:

```python
from fastapi.testclient import TestClient
import pytest

@pytest.fixture
async def client():
    await connect("mongodb://localhost:27017/test_db")
    yield TestClient(app)
    await disconnect()

def test_create_user(client):
    response = client.post("/users", json={
        "name": "Alice",
        "email": "alice@example.com"
    })
    assert response.status_code == 200
    assert response.json()["name"] == "Alice"
```

## Next steps

- [Advanced features](ADVANCED_FEATURES.md) — Lifecycle hooks and plugins
- [API reference](API_REFERENCE.md) — Complete API documentation
