from __future__ import annotations

from typing import Any, Generic, TypeVar

import math

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from pygoose.utils.exceptions import PygooseError
from pygoose.lifecycle.observability import track_query
from pygoose.utils.pagination import CursorPage, Page
from pygoose.utils.types import FilterSpec, SortSpec

T = TypeVar("T")


class QuerySet(Generic[T]):
    """Fluent, lazy, immutable query builder for MongoDB documents.

    Each chainable method returns a new QuerySet instance.
    Queries are only executed when a terminal method is called.
    """

    def __init__(
        self,
        document_class: type[T],
        filter: FilterSpec | None = None,
        sort: SortSpec | None = None,
        skip_count: int = 0,
        limit_count: int = 0,
        projection: dict[str, int] | None = None,
        populate_fields: list[str] | None = None,
    ) -> None:
        self._document_class = document_class
        self._filter: FilterSpec = filter or {}
        self._sort: SortSpec = sort or []
        self._skip_count = skip_count
        self._limit_count = limit_count
        self._projection = projection
        self._populate_fields: list[str] = populate_fields or []

    def _clone(self, **overrides: Any) -> QuerySet[T]:
        """Return a new QuerySet with merged overrides."""
        defaults = {
            "document_class": self._document_class,
            "filter": self._filter.copy(),
            "sort": self._sort.copy(),
            "skip_count": self._skip_count,
            "limit_count": self._limit_count,
            "projection": self._projection.copy() if self._projection else None,
            "populate_fields": self._populate_fields.copy(),
        }
        defaults.update(overrides)
        return QuerySet(**defaults)

    # --- Chainable methods ---

    def filter(self, _filter: FilterSpec | str | ObjectId | None = None, **kwargs: Any) -> QuerySet[T]:
        """Add filter conditions. Merges with existing filter.

        Args:
            _filter: MongoDB filter dict, ObjectId string, or ObjectId instance
            **kwargs: Additional filter criteria

        Examples:
            User.find().filter("507f1f77bcf86cd799439011")  # Filter by ID string
            User.find().filter(ObjectId("507f1f77bcf86cd799439011"))  # Filter by ObjectId
            User.find(age=18).filter({"city": "NYC"})  # Chain filters
        """
        from pygoose.utils.types import merge_filters

        # Handle string/ObjectId shortcuts
        if isinstance(_filter, str):
            _filter = {"_id": ObjectId(_filter)}
        elif isinstance(_filter, ObjectId):
            _filter = {"_id": _filter}

        merged = merge_filters(self._filter, _filter, **kwargs)
        return self._clone(filter=merged)

    def sort(self, *fields: str) -> QuerySet[T]:
        """Set sort order. Prefix with '-' for descending.

        Example: .sort("-created_at", "name")
        """
        sort_spec: SortSpec = []
        for field in fields:
            if field.startswith("-"):
                sort_spec.append((field[1:], DESCENDING))
            else:
                sort_spec.append((field, ASCENDING))
        return self._clone(sort=sort_spec)

    def skip(self, n: int) -> QuerySet[T]:
        return self._clone(skip_count=n)

    def limit(self, n: int) -> QuerySet[T]:
        return self._clone(limit_count=n)

    def select(self, *fields: str) -> QuerySet[T]:
        """Set field projection."""
        projection = {f: 1 for f in fields}
        # Always include _id
        projection["_id"] = 1
        return self._clone(projection=projection)

    def populate(self, *fields: str) -> QuerySet[T]:
        """Mark reference fields to be populated after query execution."""
        merged = self._populate_fields + list(fields)
        return self._clone(populate_fields=merged)

    # --- Terminal methods ---

    async def all(self) -> list[T]:
        """Execute the query and return all matching documents."""
        async with track_query("find", self._document_class._collection_name, self._document_class.__name__, filter=self._filter) as ctx:
            cursor = self._build_cursor()
            results = []
            async for raw in cursor:
                doc = self._document_class._from_mongo(raw)
                results.append(doc)
            ctx["result_count"] = len(results)

        # Run populate if requested
        if self._populate_fields and results:
            from pygoose.core.reference import PopulateEngine

            engine = PopulateEngine()
            for field in self._populate_fields:
                if "." in field:
                    await engine.populate_nested(results, field)
                else:
                    await engine.populate_many(results, field)

        return results

    async def first(self) -> T | None:
        """Return the first matching document, or None."""
        qs = self.limit(1)
        results = await qs.all()
        return results[0] if results else None

    async def count(self) -> int:
        """Count matching documents."""
        async with track_query("count", self._document_class._collection_name, self._document_class.__name__, filter=self._filter) as ctx:
            collection = self._document_class.get_collection()
            result = await collection.count_documents(self._filter)
            ctx["result_count"] = result
        return result

    async def exists(self) -> bool:
        """Check if any matching documents exist."""
        return await self.count() > 0

    async def distinct(self, field: str) -> list[Any]:
        """Return distinct values for a field."""
        async with track_query("distinct", self._document_class._collection_name, self._document_class.__name__, filter=self._filter):
            collection = self._document_class.get_collection()
            return await collection.distinct(field, self._filter)

    async def update_many(self, **kwargs: Any) -> int:
        """Bulk $set update on matching documents. Returns modified count."""
        async with track_query("update_many", self._document_class._collection_name, self._document_class.__name__, filter=self._filter, update=kwargs) as ctx:
            collection = self._document_class.get_collection()
            result = await collection.update_many(self._filter, {"$set": kwargs})
            ctx["result_count"] = result.modified_count
        return result.modified_count

    async def delete_many(self) -> int:
        """Delete all matching documents. Raises if filter is empty (safety)."""
        if not self._filter:
            raise PygooseError(
                "Refusing to delete_many with empty filter. "
                "Use filter() to specify conditions."
            )
        async with track_query("delete_many", self._document_class._collection_name, self._document_class.__name__, filter=self._filter) as ctx:
            collection = self._document_class.get_collection()
            result = await collection.delete_many(self._filter)
            ctx["result_count"] = result.deleted_count
        return result.deleted_count

    async def explain(self) -> dict[str, Any]:
        """Return the query execution plan from MongoDB."""
        collection = self._document_class.get_collection()
        find_spec: dict[str, Any] = {
            "find": collection.name,
            "filter": self._filter,
        }
        if self._sort:
            find_spec["sort"] = dict(self._sort)
        if self._skip_count:
            find_spec["skip"] = self._skip_count
        if self._limit_count:
            find_spec["limit"] = self._limit_count
        if self._projection:
            find_spec["projection"] = self._projection

        db = collection.database
        result = await db.command("explain", find_spec, verbosity="executionStats")
        return result

    # --- Pagination ---

    async def paginate(self, page: int = 1, size: int = 20) -> Page[T]:
        """Offset-based pagination. Returns a Page with items and metadata."""
        if page < 1:
            raise ValueError("page must be >= 1")
        if size < 1:
            raise ValueError("size must be >= 1")

        total = await self.count()
        total_pages = math.ceil(total / size) if total > 0 else 0
        items = await self.skip((page - 1) * size).limit(size).all()

        return Page(
            items=items,
            page=page,
            size=size,
            total=total,
            has_next=page < total_pages,
            has_prev=page > 1,
            total_pages=total_pages,
        )

    async def cursor_paginate(self, size: int = 20, after: str | None = None) -> CursorPage[T]:
        """Cursor-based pagination using _id. Always sorts by _id ascending."""
        if size < 1:
            raise ValueError("size must be >= 1")

        filter_spec = self._filter.copy()
        if after is not None:
            filter_spec["_id"] = {"$gt": ObjectId(after)}

        qs = self._clone(filter=filter_spec)
        # Fetch size+1 to detect if there's a next page
        items = await qs.sort("_id").limit(size + 1).all()

        has_next = len(items) > size
        if has_next:
            items = items[:size]

        next_cursor = str(items[-1].id) if has_next and items else None

        return CursorPage(
            items=items,
            size=size,
            next_cursor=next_cursor,
            has_next=has_next,
        )

    # --- Async iteration ---

    async def __aiter__(self):
        cursor = self._build_cursor()
        async for raw in cursor:
            yield self._document_class._from_mongo(raw)

    # --- Internal ---

    def _build_cursor(self):
        """Compose a pymongo cursor from stored query parameters."""
        collection = self._document_class.get_collection()
        cursor = collection.find(self._filter, self._projection)
        if self._sort:
            cursor = cursor.sort(self._sort)
        if self._skip_count:
            cursor = cursor.skip(self._skip_count)
        if self._limit_count:
            cursor = cursor.limit(self._limit_count)
        return cursor
