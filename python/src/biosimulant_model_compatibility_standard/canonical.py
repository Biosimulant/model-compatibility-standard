"""RFC 8785 serialization and content digests."""

from __future__ import annotations

import hashlib
from typing import Any

import rfc8785


def canonical_bytes(value: Any) -> bytes:
    """Return RFC 8785 canonical JSON bytes, rejecting non-JSON numbers."""
    return rfc8785.dumps(value)


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()
