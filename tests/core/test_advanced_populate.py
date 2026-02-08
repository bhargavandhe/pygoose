from unittest.mock import patch

from bson import ObjectId

from pygoose import Document, Ref
from pygoose.core.reference import LazyRef, PopulateEngine


class Team(Document):
    name: str

    class Settings:
        collection = "adv_teams"


class Player(Document):
    name: str
    team: Ref["Team"] = None

    class Settings:
        collection = "adv_players"


class AutoPlayer(Document):
    name: str
    team: Ref["Team"] = None

    class Settings:
        collection = "adv_auto_players"
        auto_populate = ["team"]


# Circular references for testing
class NodeA(Document):
    name: str
    link: Ref["NodeB"] = None

    class Settings:
        collection = "adv_node_a"


class NodeB(Document):
    name: str
    link: Ref["NodeA"] = None

    class Settings:
        collection = "adv_node_b"


class TestPopulateCache:
    async def test_cache_avoids_duplicate_queries(self, mongo_connection):
        team = await Team.create(name="Warriors")
        p1 = await Player.create(name="Alice", team=team.id)
        p2 = await Player.create(name="Bob", team=team.id)

        engine = PopulateEngine()
        # Populate both players — same team should only be queried once
        await engine.populate_many([p1, p2], "team")

        # Both should be resolved
        assert not isinstance(p1.team, ObjectId)
        assert not isinstance(p2.team, ObjectId)
        assert p1.team.name == "Warriors"
        assert p2.team.name == "Warriors"

        # Cache should have the team
        assert len(engine._cache) == 1

    async def test_cache_used_on_second_call(self, mongo_connection):
        team = await Team.create(name="Lakers")
        p1 = await Player.create(name="Charlie", team=team.id)
        p2 = await Player.create(name="Diana", team=team.id)

        engine = PopulateEngine()
        # First call populates and caches
        fetched1 = await Player.get(p1.id)
        await engine.populate_one(fetched1, "team")
        assert not isinstance(fetched1.team, ObjectId)

        # Second call should use cache (no DB query)
        fetched2 = await Player.get(p2.id)
        await engine.populate_one(fetched2, "team")
        assert not isinstance(fetched2.team, ObjectId)
        assert fetched2.team.name == "Lakers"


class TestCircularRefDetection:
    async def test_circular_ref_no_infinite_loop(self, mongo_connection):
        a = await NodeA.create(name="A")
        b = await NodeB.create(name="B", link=a.id)
        # Update A to point back to B
        await a.update(link=b.id)

        engine = PopulateEngine()
        fetched_a = await NodeA.get(a.id)

        # Populate link → should resolve to NodeB
        await engine.populate_one(fetched_a, "link")
        assert not isinstance(fetched_a.link, ObjectId)
        assert fetched_a.link.name == "B"

        # Now try to populate the back-reference on B — should not infinite loop
        await engine.populate_one(fetched_a.link, "link")
        # The back-link might be resolved from cache, or left as ObjectId if circular
        # The key thing is it doesn't hang


class TestAutoPopulate:
    async def test_auto_populate_on_get(self, mongo_connection):
        team = await Team.create(name="Bulls")
        player = await AutoPlayer.create(name="Eve", team=team.id)
        fetched = await AutoPlayer.get(player.id)
        # Should be auto-populated
        assert not isinstance(fetched.team, ObjectId)
        assert fetched.team.name == "Bulls"

    async def test_auto_populate_on_find_one(self, mongo_connection):
        team = await Team.create(name="Heat")
        await AutoPlayer.create(name="Frank", team=team.id)
        fetched = await AutoPlayer.find_one(name="Frank")
        assert fetched is not None
        assert not isinstance(fetched.team, ObjectId)
        assert fetched.team.name == "Heat"

    async def test_auto_populate_disabled_by_default(self, mongo_connection):
        team = await Team.create(name="Celtics")
        player = await Player.create(name="Grace", team=team.id)
        fetched = await Player.get(player.id)
        # Regular Player doesn't auto-populate
        assert isinstance(fetched.team, ObjectId)


class TestLazyRef:
    async def test_lazy_ref_resolve(self, mongo_connection):
        team = await Team.create(name="Spurs")
        player = await Player.create(name="Heidi", team=team.id)
        fetched = await Player.get(player.id)

        lazy = LazyRef(fetched, "team")
        assert lazy.ref_id == team.id

        resolved = await lazy.resolve()
        assert resolved is not None
        assert resolved.name == "Spurs"

    async def test_lazy_ref_caches_after_resolve(self, mongo_connection):
        team = await Team.create(name="Nets")
        player = await Player.create(name="Ivan", team=team.id)
        fetched = await Player.get(player.id)

        lazy = LazyRef(fetched, "team")
        first = await lazy.resolve()
        second = await lazy.resolve()
        # Should be the same object (cached)
        assert first is second
