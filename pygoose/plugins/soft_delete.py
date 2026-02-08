from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

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
    def find(cls, filter: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        """Override find to exclude soft-deleted documents by default."""
        merged = {**(filter or {}), **kwargs, "deleted_at": None}
        return super().find(merged)

    @classmethod
    def find_deleted(cls, filter: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        """Find only soft-deleted documents."""
        merged = {**(filter or {}), **kwargs, "deleted_at": {"$ne": None}}
        from pygoose.core.queryset import QuerySet

        return QuerySet(cls, merged)

    @classmethod
    def find_with_deleted(cls, filter: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        """Find all documents including soft-deleted ones."""
        merged = {**(filter or {}), **kwargs}
        from pygoose.core.queryset import QuerySet

        return QuerySet(cls, merged)
