"""Small, safe JSON Pointer helpers used by declarative rules."""

from __future__ import annotations

from typing import Any

MISSING = object()


def get_pointer(document: Any, pointer: str, default: Any = MISSING) -> Any:
    if pointer in ("", "/"):
        return document
    if not pointer.startswith("/"):
        raise ValueError(f"JSON Pointer must start with '/': {pointer}")
    current = document
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            return default
    return current


def get_dotted(document: Any, dotted: str, default: Any = MISSING) -> Any:
    current = document
    for token in dotted.split("."):
        if isinstance(current, dict) and token in current:
            current = current[token]
        else:
            return default
    return current
