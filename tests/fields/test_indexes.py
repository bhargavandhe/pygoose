import pytest
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from pygoose import Document
from pygoose.fields.indexed import Indexed, IndexSpec


class UniqueUser(Document):
    email: str = Indexed(unique=True)
    name: str

    class Settings:
        collection = "unique_users"


class SparseDoc(Document):
    tag: str = Indexed(sparse=True, default=None)
    name: str

    class Settings:
        collection = "sparse_docs"


class CompoundDoc(Document):
    first_name: str
    last_name: str
    age: int = 0

    class Settings:
        collection = "compound_docs"
        indexes = [
            IndexSpec(fields=[("first_name", ASCENDING), ("last_name", ASCENDING)], unique=True),
        ]


class PlainIndexed(Document):
    category: str = Indexed()
    name: str

    class Settings:
        collection = "plain_indexed"


class TestFieldLevelIndex:
    async def test_indexed_creates_index(self, mongo_connection):
        names = await PlainIndexed.ensure_indexes()
        assert len(names) == 1
        # Verify index exists
        collection = PlainIndexed.get_collection()
        indexes = await collection.index_information()
        assert any("category" in str(idx) for idx in indexes)

    async def test_unique_index_enforced(self, mongo_connection):
        await UniqueUser.ensure_indexes()
        await UniqueUser.create(email="alice@example.com", name="Alice")
        with pytest.raises(DuplicateKeyError):
            await UniqueUser.create(email="alice@example.com", name="Alice2")

    async def test_non_unique_index_allows_duplicates(self, mongo_connection):
        await PlainIndexed.ensure_indexes()
        await PlainIndexed.create(category="A", name="Item1")
        await PlainIndexed.create(category="A", name="Item2")
        count = await PlainIndexed.find(category="A").count()
        assert count == 2

    async def test_sparse_index(self, mongo_connection):
        names = await SparseDoc.ensure_indexes()
        assert len(names) == 1
        collection = SparseDoc.get_collection()
        indexes = await collection.index_information()
        tag_index = [v for k, v in indexes.items() if "tag" in str(v.get("key", []))]
        assert tag_index
        assert tag_index[0].get("sparse") is True


class TestClassLevelIndex:
    async def test_compound_index_created(self, mongo_connection):
        names = await CompoundDoc.ensure_indexes()
        assert len(names) == 1
        collection = CompoundDoc.get_collection()
        indexes = await collection.index_information()
        # Should have compound index on first_name + last_name
        compound = [
            v for k, v in indexes.items()
            if k != "_id_" and len(v.get("key", [])) == 2
        ]
        assert len(compound) == 1

    async def test_compound_unique_enforced(self, mongo_connection):
        await CompoundDoc.ensure_indexes()
        await CompoundDoc.create(first_name="Alice", last_name="Smith")
        with pytest.raises(DuplicateKeyError):
            await CompoundDoc.create(first_name="Alice", last_name="Smith")


class TestExplain:
    async def test_explain_returns_plan(self, mongo_connection):
        await PlainIndexed.create(category="A", name="Item1")
        result = await PlainIndexed.find(category="A").explain()
        assert isinstance(result, dict)
        # Should have queryPlanner or similar key
        assert "queryPlanner" in result or "command" in result


class TestIdempotent:
    async def test_ensure_indexes_idempotent(self, mongo_connection):
        names1 = await UniqueUser.ensure_indexes()
        names2 = await UniqueUser.ensure_indexes()
        # Both calls succeed and return index names
        assert len(names1) == len(names2)
