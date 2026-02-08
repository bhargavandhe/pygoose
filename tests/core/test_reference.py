from bson import ObjectId

from pygoose import Document, Ref


class Company(Document):
    name: str


class Author(Document):
    name: str
    company: Ref["Company"] = None


class Post(Document):
    title: str
    author: Ref["Author"] = None


class TestRefType:
    async def test_ref_stores_objectid_on_insert(self, mongo_connection):
        company = await Company.create(name="Acme")
        author = await Author.create(name="Alice", company=company.id)
        # Raw DB check
        collection = Author.get_collection()
        raw = await collection.find_one({"_id": author.id})
        assert isinstance(raw["company"], ObjectId)

    async def test_ref_accepts_objectid(self, mongo_connection):
        oid = ObjectId()
        author = Author(name="Bob", company=oid)
        assert author.company == oid

    async def test_ref_accepts_string(self, mongo_connection):
        oid = ObjectId()
        author = Author(name="Charlie", company=str(oid))
        assert author.company == oid

    async def test_ref_serializes_to_string_in_json(self, mongo_connection):
        oid = ObjectId()
        author = Author(name="Diana", company=oid)
        data = author.model_dump(mode="json")
        assert isinstance(data["company"], str)
        assert data["company"] == str(oid)

    async def test_ref_preserves_objectid_in_python_mode(self, mongo_connection):
        oid = ObjectId()
        author = Author(name="Diana", company=oid)
        data = author.model_dump(mode="python")
        assert isinstance(data["company"], ObjectId)
        assert data["company"] == oid


class TestPopulateOne:
    async def test_populate_resolves_ref(self, mongo_connection):
        company = await Company.create(name="Acme")
        author = await Author.create(name="Alice", company=company.id)
        fetched = await Author.get(author.id)
        assert isinstance(fetched.company, ObjectId)
        await fetched.populate("company")
        assert not isinstance(fetched.company, ObjectId)
        assert fetched.company.name == "Acme"

    async def test_populate_already_resolved_is_noop(self, mongo_connection):
        company = await Company.create(name="Acme")
        author = await Author.create(name="Alice", company=company.id)
        fetched = await Author.get(author.id)
        await fetched.populate("company")
        resolved = fetched.company
        await fetched.populate("company")  # Should be no-op
        assert fetched.company is resolved


class TestPopulateBatch:
    async def test_batch_populate_single_query(self, mongo_connection):
        company = await Company.create(name="Acme")
        await Author.create(name="Alice", company=company.id)
        await Author.create(name="Bob", company=company.id)

        authors = await Author.find().all()
        assert len(authors) == 2

        # Populate via QuerySet
        authors = await Author.find().populate("company").all()
        for author in authors:
            assert not isinstance(author.company, ObjectId)
            assert author.company.name == "Acme"

    async def test_populate_multiple_refs(self, mongo_connection):
        company1 = await Company.create(name="Acme")
        company2 = await Company.create(name="Beta")
        await Author.create(name="Alice", company=company1.id)
        await Author.create(name="Bob", company=company2.id)

        authors = await Author.find().populate("company").all()
        companies = {a.company.name for a in authors}
        assert companies == {"Acme", "Beta"}


class TestPopulateNested:
    async def test_nested_dot_notation(self, mongo_connection):
        company = await Company.create(name="Acme")
        author = await Author.create(name="Alice", company=company.id)
        post = await Post.create(title="Hello World", author=author.id)

        fetched = await Post.get(post.id)
        await fetched.populate("author.company")

        assert not isinstance(fetched.author, ObjectId)
        assert fetched.author.name == "Alice"
        assert not isinstance(fetched.author.company, ObjectId)
        assert fetched.author.company.name == "Acme"

    async def test_nested_populate_on_queryset(self, mongo_connection):
        company = await Company.create(name="Acme")
        author = await Author.create(name="Alice", company=company.id)
        await Post.create(title="Post 1", author=author.id)
        await Post.create(title="Post 2", author=author.id)

        posts = await Post.find().populate("author.company").all()
        assert len(posts) == 2
        for post in posts:
            assert post.author.name == "Alice"
            assert post.author.company.name == "Acme"


class TestPopulateNone:
    async def test_populate_none_ref(self, mongo_connection):
        author = await Author.create(name="Lonely")
        fetched = await Author.get(author.id)
        # company is None — populate should not crash
        await fetched.populate("company")
        assert fetched.company is None
