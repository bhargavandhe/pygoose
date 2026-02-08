import pytest
from bson import ObjectId

from pygoose import Document, DocumentNotFound


class User(Document):
    name: str
    email: str


class CustomCollection(Document):
    value: str

    class Settings:
        collection = "my_custom_collection"


class TestCollectionName:
    def test_auto_pluralize(self):
        assert User._collection_name == "users"

    def test_settings_override(self):
        assert CustomCollection._collection_name == "my_custom_collection"


class TestCreateAndGet:
    async def test_create_assigns_id(self, mongo_connection):
        user = await User.create(name="Alice", email="alice@example.com")
        assert user.id is not None
        assert isinstance(user.id, ObjectId)

    async def test_get_round_trip(self, mongo_connection):
        user = await User.create(name="Bob", email="bob@example.com")
        fetched = await User.get(user.id)
        assert fetched.name == "Bob"
        assert fetched.email == "bob@example.com"
        assert fetched.id == user.id

    async def test_get_with_string_id(self, mongo_connection):
        user = await User.create(name="Charlie", email="charlie@example.com")
        fetched = await User.get(str(user.id))
        assert fetched.name == "Charlie"

    async def test_get_not_found_raises(self, mongo_connection):
        with pytest.raises(DocumentNotFound):
            await User.get(ObjectId())


class TestFindOne:
    async def test_find_one_returns_match(self, mongo_connection):
        await User.create(name="Diana", email="diana@example.com")
        found = await User.find_one({"name": "Diana"})
        assert found is not None
        assert found.name == "Diana"

    async def test_find_one_returns_none_when_missing(self, mongo_connection):
        result = await User.find_one({"name": "Nobody"})
        assert result is None

    async def test_find_one_with_kwargs(self, mongo_connection):
        await User.create(name="Eve", email="eve@example.com")
        found = await User.find_one(name="Eve")
        assert found is not None
        assert found.email == "eve@example.com"


class TestSave:
    async def test_save_new_document(self, mongo_connection):
        user = User(name="Frank", email="frank@example.com")
        await user.save()
        assert user.id is not None
        fetched = await User.get(user.id)
        assert fetched.name == "Frank"

    async def test_save_existing_document(self, mongo_connection):
        user = await User.create(name="Grace", email="grace@example.com")
        user.name = "Grace H."
        await user.save()
        fetched = await User.get(user.id)
        assert fetched.name == "Grace H."


class TestDelete:
    async def test_delete_removes_document(self, mongo_connection):
        user = await User.create(name="Heidi", email="heidi@example.com")
        uid = user.id
        await user.delete()
        with pytest.raises(DocumentNotFound):
            await User.get(uid)


class TestReload:
    async def test_reload_refreshes_data(self, mongo_connection):
        user = await User.create(name="Ivan", email="ivan@example.com")
        # Modify directly in DB
        collection = User.get_collection()
        await collection.update_one({"_id": user.id}, {"$set": {"name": "Ivan R."}})
        await user.reload()
        assert user.name == "Ivan R."

    async def test_reload_not_found_raises(self, mongo_connection):
        user = await User.create(name="Judy", email="judy@example.com")
        await user.delete()
        with pytest.raises(DocumentNotFound):
            await user.reload()


class TestUpdate:
    async def test_update_partial(self, mongo_connection):
        user = await User.create(name="Karl", email="karl@example.com")
        await user.update(name="Karl M.")
        assert user.name == "Karl M."
        fetched = await User.get(user.id)
        assert fetched.name == "Karl M."
        assert fetched.email == "karl@example.com"

    async def test_update_unknown_field_raises(self, mongo_connection):
        user = await User.create(name="Laura", email="laura@example.com")
        with pytest.raises(ValueError, match="Unknown field"):
            await user.update(nonexistent="value")
