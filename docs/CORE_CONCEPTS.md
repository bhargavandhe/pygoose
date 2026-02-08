# Core concepts

Pygoose provides several core abstractions for working with MongoDB. This guide
explains how they work together.

## Documents

A document is a Pydantic model that maps to a single MongoDB collection. It
extends the `Document` base class and provides CRUD operations out of the box.

```python
from pygoose import Document
from pydantic import Field
from typing import Optional

class Product(Document):
    name: str
    price: float
    description: Optional[str] = None
    in_stock: bool = True
```

Every document automatically has an `id` field (aliased to `_id` in MongoDB)
that holds the document's ObjectId. This field is populated when you save the
document for the first time.

## CRUD operations

### Create

Create a new document by instantiating your class and calling `save()`:

```python
product = Product(name="Widget", price=9.99)
await product.save()
print(product.id)  # ObjectId(...)
```

### Read

Find documents using the `find()` method, which returns a `QuerySet`:

```python
# Single document
product = await Product.find_one({"name": "Widget"})

# Multiple documents
products = await Product.find(price={"$gt": 5}).all()

# First document matching a filter
first = await Product.find().first()
```

### Update

Modify a document and save it:

```python
product = await Product.find_one({"name": "Widget"})
product.price = 10.99
await product.save()
```

Or update multiple documents at once using MongoDB operators:

```python
result = await Product.update_many(
    {"in_stock": False},
    {"$set": {"in_stock": True}}
)
print(result.modified_count)  # Number of documents updated
```

### Delete

Remove a document:

```python
product = await Product.find_one({"name": "Widget"})
await product.delete()
```

Or delete multiple documents:

```python
await Product.delete_many({"price": {"$lt": 1.00}})
```

## QuerySet

`QuerySet` is a fluent, lazy query builder that allows you to chain query
methods. Queries execute only when you call a terminal method (like `all()`,
`first()`, or `count()`).

### Filtering

Apply conditions to narrow results:

```python
# Single condition
expensive = Product.find(price={"$gte": 100})

# Multiple conditions
products = (
    Product
    .find(in_stock=True)
    .find(price={"$lt": 50})
)

# Using kwargs
products = Product.find(in_stock=True, name="Widget")
```

### Sorting

Order results by one or more fields. Prefix field names with `-` for descending
order:

```python
# Ascending
products = await Product.find().sort("price").all()

# Descending
products = await Product.find().sort("-price").all()

# Multiple fields
products = await Product.find().sort("in_stock", "-price").all()
```

### Pagination

Use `skip()` and `limit()` for pagination:

```python
# Get page 2 (10 items per page)
page = 2
page_size = 10
products = await (
    Product
    .find()
    .skip((page - 1) * page_size)
    .limit(page_size)
    .all()
)
```

### Projections

Select specific fields to reduce memory usage:

```python
# Return only name and price
products = await (
    Product
    .find()
    .project(name=1, price=1)
    .all()
)
```

### Terminal methods

Terminal methods execute the query and return results:

```python
# Get all documents
products = await Product.find().all()

# Get the first document
product = await Product.find().first()

# Count documents
count = await Product.find(in_stock=True).count()

# Check if any document exists
exists = await Product.find({"price": {"$gte": 100}}).exists()
```

## References

Reference documents to other documents using the `Ref[T]` type. This creates a
many-to-one relationship where one document can reference another.

```python
from pygoose import Ref

class User(Document):
    name: str
    email: str

class Order(Document):
    user: Ref[User]
    total: float
```

When you save an `Order`, the `user` field stores the User's ObjectId in
MongoDB. To retrieve the actual User object, use population (explained below).

### Creating references

Reference documents by assigning either an ObjectId, a Document instance, or a
string ID:

```python
user = await User.find_one({"name": "Alice"})

# Option 1: Assign the document instance
order = Order(user=user, total=99.99)

# Option 2: Assign the ObjectId
order = Order(user=user.id, total=99.99)

# Option 3: Assign a string ObjectId
order = Order(user="507f1f77bcf86cd799439011", total=99.99)

await order.save()
```

### Population

Population resolves references by fetching the referenced documents from
MongoDB. Use the `populate()` method:

```python
# Fetch an order without population
order = await Order.find_one()
print(order.user)  # ObjectId(...)

# Fetch with population
order = await Order.find().populate("user").first()
print(order.user)  # User instance
print(order.user.name)  # Alice
```

You can also populate nested references using dot notation:

```python
order = await Order.find().populate("user", "user.orders").first()
```

## Dirty tracking

Pygoose automatically tracks which fields have changed since a document was
loaded from the database. This allows efficient updates that only write changed
fields.

When you call `save()` on a document that was fetched from MongoDB, it only
updates the fields you modified:

```python
# Fetch from database
product = await Product.find_one({"name": "Widget"})

# Modify a field
product.price = 10.99

# Only the price field is updated in MongoDB
await product.save()
```

For new documents (not yet saved), all fields are written.

## Model validation

Documents use Pydantic for data validation. Define validation rules using
Pydantic's standard features:

```python
from pydantic import Field, field_validator

class Product(Document):
    name: str = Field(..., min_length=1, max_length=200)
    price: float = Field(..., gt=0)

    @field_validator("name")
    @classmethod
    def name_lowercase(cls, v):
        return v.lower()
```

Validation runs automatically before save and before insertion.

## Collection settings

Use the `Settings` inner class to customize document behavior:

```python
class Product(Document):
    name: str
    price: float

    class Settings:
        # Custom collection name (default: lowercased plural class name)
        collection = "products_v1"

        # Use a non-default connection (for multi-database setups)
        connection_alias = "db2"

        # Auto-populate these fields on every find() query
        auto_populate = ["supplier"]
```

## Next steps

Learn about advanced features:

- [Advanced features](ADVANCED_FEATURES.md) — Lifecycle hooks, encryption, and
  more
- [API reference](API_REFERENCE.md) — Complete API documentation
