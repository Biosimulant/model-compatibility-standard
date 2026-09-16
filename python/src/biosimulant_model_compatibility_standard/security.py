"""Deterministic limits for untrusted compatibility documents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ResourceLimitError(ValueError):
    """Raised when an input exceeds a validator safety limit."""


@dataclass(frozen=True)
class ResourceLimits:
    """Conservative defaults shared by the Python and TypeScript packages."""

    max_document_bytes: int = 4 * 1024 * 1024
    max_depth: int = 64
    max_nodes: int = 200_000
    max_string_bytes: int = 1024 * 1024
    max_array_items: int = 100_000
    max_object_properties: int = 100_000
    max_profile_refs: int = 100
    max_rules: int = 10_000


DEFAULT_RESOURCE_LIMITS = ResourceLimits()


def ensure_text_limit(text: str | bytes, *, limits: ResourceLimits = DEFAULT_RESOURCE_LIMITS) -> None:
    size = len(text) if isinstance(text, bytes) else len(text.encode("utf-8"))
    if size > limits.max_document_bytes:
        raise ResourceLimitError(
            f"Document is {size} bytes; the limit is {limits.max_document_bytes} bytes."
        )


def ensure_json_limits(value: Any, *, limits: ResourceLimits = DEFAULT_RESOURCE_LIMITS) -> None:
    """Reject cyclic, excessively deep, or excessively large JSON-shaped values."""

    nodes = 0
    active: set[int] = set()
    stack: list[tuple[Any, int, bool]] = [(value, 0, False)]
    while stack:
        current, depth, leaving = stack.pop()
        if leaving:
            active.discard(id(current))
            continue

        nodes += 1
        if nodes > limits.max_nodes:
            raise ResourceLimitError(
                f"Document contains more than {limits.max_nodes} JSON values."
            )
        if depth > limits.max_depth:
            raise ResourceLimitError(
                f"Document nesting exceeds the limit of {limits.max_depth}."
            )
        if isinstance(current, str):
            if len(current.encode("utf-8")) > limits.max_string_bytes:
                raise ResourceLimitError(
                    f"A string exceeds the limit of {limits.max_string_bytes} bytes."
                )
            continue
        if current is None or isinstance(current, (bool, int, float)):
            continue
        if not isinstance(current, (dict, list)):
            raise ResourceLimitError(
                f"Value of type {type(current).__name__} is not JSON-compatible."
            )

        identity = id(current)
        if identity in active:
            raise ResourceLimitError("Document contains a reference cycle.")
        active.add(identity)
        stack.append((current, depth, True))

        if isinstance(current, list):
            if len(current) > limits.max_array_items:
                raise ResourceLimitError(
                    f"An array contains more than {limits.max_array_items} items."
                )
            stack.extend((child, depth + 1, False) for child in reversed(current))
        else:
            if len(current) > limits.max_object_properties:
                raise ResourceLimitError(
                    "An object contains more than "
                    f"{limits.max_object_properties} properties."
                )
            for key, child in reversed(list(current.items())):
                if not isinstance(key, str):
                    raise ResourceLimitError("JSON object keys must be strings.")
                stack.append((child, depth + 1, False))
                stack.append((key, depth + 1, False))
