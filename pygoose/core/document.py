from __future__ import annotations

from typing import Any, ClassVar, Optional, Self, TYPE_CHECKING

if TYPE_CHECKING:
    from pygoose.core.queryset import QuerySet

from bson import ObjectId
from pydantic import BaseModel, Field, PrivateAttr
from pymongo.asynchronous.collection import AsyncCollection

from pygoose.core.connection import get_database
from pygoose.fields.encrypted import decrypt_value, encrypt_value, detect_encrypted_fields
from pygoose.utils.exceptions import DocumentNotFound
from pygoose.fields.base import PyObjectId
from pygoose.lifecycle.hooks import PRE_DELETE, PRE_SAVE, PRE_VALIDATE, POST_DELETE, POST_SAVE, POST_UPDATE, collect_hooks, run_hooks
from pygoose.lifecycle.observability import track_query
from pygoose.utils.types import DocumentData, FilterSpec
from pygoose.utils.settings import SettingsResolver

# Global registry mapping class name -> Document subclass
_document_registry: dict[str, type[Document]] = {}


class Document(BaseModel):
    """Base document class for MongoDB models.

    Provides CRUD operations, dirty tracking, and automatic collection binding.
    """

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    # Private state
    _is_new: bool = PrivateAttr(default=True)
    _dirty_fields: set[str] = PrivateAttr(default_factory=set)
    _is_loaded: bool = PrivateAttr(default=False)

    # ClassVars — set by __init_subclass__
    _collection_name: ClassVar[str] = ""
    _connection_alias: ClassVar[str] = "default"
    _hooks: ClassVar[dict[str, list[str]]] = {}
    _auto_populate: ClassVar[list[str]] = []
    _encrypted_fields: ClassVar[set[str]] = set()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        # Skip registration for intermediate abstract-like bases
        if cls.__name__ == "Document":
            return

        # Resolve settings using SettingsResolver
        cls._collection_name = SettingsResolver.get_collection_name(cls)
        cls._connection_alias = SettingsResolver.get_connection_alias(cls)
        cls._auto_populate = SettingsResolver.get_auto_populate_fields(cls)

        # Collect lifecycle hooks
        cls._hooks = collect_hooks(cls)

        # Register in global registry
        _document_registry[cls.__name__] = cls

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Called after Pydantic has fully processed the model fields."""
        super().__pydantic_init_subclass__(**kwargs)
        cls._encrypted_fields = detect_encrypted_fields(cls)

    def __setattr__(self, name: str, value: Any) -> None:
        # Track dirty fields after the document is loaded from DB
        if (
            name != "id"
            and hasattr(self, "_is_loaded")
            and self._is_loaded
            and name in self.__class__.model_fields
        ):
            self._dirty_fields.add(name)
        super().__setattr__(name, value)

    # --- Dirty tracking ---

    @property
    def is_dirty(self) -> bool:
        return len(self._dirty_fields) > 0

    @property
    def dirty_fields(self) -> set[str]:
        return set(self._dirty_fields)

    def _mark_loaded(self) -> None:
        """Mark document as loaded from DB, clearing dirty state."""
        self._dirty_fields = set()
        self._is_loaded = True
        self._is_new = False

    def _get_update_doc(self) -> DocumentData:
        """Build a $set update document from dirty fields only."""
        if not self._dirty_fields:
            return {}
        changes = {}
        data = self._to_mongo()
        for field_name in self._dirty_fields:
            # Use the alias if present for mongo field name
            field_info = self.__class__.model_fields[field_name]
            mongo_key = field_info.alias or field_name
            changes[mongo_key] = data.get(mongo_key, data.get(field_name))
        return {"$set": changes}

    # --- Serialization ---

    def _to_mongo(self) -> DocumentData:
        """Convert document to MongoDB-compatible dict.

        Uses mode='python' to preserve native types like ObjectId
        (instead of serializing them to strings for JSON).
        """
        data = self.model_dump(by_alias=True, mode="python")
        # Remove None _id (for new documents)
        if data.get("_id") is None:
            data.pop("_id", None)
        # Encrypt fields
        if self.__class__._encrypted_fields:
            for field_name in self.__class__._encrypted_fields:
                value = data.get(field_name)
                if value is not None:
                    data[field_name] = encrypt_value(value)
        return data

    @classmethod
    def _from_mongo(cls, data: DocumentData) -> Self:
        """Create a document instance from MongoDB data."""
        if cls._encrypted_fields:
            data = dict(data)  # Copy to avoid mutating cursor result
            for field_name in cls._encrypted_fields:
                value = data.get(field_name)
                if value is not None:
                    data[field_name] = decrypt_value(value)
        doc = cls.model_validate(data)
        doc._mark_loaded()
        return doc

    # --- Collection access ---

    @classmethod
    def get_collection(cls) -> AsyncCollection:
        """Get the MongoDB collection for this document class."""
        db = get_database(cls._connection_alias)
        return db[cls._collection_name]

    # --- Indexing ---

    @classmethod
    async def ensure_indexes(cls) -> list[str]:
        """Create all indexes defined on this document class.

        Reads field-level indexes from Indexed() fields and class-level
        indexes from Settings.indexes. Returns list of created index names.
        """
        from pygoose.fields.indexed import IndexSpec

        collection = cls.get_collection()
        index_names: list[str] = []

        # Field-level indexes from json_schema_extra
        for field_name, field_info in cls.model_fields.items():
            extra = field_info.json_schema_extra
            if extra and isinstance(extra, dict) and extra.get("_pygoose_index"):
                keys = [(field_name, extra.get("_index_direction", 1))]
                kwargs: dict[str, Any] = {}
                if extra.get("_index_unique"):
                    kwargs["unique"] = True
                if extra.get("_index_sparse"):
                    kwargs["sparse"] = True
                name = await collection.create_index(keys, **kwargs)
                index_names.append(name)

        # Class-level indexes from Settings.indexes
        settings = getattr(cls, "Settings", None)
        if settings and hasattr(settings, "indexes"):
            for spec in settings.indexes:
                if not isinstance(spec, IndexSpec):
                    spec = IndexSpec(**spec) if isinstance(spec, dict) else spec
                keys, kwargs = spec.to_pymongo()
                name = await collection.create_index(keys, **kwargs)
                index_names.append(name)

        return index_names

    # --- Class-level CRUD ---

    @classmethod
    async def create(cls, **kwargs: Any) -> Self:
        """Create and insert a new document."""
        doc = cls(**kwargs)
        await doc.insert()
        return doc

    @classmethod
    async def get(cls, id: ObjectId | str) -> Self:
        """Find a document by its _id. Raises DocumentNotFound if missing."""
        if isinstance(id, str):
            id = ObjectId(id)
        async with track_query("get", cls._collection_name, cls.__name__, filter={"_id": id}):
            collection = cls.get_collection()
            data = await collection.find_one({"_id": id})
            if data is None:
                raise DocumentNotFound(
                    f"{cls.__name__} with id '{id}' not found"
                )
            doc = cls._from_mongo(data)
        if cls._auto_populate:
            await doc.populate(*cls._auto_populate)
        return doc

    @classmethod
    async def find_one(cls, filter: FilterSpec | None = None, **kwargs: Any) -> Self | None:
        """Find a single document matching the filter."""
        from pygoose.utils.types import merge_filters

        filter = merge_filters(filter, **kwargs)
        async with track_query("find_one", cls._collection_name, cls.__name__, filter=filter):
            collection = cls.get_collection()
            data = await collection.find_one(filter)
            if data is None:
                return None
            doc = cls._from_mongo(data)
        if cls._auto_populate:
            await doc.populate(*cls._auto_populate)
        return doc

    @classmethod
    def find(cls, filter: FilterSpec | None = None, **kwargs: Any) -> "QuerySet[Self]":
        """Return a QuerySet for fluent query building.

        Args:
            filter: MongoDB filter criteria
            **kwargs: Additional filter criteria

        Returns:
            QuerySet for this document type
        """
        from pygoose.core.queryset import QuerySet
        from pygoose.utils.types import merge_filters

        merged = merge_filters(filter, **kwargs)
        return QuerySet(cls, merged)

    # --- Instance-level CRUD ---

    async def insert(self) -> None:
        """Insert this document into the database."""
        await run_hooks(self, PRE_VALIDATE)
        await run_hooks(self, PRE_SAVE)
        async with track_query("insert", self._collection_name, self.__class__.__name__):
            collection = self.get_collection()
            data = self._to_mongo()
            result = await collection.insert_one(data)
            self.id = result.inserted_id
            self._mark_loaded()
        await run_hooks(self, POST_SAVE)

    async def save(self) -> None:
        """Save the document. Insert if new, update dirty fields if existing."""
        if self._is_new:
            await self.insert()
            return

        if not self.is_dirty:
            return

        await run_hooks(self, PRE_VALIDATE)
        await run_hooks(self, PRE_SAVE)
        async with track_query("save", self._collection_name, self.__class__.__name__):
            update_doc = self._get_update_doc()
            collection = self.get_collection()
            await collection.update_one({"_id": self.id}, update_doc)
            self._dirty_fields = set()
        await run_hooks(self, POST_SAVE)

    async def delete(self) -> None:
        """Delete this document from the database."""
        await run_hooks(self, PRE_DELETE)
        async with track_query("delete", self._collection_name, self.__class__.__name__):
            collection = self.get_collection()
            await collection.delete_one({"_id": self.id})
        await run_hooks(self, POST_DELETE)

    async def reload(self) -> None:
        """Re-fetch this document from the database."""
        async with track_query("reload", self._collection_name, self.__class__.__name__):
            collection = self.get_collection()
            data = await collection.find_one({"_id": self.id})
            if data is None:
                raise DocumentNotFound(
                    f"{self.__class__.__name__} with id '{self.id}' not found"
                )
            # Update all fields from the fresh data
            refreshed = self.__class__.model_validate(data)
            for field_name in self.__class__.model_fields:
                object.__setattr__(self, field_name, getattr(refreshed, field_name))
            self._mark_loaded()

    async def update(self, **kwargs: Any) -> None:
        """Atomic partial update: validate fields and values, update in DB, and refresh local state.

        Args:
            **kwargs: Field names and values to update

        Raises:
            ValueError: If field doesn't exist or value is invalid
        """
        from pydantic import ValidationError

        # Step 1: Validate field existence
        for key in kwargs:
            if key not in self.__class__.model_fields:
                raise ValueError(f"Unknown field: {key}")

        # Step 2: Validate field values using Pydantic
        # Create a temporary model instance with current + updated values
        try:
            current_data = self.model_dump(mode="python")
            current_data.update(kwargs)
            # This will validate all fields including the updates
            validation_instance = self.__class__.model_validate(current_data)
        except ValidationError as e:
            raise ValueError(f"Invalid update values: {e}") from e

        # Step 3: Update database
        async with track_query("update", self._collection_name, self.__class__.__name__, update=kwargs):
            collection = self.get_collection()
            await collection.update_one({"_id": self.id}, {"$set": kwargs})

            # Update local state with validated values
            for key, value in kwargs.items():
                object.__setattr__(self, key, value)
            # Don't mark these as dirty since they're already persisted
            self._dirty_fields -= set(kwargs.keys())
        await run_hooks(self, POST_UPDATE)

    async def populate(self, *fields: str) -> Self:
        """Populate reference fields on this document."""
        from pygoose.core.reference import PopulateEngine

        engine = PopulateEngine()
        for field in fields:
            if "." in field:
                await engine.populate_nested([self], field)
            else:
                await engine.populate_one(self, field)
        return self
