import pytest

from pygoose import Document
from pygoose.utils.exceptions import PygooseError


class Article(Document):
    title: str
    category: str
    views: int = 0


class TestQuerySet:
    async def test_find_returns_queryset(self, mongo_connection):
        from pygoose.core.queryset import QuerySet

        qs = Article.find()
        assert isinstance(qs, QuerySet)

    async def test_all_returns_list(self, mongo_connection):
        await Article.create(title="A1", category="tech", views=10)
        await Article.create(title="A2", category="science", views=20)
        articles = await Article.find().all()
        assert len(articles) == 2

    async def test_first_returns_single(self, mongo_connection):
        await Article.create(title="First", category="tech")
        article = await Article.find(category="tech").first()
        assert article is not None
        assert article.title == "First"

    async def test_first_returns_none_when_empty(self, mongo_connection):
        result = await Article.find(category="nonexistent").first()
        assert result is None

    async def test_count(self, mongo_connection):
        await Article.create(title="A1", category="tech")
        await Article.create(title="A2", category="tech")
        await Article.create(title="A3", category="science")
        count = await Article.find(category="tech").count()
        assert count == 2

    async def test_exists_true(self, mongo_connection):
        await Article.create(title="Exists", category="tech")
        assert await Article.find(category="tech").exists()

    async def test_exists_false(self, mongo_connection):
        assert not await Article.find(category="nonexistent").exists()

    async def test_filter_chaining(self, mongo_connection):
        await Article.create(title="A1", category="tech", views=100)
        await Article.create(title="A2", category="tech", views=5)
        await Article.create(title="A3", category="science", views=200)

        results = await (
            Article.find(category="tech")
            .filter(views={"$gte": 50})
            .all()
        )
        assert len(results) == 1
        assert results[0].title == "A1"

    async def test_sort_ascending(self, mongo_connection):
        await Article.create(title="B", category="tech", views=2)
        await Article.create(title="A", category="tech", views=1)
        await Article.create(title="C", category="tech", views=3)

        results = await Article.find().sort("title").all()
        titles = [r.title for r in results]
        assert titles == ["A", "B", "C"]

    async def test_sort_descending(self, mongo_connection):
        await Article.create(title="B", category="tech", views=2)
        await Article.create(title="A", category="tech", views=1)
        await Article.create(title="C", category="tech", views=3)

        results = await Article.find().sort("-views").all()
        views = [r.views for r in results]
        assert views == [3, 2, 1]

    async def test_skip_and_limit(self, mongo_connection):
        for i in range(5):
            await Article.create(title=f"Art{i}", category="tech", views=i)

        results = await Article.find().sort("views").skip(1).limit(2).all()
        assert len(results) == 2
        assert results[0].views == 1
        assert results[1].views == 2

    async def test_async_iteration(self, mongo_connection):
        await Article.create(title="A1", category="tech")
        await Article.create(title="A2", category="tech")

        titles = []
        async for article in Article.find().sort("title"):
            titles.append(article.title)
        assert titles == ["A1", "A2"]

    async def test_update_many(self, mongo_connection):
        await Article.create(title="A1", category="tech", views=0)
        await Article.create(title="A2", category="tech", views=0)
        await Article.create(title="A3", category="science", views=0)

        count = await Article.find(category="tech").update_many(views=99)
        assert count == 2

        articles = await Article.find(category="tech").all()
        assert all(a.views == 99 for a in articles)

    async def test_delete_many(self, mongo_connection):
        await Article.create(title="A1", category="tech")
        await Article.create(title="A2", category="tech")
        await Article.create(title="A3", category="science")

        count = await Article.find(category="tech").delete_many()
        assert count == 2
        assert await Article.find().count() == 1

    async def test_delete_many_empty_filter_raises(self, mongo_connection):
        await Article.create(title="A1", category="tech")
        with pytest.raises(PygooseError, match="empty filter"):
            await Article.find().delete_many()

    async def test_distinct(self, mongo_connection):
        await Article.create(title="A1", category="tech")
        await Article.create(title="A2", category="tech")
        await Article.create(title="A3", category="science")

        categories = await Article.find().distinct("category")
        assert sorted(categories) == ["science", "tech"]

    async def test_immutability(self, mongo_connection):
        """Chaining returns new instances, original is unchanged."""
        qs1 = Article.find(category="tech")
        qs2 = qs1.sort("-views")
        qs3 = qs2.limit(5)

        assert qs1 is not qs2
        assert qs2 is not qs3
        assert qs1._sort == []
        assert qs1._limit_count == 0
        assert qs2._limit_count == 0
        assert qs3._limit_count == 5

    async def test_select_projection(self, mongo_connection):
        await Article.create(title="Projected", category="tech", views=42)
        results = await Article.find().select("title", "category").all()
        assert len(results) == 1
        assert results[0].title == "Projected"
        assert results[0].category == "tech"
