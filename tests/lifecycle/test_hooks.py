from pygoose import Document
from pygoose.lifecycle.hooks import (
    post_delete,
    post_save,
    post_update,
    pre_delete,
    pre_save,
    pre_validate,
)


class HookedUser(Document):
    name: str
    email: str
    log: list[str] = []

    @pre_validate
    async def on_pre_validate(self):
        self.log = [*self.log, "pre_validate"]

    @pre_save
    async def on_pre_save(self):
        self.log = [*self.log, "pre_save"]

    @post_save
    async def on_post_save(self):
        self.log = [*self.log, "post_save"]

    @pre_delete
    async def on_pre_delete(self):
        self.log = [*self.log, "pre_delete"]

    @post_delete
    async def on_post_delete(self):
        self.log = [*self.log, "post_delete"]

    @post_update
    async def on_post_update(self):
        self.log = [*self.log, "post_update"]


class TestPreSave:
    async def test_pre_save_fires_on_insert(self, mongo_connection):
        user = HookedUser(name="Alice", email="alice@example.com")
        await user.insert()
        assert "pre_save" in user.log

    async def test_pre_save_fires_on_save_existing(self, mongo_connection):
        user = await HookedUser.create(name="Bob", email="bob@example.com")
        user.log = []
        user.name = "Bob Updated"
        await user.save()
        assert "pre_save" in user.log


class TestPostSave:
    async def test_post_save_fires_after_insert(self, mongo_connection):
        user = HookedUser(name="Charlie", email="charlie@example.com")
        await user.insert()
        assert "post_save" in user.log
        # post_save comes after pre_save
        assert user.log.index("pre_save") < user.log.index("post_save")


class TestDeleteHooks:
    async def test_pre_delete_fires(self, mongo_connection):
        user = await HookedUser.create(name="Diana", email="diana@example.com")
        user.log = []
        await user.delete()
        assert "pre_delete" in user.log

    async def test_post_delete_fires(self, mongo_connection):
        user = await HookedUser.create(name="Eve", email="eve@example.com")
        user.log = []
        await user.delete()
        assert "post_delete" in user.log
        assert user.log.index("pre_delete") < user.log.index("post_delete")


class TestPostUpdate:
    async def test_post_update_fires(self, mongo_connection):
        user = await HookedUser.create(name="Frank", email="frank@example.com")
        user.log = []
        await user.update(name="Frank Updated")
        assert "post_update" in user.log


class TestPreValidate:
    async def test_pre_validate_fires_before_pre_save(self, mongo_connection):
        user = HookedUser(name="Grace", email="grace@example.com")
        await user.insert()
        assert user.log.index("pre_validate") < user.log.index("pre_save")


class TestHookOrder:
    async def test_full_insert_hook_order(self, mongo_connection):
        user = HookedUser(name="Heidi", email="heidi@example.com")
        await user.insert()
        assert user.log == ["pre_validate", "pre_save", "post_save"]


class TestMROHookOrder:
    async def test_parent_hooks_run_before_child(self, mongo_connection):
        class ParentDoc(Document):
            name: str
            log: list[str] = []

            @pre_save
            async def parent_hook(self):
                self.log = [*self.log, "parent"]

        class ChildDoc(ParentDoc):
            @pre_save
            async def child_hook(self):
                self.log = [*self.log, "child"]

        child = ChildDoc(name="Test")
        await child.insert()
        assert child.log == ["parent", "child"]


class TestSyncHooks:
    async def test_sync_hook_works(self, mongo_connection):
        class SyncHooked(Document):
            name: str
            log: list[str] = []

            @pre_save
            def sync_pre_save(self):
                self.log = [*self.log, "sync_pre_save"]

        doc = SyncHooked(name="Test")
        await doc.insert()
        assert "sync_pre_save" in doc.log


class TestNoOpOnClean:
    async def test_save_non_dirty_skips_hooks(self, mongo_connection):
        user = await HookedUser.create(name="Ivan", email="ivan@example.com")
        user.log = []
        # Clear dirty state so save is a no-op
        user._dirty_fields = set()
        await user.save()
        assert user.log == []
