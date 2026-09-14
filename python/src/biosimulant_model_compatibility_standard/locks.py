"""Deterministic compatibility.lock.json generation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .bundle import Bundle, get_bundle
from .canonical import digest
from .validation import validate_manifest


def build_compatibility_lock(manifest: dict[str, Any], *, bundle: Bundle | None = None) -> dict[str, Any]:
    active = bundle or get_bundle()
    findings = validate_manifest(manifest, bundle=active)
    if findings:
        messages = "; ".join(f"{item.path}: {item.message}" for item in findings)
        raise ValueError(f"Invalid opted-in compatibility declaration: {messages}")

    imports = sorted(manifest.get("compatibility", {}).get("profiles", []), key=lambda item: item["ref"])
    contracts = []
    for direction in ("inputs", "outputs"):
        for port in manifest.get("io", {}).get(direction, []):
            if "contract" in port:
                value = deepcopy(port["contract"])
                contracts.append({
                    "direction": direction,
                    "port": port["name"],
                    "contract": value,
                    "contract_digest": digest(value),
                })
    contracts.sort(key=lambda item: (item["direction"], item["port"]))
    lock = {
        "schema_version": "0.1",
        "standard": "https://biosimulant.com/standards/model-compatibility/v0.1",
        "bundle_sha256": active.digest,
        "contracts": contracts,
        "resolved_references": imports,
        "canonicalization": "RFC8785",
        "components": {"profile_count": len(imports), "contract_count": len(contracts)},
    }
    lock["digest"] = digest(lock)
    return lock
