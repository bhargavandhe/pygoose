import asyncio

from pygoose import Document
from pygoose.plugins import TimestampsMixin


class TimestampedUser(TimestampsMixin, Document):
    name: str

    class Settings:
        collection = "timestamped_users"


class TestTimestamps:
    async def test_create_sets_both_timestamps(self, mongo_connection):
        user = await TimestampedUser.create(name="Alice")
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.created_at == user.updated_at

    async def test_save_updates_updated_at_only(self, mongo_connection):
        user = await TimestampedUser.create(name="Bob")
        original_created = user.created_at
        original_updated = user.updated_at
        await asyncio.sleep(0.01)
        user.name = "Bob Updated"
        await user.save()
        assert user.created_at == original_created
        assert user.updated_at > original_updated

    async def test_update_sets_updated_at(self, mongo_connection):
        user = await TimestampedUser.create(name="Charlie")
        original_updated = user.updated_at
        await asyncio.sleep(0.01)
        await user.update(name="Charlie Updated")
        assert user.updated_at > original_updated

    async def test_timestamps_persisted_in_db(self, mongo_connection):
        user = await TimestampedUser.create(name="Diana")
        fetched = await TimestampedUser.get(user.id)
        assert fetched.created_at is not None
        assert fetched.updated_at is not None
        # MongoDB strips timezone info; compare after normalizing
        a = fetched.created_at.replace(tzinfo=None)
        b = user.created_at.replace(tzinfo=None)
        assert abs((a - b).total_seconds()) < 0.001

    async def test_save_new_sets_timestamps(self, mongo_connection):
        user = TimestampedUser(name="Eve")
        await user.save()
        assert user.created_at is not None
        assert user.updated_at is not None
