from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import Field


class TimestampsMixin:
    """Mixin that automatically manages created_at and updated_at fields.

    Usage: class User(TimestampsMixin, Document): ...
    """

    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    async def insert(self) -> None:
        now = datetime.now(timezone.utc)
        object.__setattr__(self, "created_at", now)
        object.__setattr__(self, "updated_at", now)
        await super().insert()

    async def save(self) -> None:
        if not self._is_new and self.is_dirty:
            now = datetime.now(timezone.utc)
            object.__setattr__(self, "updated_at", now)
            self._dirty_fields.add("updated_at")
        await super().save()

    async def update(self, **kwargs: Any) -> None:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        await super().update(**kwargs)
