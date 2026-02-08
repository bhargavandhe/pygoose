from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger("pygoose")


@dataclass(frozen=True)
class QueryEvent:
    """Represents a single database operation for tracing."""

    operation: str
    collection: str
    filter: dict[str, Any] | None = None
    update: dict[str, Any] | None = None
    duration_ms: float = 0.0
    result_count: int | None = None
    document_class: str = ""


class _ObservabilityState:
    """Global mutable state for observability."""

    def __init__(self) -> None:
        self.enabled: bool = False
        self.slow_query_threshold_ms: float = 100.0
        self.listeners: list[Callable[[QueryEvent], Any]] = []
        self.events: list[QueryEvent] = []
        self.capture_events: bool = False


_state = _ObservabilityState()


def enable_tracing(slow_query_ms: float = 100.0, capture_events: bool = False) -> None:
    """Enable query tracing and observability."""
    _state.enabled = True
    _state.slow_query_threshold_ms = slow_query_ms
    _state.capture_events = capture_events


def disable_tracing() -> None:
    """Disable tracing and clear all state."""
    _state.enabled = False
    _state.slow_query_threshold_ms = 100.0
    _state.listeners.clear()
    _state.events.clear()
    _state.capture_events = False


def get_events() -> list[QueryEvent]:
    """Return captured events."""
    return list(_state.events)


def clear_events() -> None:
    """Clear captured events."""
    _state.events.clear()


def add_listener(callback: Callable[[QueryEvent], Any]) -> None:
    """Register a listener that receives QueryEvent on each operation."""
    _state.listeners.append(callback)


def remove_listener(callback: Callable[[QueryEvent], Any]) -> None:
    """Remove a previously registered listener."""
    _state.listeners.remove(callback)


def emit_event(event: QueryEvent) -> None:
    """Emit a query event: store, log slow queries, notify listeners."""
    if not _state.enabled:
        return

    if _state.capture_events:
        _state.events.append(event)

    if event.duration_ms > _state.slow_query_threshold_ms:
        logger.warning(
            "Slow query: %s on %s took %.1fms (threshold: %.1fms)",
            event.operation,
            event.collection,
            event.duration_ms,
            _state.slow_query_threshold_ms,
        )

    for listener in _state.listeners:
        listener(event)

    _try_emit_otel_span(event)


def _try_emit_otel_span(event: QueryEvent) -> None:
    """Attempt to emit an OpenTelemetry span if the library is available."""
    try:
        from opentelemetry import trace

        tracer = trace.get_tracer("pygoose")
        with tracer.start_as_current_span(f"pygoose.{event.operation}") as span:
            span.set_attribute("db.system", "mongodb")
            span.set_attribute("db.collection", event.collection)
            span.set_attribute("db.operation", event.operation)
            if event.duration_ms:
                span.set_attribute("db.duration_ms", event.duration_ms)
    except ImportError:
        pass


@asynccontextmanager
async def track_query(operation: str, collection: str, document_class: str = "", filter: dict | None = None, update: dict | None = None):
    """Context manager that times an operation and emits a QueryEvent."""
    if not _state.enabled:
        yield {"result_count": None}
        return

    start = time.perf_counter()
    ctx: dict[str, Any] = {"result_count": None}
    try:
        yield ctx
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        event = QueryEvent(
            operation=operation,
            collection=collection,
            filter=filter,
            update=update,
            duration_ms=duration_ms,
            result_count=ctx.get("result_count"),
            document_class=document_class,
        )
        emit_event(event)
