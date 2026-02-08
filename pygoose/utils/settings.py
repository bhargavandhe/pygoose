"""Settings resolution utilities for Document configuration."""

from __future__ import annotations

from typing import Any


def _pluralize(name: str) -> str:
    """Naive pluralization for collection names.

    Args:
        name: Singular class name

    Returns:
        Pluralized collection name
    """
    lower = name.lower()
    if lower.endswith("s"):
        return lower + "es"
    if lower.endswith("y") and not lower.endswith(("ay", "ey", "iy", "oy", "uy")):
        return lower[:-1] + "ies"
    return lower + "s"


class SettingsResolver:
    """Resolves document settings from inner Settings class."""

    @staticmethod
    def get_collection_name(cls: type) -> str:
        """Get collection name from Settings or auto-pluralize.

        Args:
            cls: Document class

        Returns:
            Collection name
        """
        settings = getattr(cls, "Settings", None)
        if settings and hasattr(settings, "collection"):
            return settings.collection
        return _pluralize(cls.__name__)

    @staticmethod
    def get_connection_alias(cls: type) -> str:
        """Get connection alias from Settings or default.

        Args:
            cls: Document class

        Returns:
            Connection alias name
        """
        settings = getattr(cls, "Settings", None)
        if settings and hasattr(settings, "connection_alias"):
            return settings.connection_alias
        return "default"

    @staticmethod
    def get_auto_populate_fields(cls: type) -> list[str]:
        """Get auto-populate field list from Settings.

        Args:
            cls: Document class

        Returns:
            List of field names to auto-populate
        """
        settings = getattr(cls, "Settings", None)
        if settings and hasattr(settings, "auto_populate"):
            return list(settings.auto_populate)
        return []

    @staticmethod
    def get_indexes(cls: type) -> list[Any]:
        """Get index specifications from Settings.

        Args:
            cls: Document class

        Returns:
            List of index specifications
        """
        settings = getattr(cls, "Settings", None)
        if settings and hasattr(settings, "indexes"):
            return settings.indexes
        return []
