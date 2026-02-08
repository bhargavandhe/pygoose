import pytest

from pygoose import connect, disconnect, get_database
from pygoose.core.connection import get_client
from pygoose.utils.exceptions import NotConnected


class TestConnect:
    async def test_connect_returns_database(self, mongo_connection):
        db = mongo_connection
        assert db is not None
        assert db.name == "pygoose_test"

    async def test_get_database_returns_connected_db(self, mongo_connection):
        db = get_database()
        assert db.name == "pygoose_test"

    async def test_get_client_returns_connected_client(self, mongo_connection):
        client = get_client()
        assert client is not None

    async def test_get_database_not_connected_raises(self, mongo_connection):
        await disconnect()
        with pytest.raises(NotConnected):
            get_database()

    async def test_multiple_aliases(self, mongo_connection):
        db2 = await connect(
            "mongodb://localhost:27017/pygoose_test_alt", alias="secondary"
        )
        assert db2.name == "pygoose_test_alt"
        assert get_database("secondary").name == "pygoose_test_alt"
        assert get_database("default").name == "pygoose_test"
        await disconnect("secondary")

    async def test_disconnect_removes_connection(self, mongo_connection):
        await disconnect()
        with pytest.raises(NotConnected):
            get_database()
