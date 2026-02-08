from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import Field as PydanticField
from pymongo import ASCENDING


@dataclass
class IndexSpec:
    """Specification for a MongoDB index."""

    fields: str | list[tuple[str, int]]
    unique: bool = False
    sparse: bool = False
    name: str | None = None
    expire_after_seconds: int | None = None

    def to_pymongo(self) -> tuple[list[tuple[str, int]], dict[str, Any]]:
        """Convert to pymongo create_index arguments (keys, kwargs)."""
        if isinstance(self.fields, str):
            keys = [(self.fields, ASCENDING)]
        else:
            keys = self.fields

        kwargs: dict[str, Any] = {}
        if self.unique:
            kwargs["unique"] = True
        if self.sparse:
            kwargs["sparse"] = True
        if self.name:
            kwargs["name"] = self.name
        if self.expire_after_seconds is not None:
            kwargs["expireAfterSeconds"] = self.expire_after_seconds

        return keys, kwargs


def Indexed(
    default: Any = ...,
    *,
    unique: bool = False,
    sparse: bool = False,
    index_direction: int = ASCENDING,
    **kwargs: Any,
) -> Any:
    """Field wrapper that marks a field for automatic index creation.

    Usage: name: str = Indexed(unique=True)
    """
    index_meta = {
        "_pygoose_index": True,
        "_index_unique": unique,
        "_index_sparse": sparse,
        "_index_direction": index_direction,
    }

    field_kwargs: dict[str, Any] = {**kwargs}
    if default is not ...:
        field_kwargs["default"] = default

    field_kwargs["json_schema_extra"] = index_meta
    return PydanticField(**field_kwargs)
