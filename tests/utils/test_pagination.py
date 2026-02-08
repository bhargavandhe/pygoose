import pytest

from pygoose import Document
from pygoose.utils.pagination import CursorPage, Page


class Item(Document):
    name: str
    category: str = "default"


async def _seed_items(n: int, **kwargs) -> list[Item]:
    items = []
    for i in range(n):
        item = await Item.create(name=f"item_{i:03d}", **kwargs)
        items.append(item)
    return items


class TestOffsetPagination:
    async def test_basic_pagination(self, mongo_connection):
        await _seed_items(25)
        page = await Item.find().paginate(page=1, size=10)
        assert isinstance(page, Page)
        assert len(page.items) == 10
        assert page.page == 1
        assert page.size == 10
        assert page.total == 25
        assert page.total_pages == 3
        assert page.has_next is True
        assert page.has_prev is False

    async def test_last_page_metadata(self, mongo_connection):
        await _seed_items(25)
        page = await Item.find().paginate(page=3, size=10)
        assert len(page.items) == 5
        assert page.has_next is False
        assert page.has_prev is True

    async def test_empty_collection(self, mongo_connection):
        page = await Item.find().paginate(page=1, size=10)
        assert len(page.items) == 0
        assert page.total == 0
        assert page.total_pages == 0
        assert page.has_next is False
        assert page.has_prev is False

    async def test_with_filter(self, mongo_connection):
        await _seed_items(10, category="A")
        await _seed_items(5, category="B")
        page = await Item.find(category="A").paginate(page=1, size=10)
        assert page.total == 10
        assert len(page.items) == 10

    async def test_invalid_page_raises(self, mongo_connection):
        with pytest.raises(ValueError, match="page must be >= 1"):
            await Item.find().paginate(page=0)

    async def test_invalid_size_raises(self, mongo_connection):
        with pytest.raises(ValueError, match="size must be >= 1"):
            await Item.find().paginate(size=0)

    async def test_single_page(self, mongo_connection):
        await _seed_items(5)
        page = await Item.find().paginate(page=1, size=10)
        assert len(page.items) == 5
        assert page.total_pages == 1
        assert page.has_next is False
        assert page.has_prev is False


class TestCursorPagination:
    async def test_first_page(self, mongo_connection):
        await _seed_items(15)
        page = await Item.find().cursor_paginate(size=10)
        assert isinstance(page, CursorPage)
        assert len(page.items) == 10
        assert page.has_next is True
        assert page.next_cursor is not None

    async def test_subsequent_page(self, mongo_connection):
        await _seed_items(15)
        page1 = await Item.find().cursor_paginate(size=10)
        page2 = await Item.find().cursor_paginate(size=10, after=page1.next_cursor)
        assert len(page2.items) == 5
        assert page2.has_next is False
        assert page2.next_cursor is None

    async def test_last_page_no_next(self, mongo_connection):
        await _seed_items(5)
        page = await Item.find().cursor_paginate(size=10)
        assert len(page.items) == 5
        assert page.has_next is False
        assert page.next_cursor is None

    async def test_empty_cursor(self, mongo_connection):
        page = await Item.find().cursor_paginate(size=10)
        assert len(page.items) == 0
        assert page.has_next is False
        assert page.next_cursor is None

    async def test_cursor_with_filter(self, mongo_connection):
        await _seed_items(10, category="A")
        await _seed_items(5, category="B")
        page = await Item.find(category="A").cursor_paginate(size=5)
        assert len(page.items) == 5
        assert page.has_next is True
