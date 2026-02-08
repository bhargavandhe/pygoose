from __future__ import annotations

from typing import Any, Generic, TypeVar, get_args

from bson import ObjectId
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

T = TypeVar("T")


class Ref(Generic[T]):
    """Reference type for linking MongoDB documents.

    At runtime holds an ObjectId (unresolved) or a T instance (after populate).
    In MongoDB, always stored as ObjectId. In JSON, serialized as string.
    """

    def __class_getitem__(cls, item: Any) -> Any:
        # Support Ref["ClassName"] and Ref[ClassName]
        return type(
            f"Ref[{item if isinstance(item, str) else item.__name__}]",
            (Ref,),
            {"__ref_target__": item, "__origin__": Ref, "__args__": (item,)},
        )

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        # Extract the target type from Ref[T]
        args = getattr(source_type, "__args__", None)
        target_name = None
        if args:
            target = args[0]
            if isinstance(target, str):
                target_name = target
            elif isinstance(target, type):
                target_name = target.__name__

        return core_schema.no_info_wrap_validator_function(
            cls._make_validator(target_name),
            core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.str_schema(),
                    # Allow any dict/model (for when the ref is already resolved)
                    core_schema.any_schema(),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls._serialize,
                info_arg=True,
                when_used="unless-none",
            ),
        )

    @classmethod
    def _make_validator(cls, target_name: str | None):
        """Create a validator function that stores ObjectId or resolved document."""

        def validate(value: Any, handler: Any) -> ObjectId | Any:
            if value is None:
                return None
            if isinstance(value, ObjectId):
                return value
            if isinstance(value, str):
                if ObjectId.is_valid(value):
                    return ObjectId(value)
                raise ValueError(f"Invalid ObjectId string: {value}")
            # If it's a Document instance (already resolved), pass through
            from pygoose.core.document import Document

            if isinstance(value, Document):
                return value
            raise ValueError(f"Cannot convert {type(value)} to Ref")

        return validate

    @staticmethod
    def _serialize(value: Any, info: Any) -> Any:
        """Serialize Ref values.

        In 'python' mode (used by _to_mongo), preserve ObjectId as-is.
        In 'json' mode, convert ObjectId to string.
        """
        if value is None:
            return None

        mode = getattr(info, "mode", "python")

        if isinstance(value, ObjectId):
            return str(value) if mode == "json" else value

        from pygoose.core.document import Document

        if isinstance(value, Document):
            return value.model_dump(by_alias=True, mode=mode)

        return str(value)


def _resolve_target_class(doc_class: type, field_name: str) -> type:
    """Resolve the target Document class for a Ref field."""
    from pygoose.core.document import _document_registry

    # Get the field annotation
    annotation = doc_class.model_fields[field_name].annotation

    # Extract target from Ref[T]
    target = getattr(annotation, "__ref_target__", None)
    if target is None:
        # Try get_args for standard generic
        args = get_args(annotation)
        if args:
            target = args[0]

    if target is None:
        raise ValueError(f"Cannot resolve target for field '{field_name}' on {doc_class.__name__}")

    # Resolve string forward reference
    if isinstance(target, str):
        if target not in _document_registry:
            raise ValueError(
                f"Cannot resolve reference '{target}'. "
                f"Known documents: {list(_document_registry.keys())}"
            )
        return _document_registry[target]

    return target


