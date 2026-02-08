from __future__ import annotations

from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Any

from pygoose.core.connection import get_database

_audit_context: ContextVar[dict[str, Any]] = ContextVar("_audit_context", default={})


def set_audit_context(
    *,
    user_id: str | None = None,
    ip_address: str | None = None,
    request_id: str | None = None,
    **extra: Any,
) -> Token:
    """Set per-request audit context. Returns token for reset."""
    ctx = {
        "user_id": user_id,
        "ip_address": ip_address,
        "request_id": request_id,
        **extra,
    }
    return _audit_context.set(ctx)


def get_audit_context() -> dict[str, Any]:
    """Read the current audit context."""
    return _audit_context.get()


def clear_audit_context(token: Token | None = None) -> None:
    """Reset audit context."""
    if token is not None:
        _audit_context.reset(token)
    else:
        _audit_context.set({})


class AuditMixin:
    """Mixin that logs CRUD operations to an _audit_log collection.

    Usage: class User(AuditMixin, Document): ...
    """

    @classmethod
    def _get_audit_collection(cls):
        db = get_database(cls._connection_alias)
        return db["_audit_log"]

    async def _log_audit(
        self,
        operation: str,
        document_id: Any,
        changes: dict | None = None,
        after: dict | None = None,
    ) -> None:
        ctx = get_audit_context()
        entry = {
            "collection": self._collection_name,
            "document_class": self.__class__.__name__,
            "operation": operation,
            "document_id": document_id,
            "timestamp": datetime.now(timezone.utc),
            "user_id": ctx.get("user_id"),
            "ip_address": ctx.get("ip_address"),
            "request_id": ctx.get("request_id"),
        }
        if changes is not None:
            entry["changes"] = changes
        if after is not None:
            entry["after"] = after
        audit_col = self.__class__._get_audit_collection()
        await audit_col.insert_one(entry)

    async def insert(self) -> None:
        await super().insert()
        after = self._to_mongo()
        await self._log_audit("insert", self.id, after=after)

    async def save(self) -> None:
        if self._is_new:
            await self.insert()
            return

        if not self.is_dirty:
            return

        # Capture changes before save clears dirty fields
        changes = {}
        for field_name in self._dirty_fields:
            changes[field_name] = getattr(self, field_name)

        await super().save()
        await self._log_audit("update", self.id, changes=changes)

    async def delete(self) -> None:
        doc_id = self.id
        await super().delete()
        await self._log_audit("delete", doc_id)

    async def update(self, **kwargs: Any) -> None:
        await super().update(**kwargs)
        await self._log_audit("update", self.id, changes=kwargs)
