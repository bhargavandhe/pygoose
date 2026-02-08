from pygoose import Document


class Item(Document):
    name: str
    price: float
    quantity: int = 0


class TestDirtyTracking:
    async def test_new_doc_not_dirty(self, mongo_connection):
        item = Item(name="Widget", price=9.99)
        assert not item.is_dirty
        assert item.dirty_fields == set()

    async def test_loaded_doc_not_dirty(self, mongo_connection):
        item = await Item.create(name="Widget", price=9.99, quantity=5)
        fetched = await Item.get(item.id)
        assert not fetched.is_dirty

    async def test_field_change_marks_dirty(self, mongo_connection):
        item = await Item.create(name="Widget", price=9.99)
        fetched = await Item.get(item.id)
        fetched.name = "Super Widget"
        assert fetched.is_dirty
        assert "name" in fetched.dirty_fields

    async def test_multiple_field_changes(self, mongo_connection):
        item = await Item.create(name="Widget", price=9.99, quantity=5)
        fetched = await Item.get(item.id)
        fetched.name = "New Widget"
        fetched.price = 19.99
        assert fetched.dirty_fields == {"name", "price"}

    async def test_save_clears_dirty(self, mongo_connection):
        item = await Item.create(name="Widget", price=9.99)
        fetched = await Item.get(item.id)
        fetched.name = "Updated Widget"
        assert fetched.is_dirty
        await fetched.save()
        assert not fetched.is_dirty

    async def test_save_sends_only_dirty_fields(self, mongo_connection):
        item = await Item.create(name="Widget", price=9.99, quantity=5)
        fetched = await Item.get(item.id)
        fetched.name = "Changed"
        update_doc = fetched._get_update_doc()
        assert "$set" in update_doc
        assert "name" in update_doc["$set"]
        assert "price" not in update_doc["$set"]
        assert "quantity" not in update_doc["$set"]

    async def test_noop_save_when_clean(self, mongo_connection):
        item = await Item.create(name="Widget", price=9.99)
        fetched = await Item.get(item.id)
        # Save without changes — should be a no-op
        await fetched.save()
        assert not fetched.is_dirty

    async def test_update_does_not_mark_dirty(self, mongo_connection):
        item = await Item.create(name="Widget", price=9.99)
        fetched = await Item.get(item.id)
        await fetched.update(name="Updated")
        assert not fetched.is_dirty
