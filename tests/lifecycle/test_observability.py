import logging

from pygoose import Document
from pygoose.lifecycle.observability import (
    QueryEvent,
    add_listener,
    clear_events,
    disable_tracing,
    enable_tracing,
    get_events,
)


class TrackedDoc(Document):
    name: str

    class Settings:
        collection = "tracked_docs"


class TestObservability:
    async def test_tracing_disabled_by_default(self, mongo_connection):
        await TrackedDoc.create(name="Alice")
        events = get_events()
        assert len(events) == 0

    async def test_enable_tracing_captures_events(self, mongo_connection):
        enable_tracing(capture_events=True)
        await TrackedDoc.create(name="Bob")
        events = get_events()
        assert len(events) > 0
        assert any(e.operation == "insert" for e in events)

    async def test_disable_tracing_clears_state(self, mongo_connection):
        enable_tracing(capture_events=True)
        await TrackedDoc.create(name="Charlie")
        assert len(get_events()) > 0
        disable_tracing()
        assert len(get_events()) == 0

    async def test_slow_query_logs_warning(self, mongo_connection, caplog):
        enable_tracing(slow_query_ms=0.0)  # All queries are slow
        with caplog.at_level(logging.WARNING, logger="pygoose"):
            await TrackedDoc.create(name="Diana")
        assert any("Slow query" in record.message for record in caplog.records)

    async def test_listener_receives_events(self, mongo_connection):
        received = []

        def listener(event: QueryEvent):
            received.append(event)

        enable_tracing()
        add_listener(listener)
        await TrackedDoc.create(name="Eve")
        assert len(received) > 0
        assert any(e.operation == "insert" for e in received)

    async def test_find_event_includes_filter(self, mongo_connection):
        enable_tracing(capture_events=True)
        await TrackedDoc.create(name="Frank")
        clear_events()
        await TrackedDoc.find(name="Frank").all()
        events = get_events()
        find_events = [e for e in events if e.operation == "find"]
        assert len(find_events) > 0
        assert find_events[0].filter == {"name": "Frank"}

    async def test_events_have_duration(self, mongo_connection):
        enable_tracing(capture_events=True)
        await TrackedDoc.create(name="Grace")
        events = get_events()
        assert all(e.duration_ms >= 0 for e in events)

    async def test_count_event_has_result_count(self, mongo_connection):
        enable_tracing(capture_events=True)
        await TrackedDoc.create(name="Heidi")
        await TrackedDoc.create(name="Ivan")
        clear_events()
        count = await TrackedDoc.find().count()
        events = get_events()
        count_events = [e for e in events if e.operation == "count"]
        assert len(count_events) == 1
        assert count_events[0].result_count == 2
