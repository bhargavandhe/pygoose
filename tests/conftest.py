import pytest_asyncio

from pygoose import connect, disconnect, disable_tracing
from pygoose.core.connection import _databases


@pytest_asyncio.fixture(autouse=True)
async def mongo_connection():
    """Connect to localhost MongoDB before each test, drop the DB after."""
    db = await connect("mongodb://localhost:27017/pygoose_test")
    yield db
    # Reconnect if the test disconnected (e.g., connection tests)
    if "default" not in _databases:
        db = await connect("mongodb://localhost:27017/pygoose_test")
    # Drop all collections after each test
    collections = await db.list_collection_names()
    for name in collections:
        await db.drop_collection(name)
    # Reset observability state between tests
    disable_tracing()
    await disconnect()
