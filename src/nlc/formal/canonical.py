"""Canonical NLC state encoding, reusing the frozen M1 JSON profile."""

from __future__ import annotations

import json
import types
import unicodedata
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any, Union, get_args, get_origin, get_type_hints

from m1.canonical import CanonicalizationError, canonical_bytes, sha256_hex

from . import model
from .model import FormalValidationError, NLCFormalState


class FormalDecodingError(FormalValidationError):
    pass


_DATACLASS_TYPES = {
    value.__name__: value
    for value in vars(model).values()
    if isinstance(value, type) and is_dataclass(value)
}


def _sort_key(value: Any) -> bytes:
    return canonical_bytes(to_primitive(value))


def to_primitive(value: Any) -> Any:
    if value is None:
        raise CanonicalizationError("null is forbidden; tagged state variants omit inapplicable fields")
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        result: dict[str, Any] = {"formal_type": type(value).__name__}
        for field in fields(value):
            item = getattr(value, field.name)
            if item is not None:
                result[field.name] = to_primitive(item)
        return result
    if isinstance(value, tuple):
        return [to_primitive(item) for item in value]
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, list):
        raise CanonicalizationError("mutable list input is forbidden; use immutable tuples")
    if isinstance(value, dict):
        raise CanonicalizationError("mutable mapping input is forbidden; use typed immutable records")
    if isinstance(value, float):
        raise CanonicalizationError("floating-point numbers are forbidden")
    raise CanonicalizationError(f"unsupported formal value type: {type(value).__name__}")


def canonical_state_bytes(value: Any) -> bytes:
    return canonical_bytes(to_primitive(value))


def formal_sha256(value: Any) -> str:
    return sha256_hex(canonical_state_bytes(value))


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        normalized = unicodedata.normalize("NFC", key)
        if normalized in result:
            raise FormalDecodingError("duplicate object key")
        result[normalized] = value
    return result


def _parse_as(value: Any, annotation: Any) -> Any:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (Union, types.UnionType):
        if value is None and type(None) in args:
            return None
        failures: list[Exception] = []
        for candidate in args:
            if candidate is type(None):
                continue
            try:
                return _parse_as(value, candidate)
            except (FormalDecodingError, FormalValidationError, TypeError, ValueError) as exc:
                failures.append(exc)
        raise FormalDecodingError(f"value does not match tagged union: {failures}")
    if origin is tuple:
        if not isinstance(value, list):
            raise FormalDecodingError("tuple field must be encoded as a JSON array")
        item_type = args[0]
        return tuple(_parse_as(item, item_type) for item in value)
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        if not isinstance(value, str):
            raise FormalDecodingError("enum must be a string")
        try:
            return annotation(value)
        except ValueError as exc:
            raise FormalDecodingError(f"unknown {annotation.__name__} enum: {value}") from exc
    if isinstance(annotation, type) and is_dataclass(annotation):
        return _parse_dataclass(value, annotation)
    if annotation is str:
        if not isinstance(value, str):
            raise FormalDecodingError("expected string")
        return unicodedata.normalize("NFC", value)
    if annotation is bool:
        if not isinstance(value, bool):
            raise FormalDecodingError("expected boolean")
        return value
    if annotation is int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise FormalDecodingError("expected integer")
        return value
    raise FormalDecodingError(f"unsupported annotation: {annotation}")


def _parse_dataclass(value: Any, cls: type[Any]) -> Any:
    if not isinstance(value, dict):
        raise FormalDecodingError(f"{cls.__name__} must be an object")
    if value.get("formal_type") != cls.__name__:
        raise FormalDecodingError(f"expected formal_type {cls.__name__}")
    hints = get_type_hints(cls)
    known = {field.name for field in fields(cls)} | {"formal_type"}
    if set(value) - known:
        raise FormalDecodingError(f"unknown fields for {cls.__name__}: {sorted(set(value)-known)}")
    kwargs: dict[str, Any] = {}
    for field in fields(cls):
        if field.name in value:
            kwargs[field.name] = _parse_as(value[field.name], hints[field.name])
        elif type(None) in get_args(hints[field.name]):
            kwargs[field.name] = None
        else:
            raise FormalDecodingError(f"missing required field {cls.__name__}.{field.name}")
    try:
        return cls(**kwargs)
    except TypeError as exc:
        raise FormalDecodingError(f"malformed {cls.__name__}: {exc}") from exc


def _load_json(data: bytes | str) -> tuple[str, Any]:
    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise FormalDecodingError("state is not strict UTF-8") from exc
    elif isinstance(data, str):
        text = data
    else:
        raise FormalDecodingError("decoder accepts only bytes or text, never mutable mappings")
    try:
        raw = json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_float=lambda _: (_ for _ in ()).throw(FormalDecodingError("floating point is forbidden")),
            parse_constant=lambda _: (_ for _ in ()).throw(FormalDecodingError("non-finite number is forbidden")),
        )
    except json.JSONDecodeError as exc:
        raise FormalDecodingError("malformed JSON") from exc
    if raw is None:
        raise FormalDecodingError("null is forbidden")
    return text, raw


def decode_formal(data: bytes | str, *, require_canonical_input: bool = False) -> Any:
    text, raw = _load_json(data)
    if not isinstance(raw, dict) or not isinstance(raw.get("formal_type"), str):
        raise FormalDecodingError("formal_type tag is required")
    cls = _DATACLASS_TYPES.get(raw["formal_type"])
    if cls is None:
        raise FormalDecodingError(f"unknown formal_type: {raw['formal_type']}")
    result = _parse_dataclass(raw, cls)
    if require_canonical_input and canonical_state_bytes(result) != text.encode("utf-8"):
        raise FormalDecodingError("input bytes are not canonical")
    return result


def decode_state(data: bytes | str, *, require_canonical_input: bool = False) -> NLCFormalState:
    result = decode_formal(data, require_canonical_input=require_canonical_input)
    if not isinstance(result, NLCFormalState):
        raise FormalDecodingError("top-level state must be NLCFormalState")
    return result
