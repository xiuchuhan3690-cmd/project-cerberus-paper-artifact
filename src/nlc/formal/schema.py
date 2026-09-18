"""Generate a complete JSON Schema view of the typed formal records."""

from __future__ import annotations

import types
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any, Union, get_args, get_origin, get_type_hints

from . import model
from .model import NLCFormalState


def _is_optional(annotation: Any) -> bool:
    return get_origin(annotation) in (Union, types.UnionType) and type(None) in get_args(annotation)


def _field_schema(annotation: Any, definitions: dict[str, Any]) -> dict[str, Any]:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (Union, types.UnionType):
        non_null = [item for item in args if item is not type(None)]
        if len(non_null) == 1:
            return _field_schema(non_null[0], definitions)
        return {"oneOf": [_field_schema(item, definitions) for item in non_null]}
    if origin is tuple:
        return {"type": "array", "items": _field_schema(args[0], definitions), "uniqueItems": True}
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return {"type": "string", "enum": [item.value for item in annotation]}
    if isinstance(annotation, type) and is_dataclass(annotation):
        _add_dataclass(annotation, definitions)
        return {"$ref": f"#/$defs/{annotation.__name__}"}
    if annotation is str:
        return {"type": "string"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is int:
        return {"type": "integer", "minimum": -(2**63), "maximum": 2**63 - 1}
    raise TypeError(f"unsupported formal annotation: {annotation}")


def _add_dataclass(cls: type[Any], definitions: dict[str, Any]) -> None:
    if cls.__name__ in definitions:
        return
    definitions[cls.__name__] = {}
    hints = get_type_hints(cls)
    properties: dict[str, Any] = {"formal_type": {"const": cls.__name__}}
    required = ["formal_type"]
    for field in fields(cls):
        annotation = hints[field.name]
        properties[field.name] = _field_schema(annotation, definitions)
        if not _is_optional(annotation):
            required.append(field.name)
    definitions[cls.__name__] = {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def formal_json_schema() -> dict[str, Any]:
    definitions: dict[str, Any] = {}
    _add_dataclass(NLCFormalState, definitions)
    for value in vars(model).values():
        if isinstance(value, type) and is_dataclass(value):
            _add_dataclass(value, definitions)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:cerberus:nlc:formal-state:1.0",
        "title": "Project Cerberus NLC Formal State v1",
        "$ref": "#/$defs/NLCFormalState",
        "$defs": dict(sorted(definitions.items())),
    }

