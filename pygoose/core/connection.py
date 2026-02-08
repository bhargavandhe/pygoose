from __future__ import annotations

import logging
import re

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from pygoose.utils.exceptions import NotConnected

logger = logging.getLogger(__name__)

_clients: dict[str, AsyncMongoClient] = {}
_databases: dict[str, AsyncDatabase] = {}


async def connect(uri: str, *, alias: str = "default") -> AsyncDatabase:
    """Connect to a MongoDB instance and register the connection.

    Args:
        uri: MongoDB connection URI (must include database name).
        alias: Connection alias for multi-database setups.

    Returns:
        The AsyncDatabase instance.

    Raises:
        ValueError: If URI format is invalid
    """
    logger.info(f"Connecting to MongoDB with alias '{alias}'")

    try:
        db_name = _extract_db_name(uri)
        client = AsyncMongoClient(uri)
        db = client[db_name]
        _clients[alias] = client
        _databases[alias] = db
        logger.info(f"Connected to database '{db_name}' with alias '{alias}'")
        return db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def disconnect(alias: str = "default") -> None:
    """Disconnect and remove a registered connection.

    Args:
        alias: Connection alias to disconnect
    """
    client = _clients.pop(alias, None)
    _databases.pop(alias, None)
    if client is not None:
        await client.close()
        logger.info(f"Disconnected from MongoDB (alias: '{alias}')")


def get_database(alias: str = "default") -> AsyncDatabase:
    """Retrieve a registered database or raise NotConnected.

    Args:
        alias: Connection alias

    Returns:
        AsyncDatabase instance

    Raises:
        NotConnected: If no connection exists for the alias
    """
    try:
        return _databases[alias]
    except KeyError:
        raise NotConnected(
            f"No connection registered for alias '{alias}'. Call connect() first."
        )


def get_client(alias: str = "default") -> AsyncMongoClient:
    """Retrieve a registered client or raise NotConnected.

    Args:
        alias: Connection alias

    Returns:
        AsyncMongoClient instance

    Raises:
        NotConnected: If no client exists for the alias
    """
    try:
        return _clients[alias]
    except KeyError:
        raise NotConnected(
            f"No client registered for alias '{alias}'. Call connect() first."
        )


def _extract_db_name(uri: str) -> str:
    """Extract the database name from a MongoDB URI with validation.

    Args:
        uri: MongoDB connection URI

    Returns:
        Database name extracted from URI

    Raises:
        ValueError: If URI format is invalid or database name cannot be extracted
    """
    if not uri:
        raise ValueError("MongoDB URI cannot be empty")

    # Remove query string
    path = uri.split("?")[0]

    # Get the path after the last /
    db_name = path.rsplit("/", 1)[-1]

    if not db_name or db_name == uri:
        raise ValueError(
            f"Cannot extract database name from URI. "
            f"Expected format: mongodb://host:port/database"
        )

    # Validate database name format (MongoDB naming rules)
    if not re.match(r"^[a-zA-Z0-9_-]+$", db_name):
        raise ValueError(
            f"Invalid database name '{db_name}'. "
            f"Database names can only contain letters, numbers, underscores, and hyphens."
        )

    logger.debug(f"Extracted database name: {db_name}")
    return db_name