class PopulateEngine:
    """Engine for resolving document references (Ref[T] fields).

    Supports caching and circular reference detection.
    """

    def __init__(self) -> None:
        self._cache: dict[tuple[str, ObjectId], Any] = {}
        self._in_progress: set[tuple[str, ObjectId]] = set()

    def _cache_key(self, collection_name: str, oid: ObjectId) -> tuple[str, ObjectId]:
        return (collection_name, oid)

    async def populate_one(self, doc: Any, field: str) -> None:
        """Resolve a single reference field on a single document."""
        value = getattr(doc, field)
        if not isinstance(value, ObjectId):
            # Already resolved or None
            return

        target_class = _resolve_target_class(type(doc), field)
        key = self._cache_key(target_class._collection_name, value)

        # Circular reference detection
        if key in self._in_progress:
            return

        # Check cache
        if key in self._cache:
            object.__setattr__(doc, field, self._cache[key])
            return

        self._in_progress.add(key)
        try:
            target_doc = await target_class.find_one({"_id": value})
            if target_doc is not None:
                self._cache[key] = target_doc
                object.__setattr__(doc, field, target_doc)
        finally:
            self._in_progress.discard(key)

    async def populate_many(self, docs: list[Any], field: str) -> None:
        """Batch-resolve a reference field across multiple documents.

        Collects all ObjectIds and performs a single $in query to avoid N+1.
        Uses cache to skip already-resolved references.
        """
        if not docs:
            return

        # Collect ObjectIds that need resolving
        id_to_docs: dict[ObjectId, list[Any]] = {}
        for doc in docs:
            value = getattr(doc, field)
            if isinstance(value, ObjectId):
                id_to_docs.setdefault(value, []).append(doc)

        if not id_to_docs:
            return

        target_class = _resolve_target_class(type(docs[0]), field)

        # Check cache first, only query uncached ids
        uncached_ids: list[ObjectId] = []
        for oid, doc_list in id_to_docs.items():
            key = self._cache_key(target_class._collection_name, oid)
            if key in self._cache:
                # Use cached value
                for doc in doc_list:
                    object.__setattr__(doc, field, self._cache[key])
            elif key not in self._in_progress:
                uncached_ids.append(oid)

        if not uncached_ids:
            return

        # Mark in-progress for circular detection
        in_progress_keys = []
        for oid in uncached_ids:
            key = self._cache_key(target_class._collection_name, oid)
            self._in_progress.add(key)
            in_progress_keys.append(key)

        try:
            # Single batch query
            collection = target_class.get_collection()
            cursor = collection.find({"_id": {"$in": uncached_ids}})

            # Map results back
            async for raw in cursor:
                resolved = target_class._from_mongo(raw)
                key = self._cache_key(target_class._collection_name, raw["_id"])
                self._cache[key] = resolved
                for doc in id_to_docs.get(raw["_id"], []):
                    object.__setattr__(doc, field, resolved)
        finally:
            for key in in_progress_keys:
                self._in_progress.discard(key)

    async def populate_nested(self, docs: list[Any], path: str) -> None:
        """Handle dot-notation populate like 'author.company'.

        Populates level by level: first 'author', then 'company' on the resolved authors.

        Args:
            docs: List of documents to populate
            path: Dot-notation path (e.g., "author.company")

        Raises:
            ValueError: If populate path exceeds maximum depth or is invalid
        """
        from pygoose.utils.types import MAX_POPULATE_DEPTH

        parts = path.split(".")

        # Validate depth limit
        if len(parts) > MAX_POPULATE_DEPTH:
            raise ValueError(
                f"Populate path exceeds maximum depth ({MAX_POPULATE_DEPTH}): {path}"
            )

        # Validate no empty parts (e.g., "author..company")
        if any(not part for part in parts):
            raise ValueError(f"Invalid populate path (empty segment): {path}")

        current_docs = docs

        for i, part in enumerate(parts):
            if not current_docs:
                break

            # Populate this level
            await self.populate_many(current_docs, part)

            # Collect the resolved docs for the next level
            if i < len(parts) - 1:
                next_docs = []
                for doc in current_docs:
                    resolved = getattr(doc, part, None)
                    if resolved is not None and not isinstance(resolved, ObjectId):
                        next_docs.append(resolved)
                # Deduplicate by id
                seen = set()
                deduped = []
                for d in next_docs:
                    if hasattr(d, "id") and d.id not in seen:
                        seen.add(d.id)
                        deduped.append(d)
                current_docs = deduped


class LazyRef(Generic[T]):
    """Lazy reference that resolves on demand with caching."""

    def __init__(self, document: Any, field_name: str, engine: PopulateEngine | None = None) -> None:
        self._document = document
        self._field_name = field_name
        self._engine = engine or PopulateEngine()
        self._resolved: Any = None

    @property
    def ref_id(self) -> ObjectId | None:
        """Get the raw ObjectId of the reference."""
        value = getattr(self._document, self._field_name)
        if isinstance(value, ObjectId):
            return value
        return getattr(value, "id", None)

    async def resolve(self) -> T | None:
        """Fetch the referenced document. Uses cache after first resolution."""
        if self._resolved is not None:
            return self._resolved

        value = getattr(self._document, self._field_name)
        if not isinstance(value, ObjectId):
            # Already resolved
            self._resolved = value
            return value

        await self._engine.populate_one(self._document, self._field_name)
        resolved = getattr(self._document, self._field_name)
        if not isinstance(resolved, ObjectId):
            self._resolved = resolved
        return self._resolved
