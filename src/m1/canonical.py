"""Minimal deterministic JSON profile for Cerberus M1."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any


class CanonicalizationError(ValueError):
    pass


def _normalize(value: Any) -> Any:
    if value is None:
        raise CanonicalizationError("null is forbidden; omit optional fields")
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if not -(2**63) <= value <= 2**63 - 1:
            raise CanonicalizationError("integer is outside signed 64-bit range")
        return value
    if isinstance(value, float):
        raise CanonicalizationError("floating-point numbers are forbidden")
    if isinstance(value, str):
        normalized = unicodedata.normalize("NFC", value)
        try:
            normalized.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise CanonicalizationError("string contains an invalid Unicode scalar") from exc
        return normalized
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError("object keys must be strings")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise CanonicalizationError("Unicode normalization creates a duplicate key")
            normalized[normalized_key] = _normalize(item)
        return normalized
    raise CanonicalizationError(f"unsupported value type: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    normalized = _normalize(value)
    text = json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return text.encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

