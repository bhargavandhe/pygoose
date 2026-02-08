from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, create_model

from pygoose.core.connection import connect, disconnect
from pygoose.utils.exceptions import DocumentNotFound, PygooseError
from pygoose.utils.pagination import Page

T = TypeVar("T")


def init_app(app: Any, uri: str, alias: str = "default") -> Any:
    """Wrap a FastAPI app's lifespan to auto-connect/disconnect pygoose."""
    original_lifespan = getattr(app, "router", app).lifespan_context

    @asynccontextmanager
    async def lifespan(a: Any):
        await connect(uri, alias=alias)
        if original_lifespan is not None:
            async with original_lifespan(a) as state:
                yield state
        else:
            yield
        await disconnect(alias)

    app.router.lifespan_context = lifespan
    return app


def register_exception_handlers(app: Any) -> None:
    """Register pygoose exception handlers on a FastAPI app."""
    from starlette.responses import JSONResponse

    @app.exception_handler(DocumentNotFound)
    async def document_not_found_handler(request: Any, exc: DocumentNotFound):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(PygooseError)
    async def pygoose_error_handler(request: Any, exc: PygooseError):
        return JSONResponse(status_code=500, content={"detail": str(exc)})


class PaginationParams:
    """FastAPI dependency for pagination parameters."""

    def __init__(self, page: int = 1, size: int = 20):
        self.page = max(1, page)
        self.size = min(max(1, size), 100)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response model for API endpoints."""

    items: list[T]
    page: int
    size: int
    total: int
    has_next: bool
    has_prev: bool
    total_pages: int

    @classmethod
    def from_page(cls, page_obj: Page) -> PaginatedResponse:
        return cls(
            items=page_obj.items,
            page=page_obj.page,
            size=page_obj.size,
            total=page_obj.total,
            has_next=page_obj.has_next,
            has_prev=page_obj.has_prev,
            total_pages=page_obj.total_pages,
        )


def create_schema(document_class: type, *, name: str | None = None) -> type[BaseModel]:
    """Generate a Pydantic create schema from a Document class, excluding id."""
    model_name = name or f"{document_class.__name__}Create"
    fields: dict[str, Any] = {}

    for field_name, field_info in document_class.model_fields.items():
        if field_name == "id":
            continue
        if field_info.is_required():
            fields[field_name] = (field_info.annotation, ...)
        else:
            fields[field_name] = (field_info.annotation, field_info.default)

    return create_model(model_name, **fields)


def update_schema(document_class: type, *, name: str | None = None) -> type[BaseModel]:
    """Generate a Pydantic update schema where all fields are optional."""
    model_name = name or f"{document_class.__name__}Update"
    fields: dict[str, Any] = {}

    for field_name, field_info in document_class.model_fields.items():
        if field_name == "id":
            continue
        fields[field_name] = (Optional[field_info.annotation], None)

    return create_model(model_name, **fields)


def audit_middleware(app: Any) -> None:
    """Add middleware that sets audit context from request headers."""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request

    from pygoose.plugins.audit import clear_audit_context, set_audit_context

    class AuditContextMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            user_id = request.headers.get("x-user-id")
            request_id = request.headers.get("x-request-id")
            ip_address = None
            if request.client:
                ip_address = request.client.host
            token = set_audit_context(
                user_id=user_id,
                ip_address=ip_address,
                request_id=request_id,
            )
            try:
                response = await call_next(request)
            finally:
                clear_audit_context(token)
            return response

    app.add_middleware(AuditContextMiddleware)
