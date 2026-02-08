from pygoose import Document, DocumentNotFound
from pygoose.plugins import SoftDeleteMixin


class SoftUser(SoftDeleteMixin, Document):
    name: str

    class Settings:
        collection = "soft_users"


class TestSoftDelete:
    async def test_delete_sets_deleted_at(self, mongo_connection):
        user = await SoftUser.create(name="Alice")
        await user.delete()
        assert user.deleted_at is not None

    async def test_find_excludes_deleted(self, mongo_connection):
        user = await SoftUser.create(name="Bob")
        await user.delete()
        results = await SoftUser.find().all()
        assert len(results) == 0

    async def test_find_deleted_returns_only_deleted(self, mongo_connection):
        alive = await SoftUser.create(name="Charlie")
        deleted = await SoftUser.create(name="Diana")
        await deleted.delete()
        results = await SoftUser.find_deleted().all()
        assert len(results) == 1
        assert results[0].name == "Diana"

    async def test_find_with_deleted_returns_all(self, mongo_connection):
        alive = await SoftUser.create(name="Eve")
        deleted = await SoftUser.create(name="Frank")
        await deleted.delete()
        results = await SoftUser.find_with_deleted().all()
        assert len(results) == 2

    async def test_hard_delete_removes_permanently(self, mongo_connection):
        user = await SoftUser.create(name="Grace")
        uid = user.id
        await user.hard_delete()
        # Even find_with_deleted won't find it
        results = await SoftUser.find_with_deleted().all()
        assert all(r.id != uid for r in results)

    async def test_restore_clears_deleted_at(self, mongo_connection):
        user = await SoftUser.create(name="Heidi")
        await user.delete()
        assert user.deleted_at is not None
        await user.restore()
        assert user.deleted_at is None
        # Now find() should return it
        results = await SoftUser.find().all()
        assert len(results) == 1
        assert results[0].name == "Heidi"

    async def test_soft_deleted_doc_persists_in_db(self, mongo_connection):
        user = await SoftUser.create(name="Ivan")
        await user.delete()
        # Verify it's still in DB via raw query
        collection = SoftUser.get_collection()
        raw = await collection.find_one({"_id": user.id})
        assert raw is not None
        assert raw["deleted_at"] is not None
