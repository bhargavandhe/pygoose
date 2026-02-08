from __future__ import annotations

from typing import Optional

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from pygoose import Document
from pygoose.utils.exceptions import DocumentNotFound, PygooseError
from pygoose.integrations.fastapi import (
    PaginatedResponse,
    PaginationParams,
    create_schema,
    init_app,
    register_exception_handlers,
    update_schema,
)
from pygoose.utils.pagination import Page


class UserDoc(Document):
    name: str
    email: str
    age: Optional[int] = None


def test_create_schema_excludes_id():
    UserCreate = create_schema(UserDoc)
    assert "id" not in UserCreate.model_fields
    assert "name" in UserCreate.model_fields
    assert "email" in UserCreate.model_fields


def test_create_schema_required_fields():
    UserCreate = create_schema(UserDoc)
    assert UserCreate.model_fields["name"].is_required()
    assert UserCreate.model_fields["email"].is_required()


def test_create_schema_optional_fields():
    UserCreate = create_schema(UserDoc)
    assert not UserCreate.model_fields["age"].is_required()
    assert UserCreate.model_fields["age"].default is None


def test_update_schema_all_optional():
    UserUpdate = update_schema(UserDoc)
    for field_name, field_info in UserUpdate.model_fields.items():
        assert not field_info.is_required(), f"{field_name} should be optional"
        assert field_info.default is None


def test_paginated_response_from_page():
    page = Page(
        items=[{"name": "Alice"}, {"name": "Bob"}],
        page=1,
        size=10,
        total=2,
        has_next=False,
        has_prev=False,
        total_pages=1,
    )
    resp = PaginatedResponse[dict].from_page(page)
    assert resp.items == [{"name": "Alice"}, {"name": "Bob"}]
    assert resp.page == 1
    assert resp.total == 2
    assert resp.has_next is False


def test_pagination_params_defaults():
    p = PaginationParams()
    assert p.page == 1
    assert p.size == 20


def test_pagination_params_clamps_max():
    p = PaginationParams(page=1, size=999)
    assert p.size == 100


def test_exception_handler_404():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/user/{user_id}")
    async def get_user(user_id: str):
        raise DocumentNotFound(f"User {user_id} not found")

    client = TestClient(app)
    resp = client.get("/user/abc")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_exception_handler_500():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/error")
    async def error_endpoint():
        raise PygooseError("Something went wrong")

    client = TestClient(app)
    resp = client.get("/error")
    assert resp.status_code == 500
    assert "Something went wrong" in resp.json()["detail"]


async def test_init_app_connects():
    app = FastAPI()
    init_app(app, "mongodb://localhost:27017/pygoose_test_fastapi")

    # Use TestClient which triggers lifespan
    with TestClient(app) as client:
        from pygoose.core.connection import _databases

        assert "default" in _databases
