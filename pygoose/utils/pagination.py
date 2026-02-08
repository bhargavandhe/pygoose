from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    """Offset-based pagination result."""

    items: list[T]
    page: int
    size: int
    total: int
    has_next: bool
    has_prev: bool
    total_pages: int


@dataclass(frozen=True)
class CursorPage(Generic[T]):
    """Cursor-based pagination result using _id."""

    items: list[T]
    size: int
    next_cursor: str | None
    has_next: bool
