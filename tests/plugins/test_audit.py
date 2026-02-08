from __future__ import annotations

from typing import Any, Optional

import pytest

from pygoose import Document
from pygoose.plugins.audit import (
    AuditMixin,
    clear_audit_context,
    get_audit_context,
    set_audit_context,
)
from pygoose.plugins.timestamps import TimestampsMixin


class AuditedUser(AuditMixin, Document):
    name: str
    email: str


class FullUser(AuditMixin, TimestampsMixin, Document):
    name: str


async def _get_audit_entries() -> list[dict[str, Any]]:
    col = AuditedUser._get_audit_collection()
    return [doc async for doc in col.find()]


async def test_insert_creates_audit_entry():
    doc = await AuditedUser.create(name="Alice", email="alice@example.com")

    entries = await _get_audit_entries()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["operation"] == "insert"
    assert entry["document_id"] == doc.id
    assert entry["document_class"] == "AuditedUser"
    assert entry["collection"] == "auditedusers"
    assert "after" in entry


async def test_save_update_creates_audit_entry():
    doc = await AuditedUser.create(name="Alice", email="alice@example.com")
    doc.name = "Bob"
    await doc.save()

    entries = await _get_audit_entries()
    assert len(entries) == 2
    update_entry = entries[1]
    assert update_entry["operation"] == "update"
    assert update_entry["changes"] == {"name": "Bob"}


async def test_delete_creates_audit_entry():
    doc = await AuditedUser.create(name="Alice", email="alice@example.com")
    doc_id = doc.id
    await doc.delete()

    entries = await _get_audit_entries()
    assert len(entries) == 2
    delete_entry = entries[1]
    assert delete_entry["operation"] == "delete"
    assert delete_entry["document_id"] == doc_id


async def test_atomic_update_audit():
    doc = await AuditedUser.create(name="Alice", email="alice@example.com")
    await doc.update(name="Bob")

    entries = await _get_audit_entries()
    assert len(entries) == 2
    update_entry = entries[1]
    assert update_entry["operation"] == "update"
    assert update_entry["changes"] == {"name": "Bob"}


async def test_audit_context_captured():
    token = set_audit_context(user_id="user-1", ip_address="127.0.0.1", request_id="req-abc")
    try:
        await AuditedUser.create(name="Alice", email="alice@example.com")

        entries = await _get_audit_entries()
        entry = entries[0]
        assert entry["user_id"] == "user-1"
        assert entry["ip_address"] == "127.0.0.1"
        assert entry["request_id"] == "req-abc"
    finally:
        clear_audit_context(token)


async def test_audit_context_isolation():
    token = set_audit_context(user_id="user-1")
    clear_audit_context(token)

    ctx = get_audit_context()
    assert ctx.get("user_id") is None


async def test_clear_audit_context():
    token = set_audit_context(user_id="user-1", ip_address="10.0.0.1")
    assert get_audit_context()["user_id"] == "user-1"
    clear_audit_context(token)
    assert get_audit_context() == {}


async def test_audit_no_context_still_logs():
    clear_audit_context()
    await AuditedUser.create(name="Alice", email="alice@example.com")

    entries = await _get_audit_entries()
    assert len(entries) == 1
    assert entries[0]["user_id"] is None


async def test_audit_with_timestamps_mixin():
    doc = await FullUser.create(name="Alice")
    assert doc.created_at is not None

    entries = await _get_audit_entries()
    assert len(entries) == 1
    assert entries[0]["operation"] == "insert"
    assert entries[0]["document_class"] == "FullUser"


async def test_audit_collection_in_same_db():
    await AuditedUser.create(name="Alice", email="alice@example.com")

    from pygoose.core.connection import get_database

    db = get_database()
    collections = await db.list_collection_names()
    assert "_audit_log" in collections
