from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from pydantic import Field


class SoftDeleteMixin:
    """Mixin that replaces delete() with a soft-delete (sets deleted_at).

    Usage: class User(SoftDeleteMixin, Document): ...

    Provides:
    - deleted_at: Optional[datetime] - timestamp when deleted
    - deleted: bool - property that returns True if deleted_at is set
    - delete(): soft delete (sets deleted_at)
    - restore(): undelete (clears deleted_at)
    - hard_delete(): permanently remove from database
    """

    deleted_at: Optional[datetime] = Field(default=None)

    @property
    def deleted(self) -> bool:
        """Check if document is soft-deleted."""
        return self.deleted_at is not None

    async def delete(self) -> None:
        """Soft-delete: set deleted_at instead of removing the document."""
        from pygoose.lifecycle.hooks import PRE_DELETE, POST_DELETE, run_hooks

        await run_hooks(self, PRE_DELETE)
        collection = self.get_collection()
        now = datetime.now(timezone.utc)
        await collection.update_one({"_id": self.id}, {"$set": {"deleted_at": now}})
        object.__setattr__(self, "deleted_at", now)
        await run_hooks(self, POST_DELETE)

    async def hard_delete(self) -> None:
        """Permanently remove the document from the database."""
        collection = self.get_collection()
        await collection.delete_one({"_id": self.id})

    async def restore(self) -> None:
        """Restore a soft-deleted document by unsetting deleted_at."""
        collection = self.get_collection()
        await collection.update_one({"_id": self.id}, {"$unset": {"deleted_at": ""}})
        object.__setattr__(self, "deleted_at", None)

    @classmethod
    def find(cls, filter: dict[str, Any] | str | ObjectId | None = None, **kwargs: Any) -> Any:
        """Override find to exclude soft-deleted documents by default.

        Args:
            filter: MongoDB filter dict, ObjectId string, or ObjectId instance
            **kwargs: Additional filter criteria

        Examples:
            User.find("507f1f77bcf86cd799439011")  # Find by ID (non-deleted)
            User.find({"age": {"$gte": 18}})  # Find by filter (non-deleted)
        """
        # Handle string/ObjectId shortcuts
        if isinstance(filter, str):
            filter = {"_id": ObjectId(filter)}
        elif isinstance(filter, ObjectId):
            filter = {"_id": filter}

        merged = {**(filter or {}), **kwargs, "deleted_at": None}
        return super().find(merged)

    @classmethod
    def find_deleted(cls, filter: dict[str, Any] | str | ObjectId | None = None, **kwargs: Any) -> Any:
        """Find only soft-deleted documents.

        Args:
            filter: MongoDB filter dict, ObjectId string, or ObjectId instance
            **kwargs: Additional filter criteria

        Examples:
            User.find_deleted("507f1f77bcf86cd799439011")  # Find deleted by ID
            User.find_deleted({"age": {"$gte": 18}})  # Find deleted by filter
        """
        from pygoose.core.queryset import QuerySet

        # Handle string/ObjectId shortcuts
        if isinstance(filter, str):
            filter = {"_id": ObjectId(filter)}
        elif isinstance(filter, ObjectId):
            filter = {"_id": filter}

        merged = {**(filter or {}), **kwargs, "deleted_at": {"$ne": None}}
        return QuerySet(cls, merged)

    @classmethod
    def find_with_deleted(cls, filter: dict[str, Any] | str | ObjectId | None = None, **kwargs: Any) -> Any:
        """Find all documents including soft-deleted ones.

        Args:
            filter: MongoDB filter dict, ObjectId string, or ObjectId instance
            **kwargs: Additional filter criteria

        Examples:
            User.find_with_deleted("507f1f77bcf86cd799439011")  # Find by ID (any)
            User.find_with_deleted({"age": {"$gte": 18}})  # Find by filter (any)
        """
        from pygoose.core.queryset import QuerySet

        # Handle string/ObjectId shortcuts
        if isinstance(filter, str):
            filter = {"_id": ObjectId(filter)}
        elif isinstance(filter, ObjectId):
            filter = {"_id": filter}

        merged = {**(filter or {}), **kwargs}
        return QuerySet(cls, merged)
