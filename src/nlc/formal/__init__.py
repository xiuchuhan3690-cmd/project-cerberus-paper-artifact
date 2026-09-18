"""Finite, immutable NLC-M0-T1 formal-domain representation."""

from .canonical import canonical_state_bytes, decode_state, formal_sha256
from .fixtures import full_formal_state
from .model import *  # noqa: F401,F403 - public formal vocabulary

__all__ = ["canonical_state_bytes", "decode_state", "formal_sha256", "full_formal_state"]

