"""Specification-driven normalization helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .bundle import Bundle, get_bundle
from .validation import validate_manifest


def _normalize_value(value: Any, pointer: str, set_paths: set[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalize_value(child, f"{pointer}/{key}", set_paths)
            for key, child in value.items()
        }
    if isinstance(value, list):
        normalized = [_normalize_value(child, f"{pointer}/{index}", set_paths) for index, child in enumerate(value)]
        if pointer in set_paths:
            from .canonical import canonical_bytes

            normalized.sort(key=canonical_bytes)
        return normalized
    return value


def normalize_contract(contract: dict[str, Any], *, bundle: Bundle | None = None) -> dict[str, Any]:
    active = bundle or get_bundle()
    rules = active.read_json("rules/normalization.json")
    set_paths = set(rules.get("set_like_paths", []))
    return _normalize_value(deepcopy(contract), "/contract", set_paths)


def normalize_manifest(manifest: dict[str, Any], *, bundle: Bundle | None = None) -> dict[str, Any]:
    active = bundle or get_bundle()
    findings = validate_manifest(manifest, bundle=active)
    if findings:
        messages = "; ".join(f"{item.path}: {item.message}" for item in findings)
        raise ValueError(f"Invalid opted-in compatibility declaration: {messages}")
    result = deepcopy(manifest)
    if "compatibility" not in result:
        return result
    result["compatibility"]["profiles"] = sorted(
        result["compatibility"].get("profiles", []), key=lambda item: item["ref"]
    )
    for direction in ("inputs", "outputs"):
        for port in result.get("io", {}).get(direction, []):
            if "contract" in port:
                port["contract"] = normalize_contract(port["contract"], bundle=active)
            for profile in port.get("accepted_profiles", []):
                if "contract" in profile:
                    profile["contract"] = normalize_contract(profile["contract"], bundle=active)
    return result
