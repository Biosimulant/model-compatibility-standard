#!/usr/bin/env python3
"""Generate spec/v0.1 from source/catalogue.review.json.

Run with --check to confirm the committed spec/v0.1 is up to date without changing it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "catalogue.review.json"
OUTPUT = ROOT / "spec" / "v0.1"
STANDARD = "https://biosimulant.com/standards/model-compatibility/v0.1"
JSON_TYPES = ["string", "number", "integer", "boolean", "array", "object", "null"]

STATUSES = [
    "EXACT",
    "DIRECT_COMPATIBLE",
    "LOSSLESS_CONVERSION_AVAILABLE",
    "LOSSY_CONVERSION_REQUIRES_APPROVAL",
    "INFERENCE_MODEL_REQUIRED",
    "CONDITIONAL",
    "INCOMPATIBLE",
    "UNKNOWN",
]
POLICY_DECISIONS = ["ALLOW", "APPROVAL_REQUIRED", "BLOCK"]
QUALITY_DECISIONS = ["READY", "REVIEW", "BLOCKED"]

OPERATORS = [
    "equal",
    "not-equal",
    "in",
    "not-in",
    "subset",
    "superset",
    "range",
    "pattern",
    "same-dimension",
    "unit-convertible",
    "term-equivalent",
    "term-subsumes",
    "labels-equal",
    "labels-permutation",
    "mapping-total",
    "mapping-bijective",
    "context-compatible",
    "digest-equal",
]

REASON_CODES = {
    "BMCS_EXACT": "The source and target contracts are identical after normalization.",
    "BMCS_DIRECT": "The source already meets the target's requirements, with no conversion.",
    "BMCS_REQUIRED_MISSING": "The target requires a field that the source doesn't provide.",
    "BMCS_VALUE_MISMATCH": "A source value doesn't match what the target requires.",
    "BMCS_UNIT_CONVERSION": "A lossless unit conversion is available.",
    "BMCS_LOSSY_PATH": "The chosen conversion loses information or maps it ambiguously.",
    "BMCS_INFERENCE_PATH": "The chosen path relies on an inference model.",
    "BMCS_CONDITION_UNRESOLVED": "A required precondition hasn't been checked or isn't met.",
    "BMCS_PROFILE_UNRESOLVED": "The profile isn't in the installed bundle.",
    "BMCS_DIGEST_MISMATCH": "The content doesn't match its declared sha256.",
    "BMCS_REFERENCE_CYCLE": "Profiles or contracts extend each other in a loop.",
    "BMCS_PROFILE_NOT_REVIEWED": "The profile hasn't finished scientific review.",
    "BMCS_SCHEMA_INVALID": "The document doesn't match its JSON Schema.",
    "BMCS_PROFILE_VALUE_INVALID": "A value doesn't meet a profile requirement.",
    "BMCS_PROFILE_NOT_IMPORTED": "A port uses a profile that isn't listed in compatibility.profiles.",
    "BMCS_CONTRACT_NOT_DECLARED": "One or both ports have no compatibility contract.",
    "BMCS_EXACT_CONTRACT": "The two contracts are identical.",
    "BMCS_REQUIRED_EVIDENCE_MISSING": "Information needed for the comparison is missing.",
    "BMCS_OPERATOR_REQUIRES_SNAPSHOT": "This check needs pinned ontology or mapping data, which isn't available.",
    "BMCS_OPERATOR_INPUT_INVALID": "A comparison operator received invalid or unsafe input.",
    "BMCS_RESOURCE_LIMIT_EXCEEDED": "The document exceeds a validator safety limit.",
    "BMCS_REFINEMENT_WITHOUT_BASE": "An accepted representation declares a contract without a common input contract.",
    "BMCS_REFINEMENT_WEAKENS_CONTRACT": "An accepted representation changes a common input invariant.",
    "BMCS_RULE_SATISFIED": "A comparison rule passed.",
}

SET_LIKE_PATHS = [
    "/contract/profile_refs",
    "/contract/semantic/qualifiers",
    "/contract/biological_context/disease",
    "/contract/biological_context/intervention",
    "/contract/security/data_use",
]


def dump_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()


def canonical_bytes(value: Any) -> bytes:
    # For the values generated here (no floats), sorted-key json.dumps gives the same bytes
    # as RFC 8785. The Python and TypeScript packages use real RFC 8785 libraries.
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def write_json(root: Path, relative: str, value: Any) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(dump_bytes(value))


def item_pointer(path: str) -> str:
    clean = path.replace("[]", "").strip(".")
    return "/contract/" + "/".join(part for part in clean.split(".") if part)


def item_operator(path: str, family: str) -> str:
    if path.endswith(".unit") or path == "accepted_units":
        return "unit-convertible"
    if path.endswith(".axes") or path.endswith(".labels"):
        return "labels-equal"
    if "mapping" in path and path.endswith((".coverage", ".total")):
        return "mapping-total"
    if family == "biological_context":
        return "context-compatible"
    if family in {"semantic", "identifiers"}:
        return "term-equivalent"
    if path.endswith(".sha256") or path.endswith(".digest"):
        return "digest-equal"
    return "equal"


def example_value(path: str) -> Any:
    leaf = path.replace("[]", "").split(".")[-1]
    if leaf in {"axes", "labels", "qualifiers", "disease", "intervention", "data_use"}:
        return [f"example-{leaf}"]
    if leaf in {
        "canonical",
        "ordered",
        "sparse",
        "encrypted",
        "required",
        "dynamic",
        "reversible",
    }:
        return True
    if leaf in {
        "min",
        "max",
        "minimum",
        "maximum",
        "confidence",
        "variance",
        "byte_size",
        "cardinality",
    }:
        return 1
    if leaf == "species":
        return "NCBITaxon:9606"
    if leaf == "unit":
        return "1"
    if leaf == "kind":
        return "scalar"
    return f"example-{leaf.replace('_', '-')}"


def set_path(document: dict[str, Any], path: str, value: Any) -> None:
    parts = [part for part in path.replace("[]", "").split(".") if part]
    current = document
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    if parts:
        current[parts[-1]] = value


def contract_schema(items: list[dict[str, Any]]) -> dict[str, Any]:
    families: dict[str, set[str]] = {}
    for item in items:
        path = str(item["path"])
        if path.startswith(("compatibility.", "profiles[].")) or "." not in path:
            continue
        family, rest = path.replace("[]", "").split(".", 1)
        if family in {"contract", "io", "accepted_profiles"}:
            continue
        families.setdefault(family, set()).add(rest.split(".", 1)[0])

    object_properties: dict[str, Any] = {
        "ref": {"type": "string", "format": "uri"},
        "sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
        "profile_refs": {
            "type": "array",
            "uniqueItems": True,
            "items": {"type": "string", "format": "uri"},
        },
        "extensions": {
            "type": "object",
            "propertyNames": {"pattern": "^[a-z][a-z0-9.-]+:[A-Za-z0-9._-]+$"},
        },
    }
    for family, keys in sorted(families.items()):
        object_properties[family] = {
            "type": "object",
            "properties": {key: {"type": JSON_TYPES} for key in sorted(keys)},
            "additionalProperties": False,
        }
    object_properties["constraints"] = {
        "type": "array",
        "items": {"$ref": "rule.schema.json"},
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{STANDARD}/schemas/port-contract.schema.json",
        "title": "Biosimulant Port Contract",
        "type": "object",
        "properties": object_properties,
        "additionalProperties": False,
    }


def schemas(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    ref = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{STANDARD}/schemas/profile-reference.schema.json",
        "title": "Profile Reference",
        "type": "object",
        "required": ["ref"],
        "properties": {
            "ref": {"type": "string", "format": "uri"},
            "sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            "required": {"type": "boolean", "default": True},
        },
        "additionalProperties": False,
    }
    rule = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{STANDARD}/schemas/rule.schema.json",
        "title": "Compatibility Rule",
        "type": "object",
        "required": ["source", "target", "operator", "missing", "reason_code"],
        "properties": {
            "source": {"type": "string", "pattern": "^/"},
            "target": {"type": "string", "pattern": "^/"},
            "operator": {"enum": OPERATORS},
            "missing": {"enum": ["unknown", "conditional", "incompatible", "ignore"]},
            "severity": {"enum": ["info", "warning", "error"]},
            "reason_code": {"type": "string", "pattern": "^BMCS_[A-Z0-9_]+$"},
            "parameters": {"type": "object"},
        },
        "additionalProperties": False,
    }
    profile = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{STANDARD}/schemas/profile-definition.schema.json",
        "title": "Compatibility Profile Definition",
        "type": "object",
        "required": [
            "$id", "profile_id", "version", "domain", "name", "label", "description",
            "stage", "review", "applies_to", "item_packs", "requirements",
            "comparison_rules", "transformation_policy", "scientific_claim",
        ],
        "properties": {
            "$schema": {"type": "string", "format": "uri"},
            "$id": {"type": "string", "format": "uri"},
            "profile_id": {"type": "string", "pattern": "^[a-z0-9-]+/[a-z0-9-]+@0\\.1$"},
            "version": {"type": "string"},
            "domain": {"type": "string"},
            "domain_label": {"type": "string"},
            "name": {"type": "string"},
            "label": {"type": "string"},
            "description": {"type": "string", "minLength": 20},
            "stage": {"enum": ["CURRENT", "FOUNDATION", "V0.1_PILOT", "WAVE_2", "CONTROLLED", "DEFERRED"]},
            "review": {
                "type": "object",
                "required": ["status", "sources"],
                "properties": {
                    "status": {"enum": ["candidate", "draft", "reviewed", "deprecated", "revoked"]},
                    "reviewer": {"type": ["string", "null"]},
                    "reviewed_at": {"type": ["string", "null"], "format": "date"},
                    "sources": {"type": "array", "items": {"type": "object"}},
                },
                "additionalProperties": False,
            },
            "release_eligible": {"type": "boolean"},
            "applies_to": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"enum": ["scalar", "array", "record", "event", "artifact"]}},
            "extends": {"type": "array", "uniqueItems": True, "items": {"type": "string", "format": "uri"}},
            "fixed": {"type": "object"},
            "allowed": {"type": "object"},
            "item_packs": {"type": "array", "uniqueItems": True, "items": {"type": "string"}},
            "requirements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["path", "level"],
                    "properties": {
                        "path": {"type": "string", "pattern": "^[a-z]"},
                        "level": {"enum": ["required", "conditional", "recommended", "optional"]},
                        "schema": {"type": "object"},
                        "when": {"type": "object"},
                    },
                    "additionalProperties": False,
                },
            },
            "comparison_rules": {"type": "array", "items": {"$ref": "rule.schema.json"}},
            "transformation_policy": {
                "type": "object",
                "required": ["lossless", "lossy", "inference"],
                "properties": {
                    "lossless": {"enum": ["allow", "block"]},
                    "lossy": {"enum": ["approval", "block"]},
                    "inference": {"enum": ["approval", "block"]},
                },
                "additionalProperties": False,
            },
            "compatibility_notes": {"type": "string"},
            "scientific_claim": {"type": "string", "minLength": 20},
        },
        "additionalProperties": False,
    }
    manifest_extension = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{STANDARD}/schemas/manifest-extension.schema.json",
        "title": "model.yaml Compatibility Extension",
        "type": "object",
        "required": ["schema_version", "compatibility", "io"],
        "properties": {
            "schema_version": {"const": "2.0"},
            "compatibility": {
                "type": "object",
                "required": ["standard"],
                "properties": {
                    "standard": {"const": STANDARD},
                    "profiles": {"type": "array", "uniqueItems": True, "items": {"$ref": "profile-reference.schema.json"}},
                    "extensions": {"type": "object"},
                },
                "additionalProperties": False,
            },
            "io": {
                "type": "object",
                "properties": {
                    direction: {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name"],
                            "properties": {
                                "name": {"type": "string", "minLength": 1},
                                "contract": {"$ref": "port-contract.schema.json"},
                                "accepted_profiles": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {"contract": {"$ref": "port-contract.schema.json"}},
                                        "additionalProperties": True,
                                    },
                                },
                            },
                            "additionalProperties": True,
                        },
                    }
                    for direction in ("inputs", "outputs")
                },
                "additionalProperties": True,
            },
        },
        "additionalProperties": True,
    }

    def simple(name: str, title: str, required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{STANDARD}/schemas/{name}.schema.json",
            "title": title,
            "type": "object",
            "required": required,
            "properties": properties,
            "additionalProperties": False,
        }

    finding = simple(
        "compatibility-finding", "Compatibility Finding",
        ["dimension", "state", "severity", "reason_code", "explanation"],
        {
            "dimension": {"type": "string"}, "state": {"enum": STATUSES},
            "severity": {"enum": ["info", "warning", "error"]},
            "reason_code": {"type": "string", "pattern": "^BMCS_[A-Z0-9_]+$"},
            "source_path": {"type": ["string", "null"]}, "target_path": {"type": ["string", "null"]},
            "evidence": {"type": "object"}, "explanation": {"type": "string"},
            "remediation": {"type": ["string", "null"]},
        },
    )
    report = simple(
        "compatibility-report", "Compatibility Report",
        ["schema_version", "standard", "bundle_sha256", "source", "target", "status", "policy_decision", "findings", "digest"],
        {
            "schema_version": {"const": "0.1"}, "standard": {"const": STANDARD},
            "bundle_sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            "source": {"type": "object"}, "target": {"type": "object"},
            "status": {"enum": STATUSES}, "policy_decision": {"enum": POLICY_DECISIONS},
            "quality_reference": {"type": ["object", "null"]},
            "findings": {"type": "array", "items": {"$ref": "compatibility-finding.schema.json"}},
            "paths": {"type": "array", "items": {"type": "object"}},
            "snapshots": {"type": "object"},
            "digest": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
        },
    )
    policy = simple(
        "compatibility-policy", "Compatibility Policy",
        ["schema_version", "unknown", "conditional", "lossless", "lossy", "inference"],
        {
            "schema_version": {"const": "0.1"},
            "unknown": {"enum": POLICY_DECISIONS}, "conditional": {"enum": POLICY_DECISIONS},
            "lossless": {"enum": POLICY_DECISIONS}, "lossy": {"enum": POLICY_DECISIONS},
            "inference": {"enum": POLICY_DECISIONS}, "license": {"type": "object"},
            "security": {"type": "object"}, "cost": {"type": "object"},
            "data_boundary": {"type": "object"}, "extensions": {"type": "object"},
        },
    )
    capability_properties = {
        "schema_version": {"const": "0.1"}, "ref": {"type": "string", "format": "uri"},
        "sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
        "source": {"type": "object"}, "target": {"type": "object"},
        "state": {"enum": ["reviewed", "revoked"]},
        "loss_score": {"type": "number", "minimum": 0},
        "execution_cost": {"type": "number", "minimum": 0},
        "preconditions": {"type": "array", "items": {"$ref": "rule.schema.json"}},
        "evidence": {"type": "array", "items": {"type": "object"}},
        "release": {"type": "object"}, "limitations": {"type": "array", "items": {"type": "string"}},
    }
    adapter = simple(
        "adapter-capability", "Adapter Capability",
        ["schema_version", "ref", "sha256", "source", "target", "state", "transformation_class", "information_loss", "release"],
        {**capability_properties, "transformation_class": {"enum": ["representation", "unit", "identifier", "normalization", "projection", "aggregation"]}, "information_loss": {"enum": ["none", "bounded", "lossy"]}},
    )
    inference = simple(
        "inference-capability", "Inference Capability",
        ["schema_version", "ref", "sha256", "source", "target", "state", "inferred_modality", "assumptions", "uncertainty", "release"],
        {**capability_properties, "inferred_modality": {"type": "string"}, "assumptions": {"type": "array", "items": {"type": "string"}}, "uncertainty": {"type": "object"}},
    )
    plan = simple(
        "resolution-plan", "Resolution Plan",
        ["schema_version", "standard", "bundle_sha256", "nodes", "edges", "reports", "policy", "approvals", "digest"],
        {
            "schema_version": {"const": "0.1"}, "standard": {"const": STANDARD},
            "bundle_sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            "nodes": {"type": "array", "items": {"type": "object"}},
            "edges": {"type": "array", "items": {"type": "object"}},
            "reports": {"type": "array", "items": {"type": "object"}},
            "policy": {"type": "object"}, "approvals": {"type": "array", "items": {"type": "object"}},
            "immutable_references": {"type": "array", "items": {"type": "object"}},
            "expires_at": {"type": ["string", "null"], "format": "date-time"},
            "digest": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
        },
    )
    envelope = simple(
        "signal-envelope", "Signal Envelope",
        ["schema_version", "contract_digest"],
        {
            "schema_version": {"const": "0.1"}, "contract_digest": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            "value": {}, "artifact": {"type": "object"}, "actual_context": {"type": "object"},
            "origin": {"type": "object"}, "uncertainty": {"type": "object"},
            "provenance": {"type": "object"}, "observation_time": {"type": ["string", "number", "null"]},
        },
    )
    lock = simple(
        "compatibility-lock", "Compatibility Lock",
        ["schema_version", "standard", "bundle_sha256", "contracts", "resolved_references", "canonicalization", "digest"],
        {
            "schema_version": {"const": "0.1"}, "standard": {"const": STANDARD},
            "bundle_sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            "contracts": {"type": "array", "items": {"type": "object"}},
            "resolved_references": {"type": "array", "items": {"type": "object"}},
            "canonicalization": {"const": "RFC8785"}, "components": {"type": "object"},
            "digest": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
        },
    )
    conformance = simple(
        "conformance-manifest", "Conformance Manifest",
        ["schema_version", "implementation", "standard", "bundle_sha256", "supported_levels", "fixture_results", "digest"],
        {
            "schema_version": {"const": "0.1"}, "implementation": {"type": "object"},
            "standard": {"const": STANDARD}, "bundle_sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            "supported_levels": {"type": "array", "items": {"type": "string"}},
            "fixture_results": {"type": "object"}, "digest": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
        },
    )
    catalogue = simple(
        "catalogue", "Profile Catalogue",
        ["schema_version", "standard", "counts", "item_definitions", "item_packs", "profiles"],
        {
            "schema_version": {"const": "0.1"}, "standard": {"const": STANDARD},
            "status": {"type": "string"}, "bundle_sha256": {"type": ["string", "null"]},
            "counts": {"type": "object"}, "item_definitions": {"type": "array", "items": {"type": "object"}},
            "item_packs": {"type": "array", "items": {"type": "object"}},
            "profiles": {"type": "array", "items": {"type": "object"}},
        },
    )
    return {
        "profile-reference": ref,
        "rule": rule,
        "port-contract": contract_schema(items),
        "profile-definition": profile,
        "manifest-extension": manifest_extension,
        "catalogue": catalogue,
        "adapter-capability": adapter,
        "inference-capability": inference,
        "compatibility-policy": policy,
        "compatibility-finding": finding,
        "compatibility-report": report,
        "resolution-plan": plan,
        "signal-envelope": envelope,
        "compatibility-lock": lock,
        "conformance-manifest": conformance,
    }


def build(root: Path) -> None:
    source = json.loads(SOURCE.read_text())
    profiles = source["profiles"]
    items = source["item_definitions"]
    packs = source["item_packs"]
    if (len(profiles), len(items), len(packs)) != (650, 266, 30):
        raise SystemExit(
            "source/catalogue.review.json must have 650 profiles, 266 items and 30 packs; "
            f"found {len(profiles)}, {len(items)} and {len(packs)}"
        )

    enriched_items: list[dict[str, Any]] = []
    item_index: dict[str, dict[str, Any]] = {}
    for raw in items:
        item = dict(raw)
        item["comparison_operator"] = item_operator(str(item["path"]), str(item["family"]))
        item["missing_behavior"] = "unknown"
        item["json_schema"] = {"type": JSON_TYPES}
        item["ordered"] = item_pointer(str(item["path"])) not in SET_LIKE_PATHS
        enriched_items.append(item)
        item_index[str(item["path"])] = item

    definitions: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for raw in profiles:
        requirements = [
            {"path": path, "level": "required", "schema": item_index.get(path, {}).get("json_schema", {})}
            for path in raw["required_items"]
        ]
        rules = [
            {
                "source": item_pointer(path),
                "target": item_pointer(path),
                "operator": item_index.get(path, {}).get("comparison_operator", "equal"),
                "missing": "unknown",
                "severity": "error",
                "reason_code": "BMCS_VALUE_MISMATCH",
            }
            for path in raw["required_items"]
        ]
        definition = {
            "$schema": f"{STANDARD}/schemas/profile-definition.schema.json",
            "$id": raw["ref"],
            "profile_id": raw["id"],
            "version": raw["version"],
            "domain": raw["domain"],
            "domain_label": raw["domain_label"],
            "name": raw["name"],
            "label": raw["label"],
            "description": raw["description"],
            "stage": raw["stage"],
            "review": {
                "status": raw["review_status"],
                "reviewer": None,
                "reviewed_at": None,
                "sources": [],
            },
            "release_eligible": False,
            "applies_to": raw["applies_to"],
            "extends": [],
            "fixed": {},
            "allowed": {},
            "item_packs": raw["required_item_packs"],
            "requirements": requirements,
            "comparison_rules": rules,
            "transformation_policy": {"lossless": "allow", "lossy": "approval", "inference": "approval"},
            "compatibility_notes": raw["compatibility_notes"],
            "scientific_claim": raw["scientific_claim"],
        }
        definition_digest = digest(definition)
        definitions.append(definition)
        summaries.append(
            {
                "id": raw["id"], "ref": raw["ref"], "sha256": definition_digest,
                "version": raw["version"], "domain": raw["domain"], "domain_label": raw["domain_label"],
                "name": raw["name"], "label": raw["label"], "description": raw["description"],
                "stage": raw["stage"], "review_status": raw["review_status"],
                "release_eligible": False, "applies_to": raw["applies_to"],
                "required_item_count": len(requirements), "item_packs": raw["required_item_packs"],
            }
        )

    for name, schema in schemas(enriched_items).items():
        write_json(root, f"schemas/{name}.schema.json", schema)

    write_json(root, "rules/operators.json", {"standard": STANDARD, "operators": OPERATORS})
    write_json(root, "rules/reason-codes.json", {"standard": STANDARD, "reason_codes": REASON_CODES})
    write_json(root, "rules/statuses.json", {"standard": STANDARD, "technical": STATUSES, "policy": POLICY_DECISIONS, "quality": QUALITY_DECISIONS})
    write_json(root, "rules/normalization.json", {"standard": STANDARD, "canonicalization": "RFC8785", "set_like_paths": SET_LIKE_PATHS})
    write_json(
        root,
        "rules/unit-conversions.json",
        {
            "standard": STANDARD,
            "conversions": [
                {"from": "nM", "to": "uM", "factor": "0.001", "offset": "0", "loss": "none"},
                {"from": "uM", "to": "nM", "factor": "1000", "offset": "0", "loss": "none"},
                {"from": "mM", "to": "uM", "factor": "1000", "offset": "0", "loss": "none"},
                {"from": "uM", "to": "mM", "factor": "0.001", "offset": "0", "loss": "none"},
            ],
        },
    )
    write_json(root, "catalogue/items.json", {"schema_version": "0.1", "standard": STANDARD, "items": enriched_items})
    write_json(root, "catalogue/item-packs.json", {"schema_version": "0.1", "standard": STANDARD, "item_packs": packs})

    canonical_cases = [
        {"name": "object-key-order", "input": {"z": 1, "a": {"b": True, "a": None}}},
        {"name": "unicode-and-arrays", "input": {"label": "β-cell", "values": [3, 2, 1]}},
    ]
    for case in canonical_cases:
        canonical = json.dumps(case["input"], ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        case["canonical"] = canonical
        case["sha256"] = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    write_json(
        root,
        "fixtures/golden/canonicalization.json",
        {"canonicalization": "RFC8785", "cases": canonical_cases},
    )
    write_json(
        root,
        "fixtures/golden/comparison-statuses.json",
        {
            "cases": [
                {"name": "exact", "source": {"semantic": {"concept": "concentration"}}, "target": {"semantic": {"concept": "concentration"}}, "status": "EXACT"},
                {"name": "missing-contract", "source": None, "target": {"semantic": {"concept": "concentration"}}, "status": "UNKNOWN"},
                {"name": "lossless-unit", "source": {"measurement": {"unit": "nM"}}, "target": {"measurement": {"unit": "uM"}}, "status": "LOSSLESS_CONVERSION_AVAILABLE"},
                {"name": "context-contradiction", "source": {"biological_context": {"compartment": "extracellular"}}, "target": {"biological_context": {"compartment": "intracellular"}}, "status": "INCOMPATIBLE"},
            ]
        },
    )

    for definition in definitions:
        write_json(root, f"profiles/{definition['domain']}/{definition['name']}/v0.1.json", definition)
        valid_contract: dict[str, Any] = {}
        for requirement in definition["requirements"]:
            set_path(valid_contract, requirement["path"], example_value(requirement["path"]))
        invalid_contract = json.loads(json.dumps(valid_contract))
        first_path = definition["requirements"][0]["path"] if definition["requirements"] else None
        if first_path:
            parts = first_path.split(".")
            current = invalid_contract
            for part in parts[:-1]:
                current = current.get(part, {})
            current.pop(parts[-1], None)
        write_json(
            root,
            f"fixtures/profiles/{definition['domain']}/{definition['name']}.json",
            {
                "profile_ref": definition["$id"],
                "cases": [
                    {"name": "positive", "contract": valid_contract, "valid": True},
                    {"name": "negative-required-missing", "contract": invalid_contract, "valid": False, "reason_code": "BMCS_REQUIRED_MISSING"},
                    {"name": "comparison-unknown", "source": invalid_contract, "target": valid_contract, "status": "UNKNOWN"},
                ],
            },
        )

    catalogue = {
        "$schema": f"{STANDARD}/schemas/catalogue.schema.json",
        "$id": f"{STANDARD}/catalogue.json",
        "schema_version": "0.1",
        "standard": STANDARD,
        "status": "implementation-draft",
        "bundle_sha256": None,
        "counts": {"profiles": len(summaries), "item_definitions": len(enriched_items), "item_packs": len(packs)},
        "item_definitions": enriched_items,
        "item_packs": packs,
        "profiles": summaries,
    }
    write_json(root, "catalogue/catalogue.json", catalogue)

    (root / "examples").mkdir(parents=True, exist_ok=True)
    (root / "examples" / "legacy-model.yaml").write_text(
        'schema_version: "2.0"\nstandard: other\nbiosim:\n  entrypoint: src.model:Model\n  communication_step: 1.0\nio:\n  inputs:\n    - name: expression\n      signal_type: array\n      dtype: float32\n      shape: ["*"]\n  outputs: []\n'
    )
    example_ref = "https://biosimulant.com/standards/model-compatibility/profiles/transcriptome/gene-expression-counts/v0.1"
    example_digest = next(entry["sha256"] for entry in summaries if entry["ref"] == example_ref)
    (root / "examples" / "compatible-model.yaml").write_text(
        f'schema_version: "2.0"\nstandard: other\ncompatibility:\n  standard: https://biosimulant.com/standards/model-compatibility/v0.1\n  profiles:\n    - ref: {example_ref}\n      sha256: {example_digest}\nbiosim:\n  entrypoint: src.model:Model\n  communication_step: 1.0\nio:\n  inputs:\n    - name: expression\n      signal_type: array\n      dtype: float32\n      shape: ["*"]\n      contract:\n        profile_refs:\n          - {example_ref}\n        semantic:\n          concept: gene_expression\n          subject: biological_sample\n        representation:\n          kind: dense_vector\n        identifiers:\n          namespace: ensembl-gene\n          namespace_version: release-pinned\n        biological_context:\n          species: NCBITaxon:9606\n  outputs: []\n'
    )

    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "bundle.manifest.json":
            data = path.read_bytes()
            files.append({"path": path.relative_to(root).as_posix(), "sha256": "sha256:" + hashlib.sha256(data).hexdigest(), "size_bytes": len(data)})
    manifest_without_digest = {
        "schema_version": "0.1", "standard": STANDARD, "release": "0.1.0-alpha.4",
        "canonicalization": "RFC8785", "files": files,
        "counts": {"profiles": 650, "item_definitions": 266, "item_packs": 30},
        "ga_ready": False,
        "ga_blockers": ["Every profile still needs authoritative scientific sources and sign-off from a named domain reviewer."],
    }
    bundle_digest = digest(manifest_without_digest)
    write_json(root, "bundle.manifest.json", {**manifest_without_digest, "bundle_sha256": bundle_digest})


def compare_trees(left: Path, right: Path) -> list[str]:
    left_files = {p.relative_to(left).as_posix(): p.read_bytes() for p in left.rglob("*") if p.is_file()}
    right_files = {p.relative_to(right).as_posix(): p.read_bytes() for p in right.rglob("*") if p.is_file()}
    return sorted(name for name in set(left_files) | set(right_files) if left_files.get(name) != right_files.get(name))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate spec/v0.1 from source/catalogue.review.json.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="build into a temporary folder and fail if spec/v0.1 differs, without changing it",
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="bmcs-build-") as temp:
        generated = Path(temp) / "v0.1"
        build(generated)
        if args.check:
            differences = compare_trees(generated, OUTPUT) if OUTPUT.exists() else ["spec/v0.1 is missing"]
            if differences:
                raise SystemExit(
                    "spec/v0.1 is out of date. Run `python3 scripts/build_standard.py` to regenerate it.\n"
                    "Files that differ:\n" + "\n".join(differences[:50])
                )
            print("spec/v0.1 is up to date.")
            return
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(generated, OUTPUT)
        print(f"Generated {OUTPUT}")


if __name__ == "__main__":
    main()
