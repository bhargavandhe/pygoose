from typing import Any, TypeVar, Protocol
from bson import ObjectId

# Type aliases for better clarity
DocumentData = dict[str, Any]
FilterSpec = dict[str, Any]
SortSpec = list[tuple[str, int]]
UpdateSpec = dict[str, Any]
DocumentId = ObjectId | str

# Generic type variable for documents
T = TypeVar("T")

# Constants
MAX_POPULATE_DEPTH = 5  # Maximum depth for nested population


def merge_filters(
    base: FilterSpec | None = None,
    override: FilterSpec | None = None,
    **kwargs: Any
) -> FilterSpec:
    """Merge multiple filter dictionaries with proper precedence.

    Args:
        base: Base filter dict
        override: Override filter dict (takes precedence over base)
        **kwargs: Additional filters (highest precedence)

    Returns:
        Merged filter dictionary
    """
    return {**(base or {}), **(override or {}), **kwargs}
