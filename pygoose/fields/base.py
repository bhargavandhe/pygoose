from __future__ import annotations

from typing import Any

from bson import ObjectId
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


class PyObjectId(ObjectId):
    """Pydantic v2-compatible ObjectId type.

    Accepts ObjectId or str input, validates, and serializes to string for JSON.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_wrap_validator_function(
            cls._validate,
            core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.str_schema(),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: str(v),
                info_arg=False,
            ),
        )

    @classmethod
    def _validate(cls, value: Any, handler: Any) -> ObjectId:
        if isinstance(value, ObjectId):
            return value
        if isinstance(value, str):
            if not ObjectId.is_valid(value):
                raise ValueError(f"Invalid ObjectId: {value}")
            return ObjectId(value)
        raise ValueError(f"Cannot convert {type(value)} to ObjectId")
