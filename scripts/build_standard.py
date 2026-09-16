#!/usr/bin/env python3
"""Generate spec/v0.1 from the human-authored YAML under source/.

Run with --check to confirm the committed spec/v0.1 is up to date without changing it.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]

# Load the unit parser straight from its file, so the generator shares one definition of what a
# unit means with the engines without taking on the package's runtime dependencies.
_units_spec = importlib.util.spec_from_file_location(
    "bmcs_units", ROOT / "python" / "src" / "biosimulant_model_compatibility_standard" / "units.py"
)
_units = importlib.util.module_from_spec(_units_spec)
# dataclasses resolve their annotations through sys.modules, so the module has to be registered
sys.modules["bmcs_units"] = _units
_units_spec.loader.exec_module(_units)
UnitError, parse_unit = _units.UnitError, _units.parse_unit
FIELDS_SOURCE = ROOT / "source" / "fields.yaml"
PROFILES_SOURCE = ROOT / "source" / "profiles"
QUANTITY_KINDS_SOURCE = ROOT / "source" / "quantity-kinds.yaml"

QUANTITY_KINDS: dict[str, Any] = {}
FIELD_INDEX: dict[str, Any] = {}
UCUM_TABLE: dict[str, Any] = {}


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(loader: UniqueKeyLoader, node: yaml.nodes.MappingNode, deep: bool = False) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except (yaml.YAMLError, ValueError) as error:
        raise SystemExit(f"{path.relative_to(ROOT)}: invalid YAML: {error}") from error
    if not isinstance(value, dict):
        raise SystemExit(f"{path.relative_to(ROOT)}: expected one YAML mapping")
    return value


def load_declarations() -> None:
    global QUANTITY_KINDS, UCUM_TABLE
    QUANTITY_KINDS = load_yaml(QUANTITY_KINDS_SOURCE)["kinds"]
    UCUM_TABLE = json.loads((ROOT / "source" / "vendor" / "ucum" / "ucum-table.json").read_text())


def example_species() -> str:
    """Return a schema-valid example, not a profile-level scientific assertion."""

    return "NCBITaxon:9606"
OUTPUT = ROOT / "spec" / "v0.1"
STANDARD = "https://biosimulant.com/standards/model-compatibility/v0.1"
RELEASE = "0.0.2"
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
    "representation-equivalent",
    "namespace-version-compatible",
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

REPRESENTATION_KINDS = {
    "scalar": ["scalar"],
    "array": ["dense_vector", "sparse_vector", "matrix", "sparse_matrix", "tensor", "array"],
    "record": ["record", "table"],
    "event": ["event"],
    "artifact": ["artifact", "file"],
}

SET_LIKE_PATHS = [
    "/contract/profile_refs",
    "/contract/semantic/qualifiers",
    "/contract/semantic/ontology_terms",
    "/contract/identifiers/mapping_refs",
    "/contract/uncertainty/quality_flags",
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


FIELD_DISPOSITIONS = {"required", "conditional", "recommended", "excluded"}


def load_fields() -> list[dict[str, Any]]:
    source = load_yaml(FIELDS_SOURCE)
    if source.get("schema_version") != "0.1":
        raise SystemExit("source/fields.yaml: schema_version must be '0.1'")
    defaults = source.get("defaults") or {}
    raw_fields = source.get("fields")
    if not isinstance(raw_fields, list) or not raw_fields:
        raise SystemExit("source/fields.yaml: fields must be a non-empty list")
    fields: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_fields:
        if not isinstance(raw, dict):
            raise SystemExit("source/fields.yaml: every field must be a mapping")
        path = raw.get("path")
        family = raw.get("family")
        schema = raw.get("schema")
        comparison = raw.get("comparison", defaults.get("comparison", "equal"))
        if not isinstance(path, str) or not path or path in seen:
            raise SystemExit(f"source/fields.yaml: invalid or duplicate field path: {path}")
        if not isinstance(family, str) or not family:
            raise SystemExit(f"source/fields.yaml: {path} needs a family")
        if not isinstance(schema, dict) or not schema:
            raise SystemExit(f"source/fields.yaml: {path} needs an explicit schema")
        if comparison not in OPERATORS:
            raise SystemExit(f"source/fields.yaml: {path} uses unknown comparison operator {comparison}")
        seen.add(path)
        fields.append(
            {
                "path": path,
                "family": family,
                "description": str(raw.get("description", defaults.get("description", ""))),
                "schema": schema,
                "comparison": comparison,
                "ordered": bool(raw.get("ordered", defaults.get("ordered", True))),
            }
        )
    return fields


def load_profiles() -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for path in sorted(PROFILES_SOURCE.rglob("*.yaml")):
        relative = path.relative_to(PROFILES_SOURCE)
        if len(relative.parts) != 2:
            raise SystemExit(f"{path.relative_to(ROOT)}: profiles must be source/profiles/<domain>/<name>.yaml")
        domain, filename = relative.parts
        name = Path(filename).stem
        source = load_yaml(path)
        if source.get("schema_version") != "0.1":
            raise SystemExit(f"{path.relative_to(ROOT)}: schema_version must be '0.1'")
        field_source = source.get("fields")
        if not isinstance(field_source, dict) or not field_source:
            raise SystemExit(f"{path.relative_to(ROOT)}: fields must be a non-empty mapping")
        dispositions: dict[str, dict[str, Any]] = {}
        for field_path, decision in field_source.items():
            if isinstance(decision, str):
                decision = {"disposition": decision}
            if not isinstance(field_path, str) or not isinstance(decision, dict):
                raise SystemExit(f"{path.relative_to(ROOT)}: every field needs a disposition")
            disposition = decision.get("disposition")
            if disposition not in FIELD_DISPOSITIONS:
                raise SystemExit(
                    f"{path.relative_to(ROOT)}: {field_path} has invalid disposition {disposition}"
                )
            if disposition == "conditional" and not decision.get("when"):
                raise SystemExit(f"{path.relative_to(ROOT)}: conditional field {field_path} needs 'when'")
            dispositions[field_path] = dict(decision)
        unknown = sorted(set(dispositions) - set(FIELD_INDEX))
        if unknown:
            raise SystemExit(f"{path.relative_to(ROOT)}: unknown fields: {', '.join(unknown)}")
        required = [field_path for field_path, decision in dispositions.items() if decision["disposition"] == "required"]
        if "semantic.concept" not in required:
            raise SystemExit(f"{path.relative_to(ROOT)}: semantic.concept must be required")
        examples = source.get("examples")
        if not isinstance(examples, list) or not examples:
            raise SystemExit(f"{path.relative_to(ROOT)}: examples must be a non-empty list")
        status = source.get("status")
        if status not in {"active", "deprecated"}:
            raise SystemExit(
                f"{path.relative_to(ROOT)}: status must be active or deprecated"
            )
        sources = source.get("sources")
        if not isinstance(sources, list) or not sources:
            raise SystemExit(
                f"{path.relative_to(ROOT)}: sources must contain at least one source"
            )
        for index, reference in enumerate(sources):
            if not isinstance(reference, dict):
                raise SystemExit(
                    f"{path.relative_to(ROOT)}: sources[{index}] must be a mapping"
                )
            if not isinstance(reference.get("title"), str) or not reference["title"].strip():
                raise SystemExit(
                    f"{path.relative_to(ROOT)}: sources[{index}].title is required"
                )
            if not isinstance(reference.get("url"), str) or not reference["url"].startswith(
                ("https://", "http://")
            ):
                raise SystemExit(
                    f"{path.relative_to(ROOT)}: sources[{index}].url must be an HTTP(S) URL"
                )
        profile_id = f"{domain}/{name}@0.1"
        if profile_id in seen_ids:
            raise SystemExit(f"{path.relative_to(ROOT)}: duplicate profile {profile_id}")
        seen_ids.add(profile_id)
        profiles.append(
            {
                "id": profile_id,
                "ref": f"{STANDARD.rsplit('/', 1)[0]}/profiles/{domain}/{name}/v0.1",
                "version": "0.1.0",
                "domain": domain,
                "domain_label": source.get("domain_label"),
                "name": name,
                "label": source.get("label"),
                "description": source.get("description"),
                "status": status,
                "applies_to": source.get("representations"),
                "field_dispositions": dispositions,
                "required_items": required,
                "intended_use": source.get("intended_use"),
                "limitations": source.get("limitations"),
                "sources": sources,
                "examples": examples,
                "compatibility_notes": (
                    "Two ports match only when every field the target requires is satisfied. "
                    "Missing required information returns UNKNOWN. Every conversion or inference "
                    "must be declared and versioned."
                ),
                "scientific_claim": (
                    "This profile checks whether two model interfaces fit together. It does not "
                    "show that a model is scientifically valid or clinically safe."
                ),
            }
        )
    if not profiles:
        raise SystemExit("source/profiles must contain at least one active YAML profile")
    return profiles


def field_pointer(path: str) -> str:
    clean = path.replace("[]", "").strip(".")
    return "/contract/" + "/".join(part for part in clean.split(".") if part)


def profile_concept(profile: dict[str, Any]) -> str:
    """Return a term identifier that does not change with the profile version."""

    return f"{STANDARD.rsplit('/', 1)[0]}/terms/{profile.get('domain')}/{profile.get('name')}"


def allowed_representation_kinds(profile: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for signal_type in profile.get("applies_to", []):
        values.extend(REPRESENTATION_KINDS.get(str(signal_type), []))
    return list(dict.fromkeys(values)) or ["record"]


# These operators need a pinned snapshot to decide anything. Without one the engine answers
# UNKNOWN, so a differing value is absent evidence rather than a contradiction.
SNAPSHOT_OPERATORS = {
    "term-equivalent",
    "term-subsumes",
    "mapping-total",
    "mapping-bijective",
    "namespace-version-compatible",
}


def contradiction_reason_code(path: str, definition: dict[str, Any]) -> str:
    """The code the engine actually reports for this contradiction.

    Where the profile fixes a quantity kind, a unit of another quantity is caught by the kind check
    before the unit rule is reached, and that check reports its own code.
    """

    if path == "measurement.unit" and get_path(definition.get("fixed", {}), "measurement.quantity"):
        return "BMCS_UNIT_DIMENSION_MISMATCH"
    return reason_code_for(path)


def policy_layer(path: str) -> bool:
    """Whether this item is decided by governance rather than by technical fit.

    Consent and data-use terms say whether two ports may exchange data at all. That is a policy
    outcome: it is reported as a policy finding and does not decide the technical status, so a
    contradiction in one of these fields produces no INCOMPATIBLE fixture.
    """

    return path.split(".")[0] == "security"


def needs_snapshot(path: str) -> bool:
    return (FIELD_INDEX.get(path) or {}).get("comparison_operator") in SNAPSHOT_OPERATORS


def reason_code_for(path: str) -> str:
    normalized = path.replace("[]", "").replace(".", "_").replace("-", "_").upper()
    return f"BMCS_{normalized}_MISMATCH"


def profile_fixed(profile: dict[str, Any]) -> dict[str, Any]:
    fixed: dict[str, Any] = {}
    if "semantic.concept" in profile.get("required_items", []):
        set_path(fixed, "semantic.concept", profile_concept(profile))
    return fixed


def profile_allowed(profile: dict[str, Any]) -> dict[str, Any]:
    allowed: dict[str, Any] = {}
    if "representation.kind" in profile.get("required_items", []):
        set_path(allowed, "representation.kind", allowed_representation_kinds(profile))
    return allowed


def get_path(document: dict[str, Any], path: str) -> Any:
    if "[]" in path:
        # A path through "[]" addresses every member of the array, so it resolves to one value per
        # member rather than to a single value.
        head, _, tail = path.partition("[]")
        container = get_path(document, head.strip("."))
        if not isinstance(container, list):
            return None
        leaf = tail.strip(".")
        return [get_path(item, leaf) if isinstance(item, dict) else None for item in container]
    current: Any = document
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def requirement_schema(profile: dict[str, Any], path: str) -> dict[str, Any]:
    fixed = get_path(profile_fixed(profile), path)
    if fixed is not None:
        return {"const": fixed}
    allowed = get_path(profile_allowed(profile), path)
    if isinstance(allowed, list) and allowed:
        return {"enum": allowed}
    return dict((FIELD_INDEX.get(path) or {}).get("json_schema") or {})


def measurement_unit() -> str:
    """Return a dimensionless example when no profile-specific quantity is declared."""

    return "1"


def axis_entries() -> list[Any]:
    """Return the smallest schema-valid axis example."""

    return [{"name": "axis"}]


def example_from_schema(schema: Any, leaf: str) -> Any:
    """Derive an example from the item's own schema.

    The catalogue schema is the authority on an item's type. Guessing from the leaf name produced a
    number where the schema said string, and a string where it said number.
    """

    if not isinstance(schema, dict):
        return None
    if "const" in schema:
        return schema["const"]
    if schema.get("enum"):
        return schema["enum"][0]
    declared = schema.get("type")
    if isinstance(declared, list):
        declared = next((entry for entry in declared if entry != "null"), None)
    if declared in {"number", "integer"}:
        return 1
    if declared == "boolean":
        return True
    if declared == "string" and schema.get("pattern") == "^sha256:[0-9a-f]{64}$":
        # The one pattern a readable placeholder cannot satisfy, including inside nested objects.
        return "sha256:" + "0" * 64
    if declared == "string" and schema.get("format") == "uri":
        # TypeScript's validator checks this format even though Python's does not, so a readable
        # placeholder would make the two engines disagree about the same fixture.
        return f"https://biosimulant.com/standards/model-compatibility/examples/{leaf.replace('_', '-')}"
    if declared == "array":
        item = example_from_schema(schema.get("items", {}), leaf)
        return [item if item is not None else f"example-{leaf.replace('_', '-')}"]
    if declared == "object":
        properties = schema.get("properties") or {}
        built = {name: example_from_schema(child, name) for name, child in properties.items()}
        return {name: value if value is not None else f"example-{name.replace('_', '-')}" for name, value in built.items()} or None
    return None


def example_value(path: str, profile: dict[str, Any] | None = None) -> Any:
    if profile is not None:
        fixed = get_path(profile_fixed(profile), path)
        if fixed is not None:
            return fixed
        allowed = get_path(profile_allowed(profile), path)
        if isinstance(allowed, list) and allowed:
            return allowed[0]
    leaf = path.replace("[]", "").split(".")[-1]
    if leaf == "axes" and profile is not None:
        return axis_entries()
    if leaf in {"axes", "qualifiers", "quality_flags"}:
        return [f"example-{leaf}"]
    if leaf == "mapping_refs":
        # An array of pinned mappings, not a label. Each entry is built from the
        # catalogue's own sub-item definitions, so the example cannot drift from their schemas.
        prefix = "identifiers.mapping_refs[]."
        entry = {sub[len(prefix):]: example_value(sub) for sub in FIELD_INDEX if sub.startswith(prefix)}
        return [entry] if entry else []
    if leaf.endswith("sha256") or leaf in {"digest", "structure_hash"}:
        # A digest item has a pattern to satisfy; "example-sha256" is not a digest.
        return "sha256:" + "0" * 64
    if leaf == "species":
        return example_species()
    if leaf == "unit":
        return measurement_unit()
    if leaf == "kind":
        return allowed_representation_kinds(profile or {})[0]
    if leaf == "concept" and profile is not None:
        return profile_concept(profile)
    if leaf == "subject" and profile is not None:
        return "biological_entity"
    if leaf == "quantity" and profile is not None:
        return "port-declared"
    if leaf == "scale":
        return "ratio"
    if leaf == "transform":
        return "identity"
    if leaf == "ordering":
        return "explicit"
    # Inferring a value from the item's schema comes last so explicit scientific examples win over
    # the first member of a generic enum.
    derived = example_from_schema((FIELD_INDEX.get(path) or {}).get("json_schema"), leaf)
    if derived is not None:
        return derived
    return f"example-{leaf.replace('_', '-')}"


def invalid_value_for(schema: dict[str, Any], valid: Any) -> Any:
    if "const" in schema:
        return f"{schema['const']}-different"
    if "enum" in schema:
        return "not-an-allowed-value"
    declared = schema.get("type")
    if declared == "string":
        return 7
    if declared in {"number", "integer"}:
        return "not-a-number"
    if declared == "boolean":
        return "not-a-boolean"
    if declared == "array":
        return "not-an-array"
    if declared == "object":
        return "not-an-object"
    return None if valid is not None else "invalid"


def incompatible_value(valid: Any, path: str) -> Any:
    if path == "biological_context.species":
        return "NCBITaxon:10090" if valid != "NCBITaxon:10090" else "NCBITaxon:9606"
    if path == "measurement.unit":
        return contradicting_unit(str(valid))
    if isinstance(valid, bool):
        return not valid
    if isinstance(valid, (int, float)):
        return valid + 1
    if isinstance(valid, list):
        return [*valid, "different"]
    if isinstance(valid, dict):
        return {**valid, "different": True}
    return f"{valid}-different"


def convertible_unit(unit: str) -> str | None:
    """Another spelling of the same quantity, for the lossless conversion fixture.

    Changing a metric prefix keeps the quantity and changes the number, which is exactly what a
    conversion fixture should exercise. Candidates are checked with the same parser the engines
    use, so the fixture can only claim a conversion the engine will actually find. A profile with
    no such alternative gets no conversion fixture, rather than the nanomolar-to-micromolar one it
    used to get whatever it measured.
    """

    try:
        base = parse_unit(unit, UCUM_TABLE)
    except UnitError:
        return None
    if base.arbitrary_codes or base.offset:
        return None
    candidates = [f"{prefix}{unit}" for prefix in ("m", "k", "u")]
    if len(unit) > 1:
        candidates.extend([unit[1:], f"m{unit[1:]}", f"k{unit[1:]}"])
    for candidate in candidates:
        if candidate == unit:
            continue
        try:
            other = parse_unit(candidate, UCUM_TABLE)
        except UnitError:
            continue
        if other.dimension == base.dimension and other.factor != base.factor and not other.arbitrary_codes and not other.offset:
            return candidate
    return None


def contradicting_unit(unit: str) -> str:
    """A unit of a different dimension, so the contradiction fixture is a real contradiction.

    The generator used to hard-code kg, which asserted that grams and kilograms are incompatible.
    """

    from_units = UCUM_TABLE.get("units", {})

    def dimension(code: str) -> tuple[int, ...] | None:
        entry = from_units.get(code)
        return tuple(entry["dim"]) if entry else None

    current = dimension(unit)
    for candidate in ("s", "kg", "m", "K", "Hz"):
        if dimension(candidate) != current:
            return candidate
    return "s"


def fixture_slug(path: str) -> str:
    return path.replace("[]", "").replace(".", "-").replace("_", "-")


def delete_path(document: dict[str, Any], path: str) -> None:
    if "[]" in path:
        # Deleting through "[]" removes the field from every member of the array. Stripping the
        # marker would otherwise be a silent no-op because the container is a list, not a dict.
        head, _, tail = path.partition("[]")
        container = get_path(document, head.strip("."))
        if isinstance(container, list):
            for item in container:
                if isinstance(item, dict):
                    delete_path(item, tail.strip("."))
        return
    parts = [part for part in path.split(".") if part]
    current: Any = document
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    if isinstance(current, dict) and parts:
        current.pop(parts[-1], None)


def effective_required_items(profile: dict[str, Any]) -> list[str]:
    """Return the authored v0 contract without catalogue-wide inferred requirements."""

    return list(dict.fromkeys(str(path) for path in profile.get("required_items", [])))


def set_path(document: dict[str, Any], path: str, value: Any) -> None:
    if "[]" in path:
        # Writing through "[]" writes into every member of the array. Stripping the marker instead
        # would write a dict over the array itself, which is what made per-axis requirements
        # unusable.
        head, _, tail = path.partition("[]")
        container = get_path(document, head.strip("."))
        if isinstance(container, list):
            for item in container:
                if isinstance(item, dict):
                    set_path(item, tail.strip("."), value)
        return
    parts = [part for part in path.split(".") if part]
    current = document
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    if parts:
        current[parts[-1]] = value


def gating_pointer(path: str) -> str:
    """Where the gating rule for a required field points.

    Almost always the field itself. representation.kind is the exception: conditional equivalence
    needs to see the sibling fields that would make a re-encoding lossless, so its rule points at the
    representation object.
    """

    return "/contract/representation" if path == "representation.kind" else field_pointer(path)


def internal_quality_errors(profile: dict[str, Any], definition: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if definition.get("status") not in {"active", "deprecated"}:
        errors.append("status is outside the published profile lifecycle")
    requirements = definition.get("requirements", [])
    paths = [item.get("path") for item in requirements]
    if len(paths) != len(set(paths)):
        errors.append("requirements contain duplicate paths")
    concept = get_path(definition.get("fixed", {}), "semantic.concept")
    if not concept:
        errors.append("semantic.concept is not fixed to this profile")
    elif isinstance(concept, str) and "/v0." in concept:
        # A versioned concept IRI would make a later profile version appear scientifically different
        # even when the meaning is unchanged.
        errors.append("semantic.concept embeds a profile version")
    kinds = get_path(definition.get("allowed", {}), "representation.kind")
    if not isinstance(kinds, list) or not kinds:
        errors.append("representation.kind has no allowed values")
    required_paths = [
        item["path"] for item in requirements
        if item.get("level") == "required" and "[]" not in item["path"]
    ]
    levels = {item.get("level") for item in requirements}
    if levels - {"required", "conditional", "recommended", "optional"}:
        errors.append("a requirement declares a level outside the published vocabulary")
    gating = [rule for rule in definition.get("comparison_rules", []) if rule.get("missing") != "ignore"]
    if sorted(rule["target"] for rule in gating) != sorted(gating_pointer(path) for path in required_paths):
        errors.append("each required field must have exactly one comparison rule")
    for requirement in requirements:
        schema = requirement.get("schema", {})
        if not isinstance(schema, dict) or not schema:
            errors.append(f"{requirement.get('path')} has no value schema")
        if schema.get("type") == JSON_TYPES:
            errors.append(f"{requirement.get('path')} still accepts every JSON type")
        declared_type = schema.get("type")
        if declared_type == "null" or (isinstance(declared_type, list) and "null" in declared_type):
            errors.append(f"{requirement.get('path')} allows null even though it is required")
    if not definition.get("sources"):
        errors.append("at least one source is required")
    if not definition.get("examples"):
        errors.append("at least one worked example is required")
    return errors


def contract_schema(fields: list[dict[str, Any]]) -> dict[str, Any]:
    families: dict[str, dict[str, dict[str, Any]]] = {}
    for field in fields:
        path = str(field["path"])
        if path.startswith(("compatibility.", "profiles[].")) or "." not in path:
            continue
        family, rest = path.replace("[]", "").split(".", 1)
        if family in {"contract", "io", "accepted_profiles"}:
            continue
        key = rest.split(".", 1)[0]
        # Prefer the schema for the direct family member. A deeper field
        # documents part of that member rather than replacing its shape.
        candidate = field.get("json_schema", {}) if "." not in rest else {"type": "object"}
        current = families.setdefault(family, {}).get(key)
        if current is None or "." not in rest:
            families[family][key] = candidate

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
            "properties": {key: keys[key] for key in sorted(keys)},
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


def schemas(fields: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    ref = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{STANDARD}/schemas/profile-reference.schema.json",
        "title": "Profile Reference",
        "type": "object",
        "required": ["ref", "sha256"],
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
            # A governance rule is reported separately instead of changing technical compatibility.
            "layer": {"enum": ["technical", "policy"]},
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
            "status", "applies_to", "intended_use", "limitations", "sources",
            "field_dispositions", "requirements", "comparison_rules", "examples",
            "transformation_policy", "scientific_claim",
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
            "status": {"enum": ["active", "deprecated"]},
            "applies_to": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"enum": ["scalar", "array", "record", "event", "artifact"]}},
            "extends": {"type": "array", "uniqueItems": True, "items": {"type": "string", "format": "uri"}},
            "fixed": {"type": "object"},
            "allowed": {"type": "object"},
            "intended_use": {"type": "string", "minLength": 20},
            "limitations": {
                "type": "array", "minItems": 1, "items": {"type": "string", "minLength": 10}
            },
            "sources": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["title", "url"],
                    "properties": {
                        "title": {"type": "string", "minLength": 1},
                        "url": {"type": "string", "format": "uri"},
                        "note": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
            },
            "field_dispositions": {
                "type": "object",
                "minProperties": 1,
                "additionalProperties": {
                    "type": "object",
                    "required": ["disposition"],
                    "properties": {
                        "disposition": {"enum": sorted(FIELD_DISPOSITIONS)},
                        "when": {"type": ["string", "object"]},
                        "note": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
            },
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
            "examples": {"type": "array", "minItems": 1, "items": {"type": "object"}},
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
        ["schema_version", "standard", "bundle_sha256", "source", "target", "status", "policy_decision", "findings", "policy_findings", "digest"],
        {
            "schema_version": {"const": "0.1"}, "standard": {"const": STANDARD},
            "bundle_sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            "source": {"type": "object"}, "target": {"type": "object"},
            "status": {"enum": STATUSES}, "policy_decision": {"enum": POLICY_DECISIONS},
            "quality_reference": {"type": ["object", "null"]},
            "findings": {"type": "array", "items": {"$ref": "compatibility-finding.schema.json"}},
            # Consent and data-use are governance outcomes, not statements about
            # whether two datasets fit together, so they are reported here rather than deciding
            # the technical status.
            "policy_findings": {"type": "array", "items": {"$ref": "compatibility-finding.schema.json"}},
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
        ["schema_version", "standard", "bundle_sha256", "technical_status", "nodes", "edges", "reports", "policy", "approvals", "digest"],
        {
            "schema_version": {"const": "0.1"}, "standard": {"const": STANDARD},
            "bundle_sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            # The status the chain carries. reports[] holds the terminal comparison, which is EXACT
            # whenever the last adapter lands exactly on the target, so a reader needs this to tell a
            # lossy chain from an inference one.
            "technical_status": {"enum": STATUSES},
            "nodes": {"type": "array", "items": {"type": "object"}},
            "edges": {"type": "array", "items": {"type": "object"}},
            "reports": {"type": "array", "items": {"type": "object"}},
            "policy": {"type": "object"}, "approvals": {"type": "array", "items": {"type": "object"}},
            "immutable_references": {"type": "array", "items": {"type": "object"}},
            "expires_at": {"type": ["string", "null"], "format": "date-time"},
            "digest": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
        },
    )
    # The engines consume three kinds of pinned snapshot and the standard published the format of
    # none of them. A snapshot is verified by digest, so the shape below is what a publisher has to
    # produce for the operators to read it.
    ontology_snapshot = simple(
        "ontology-snapshot", "Ontology Snapshot",
        ["ref", "sha256"],
        {
            "schema_version": {"const": "0.1"},
            "ref": {"type": "string", "format": "uri"},
            "sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            "ontology": {"type": "string", "minLength": 1},
            "release": {"type": "string", "minLength": 1},
            "license": {"type": "string", "minLength": 1},
            "equivalences": {"type": "array", "items": {"type": "array", "minItems": 2, "items": {"type": "string", "minLength": 1}}},
            "subsumptions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["parent", "child"],
                    "properties": {"parent": {"type": "string", "minLength": 1}, "child": {"type": "string", "minLength": 1}},
                    "additionalProperties": False,
                },
            },
        },
    )
    mapping_snapshot = simple(
        "mapping-snapshot", "Mapping Snapshot",
        ["ref", "sha256"],
        {
            "schema_version": {"const": "0.1"},
            "ref": {"type": "string", "format": "uri"},
            "sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            "source_namespace": {"type": "string", "minLength": 1},
            "target_namespace": {"type": "string", "minLength": 1},
            "release": {"type": "string", "minLength": 1},
            "license": {"type": "string", "minLength": 1},
            "mappings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["source"],
                    "properties": {
                        "source": {"type": "string", "minLength": 1},
                        "target": {"type": "string", "minLength": 1},
                        "targets": {"type": "array", "items": {"type": "string", "minLength": 1}},
                    },
                    "additionalProperties": False,
                },
            },
        },
    )
    namespace_snapshot = simple(
        "namespace-transition-snapshot", "Namespace Transition Snapshot",
        ["ref", "sha256", "namespace", "transitions"],
        {
            "schema_version": {"const": "0.1"},
            "ref": {"type": "string", "format": "uri"},
            "sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            "namespace": {"type": "string", "minLength": 1},
            "license": {"type": "string", "minLength": 1},
            "transitions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["from", "to"],
                    "properties": {
                        "from": {"type": "string", "minLength": 1},
                        "to": {"type": "string", "minLength": 1},
                        # A transition that retired and merged nothing preserves every identifier;
                        # one that did either is a real loss and needs approval.
                        "identifiers_retired": {"type": "integer", "minimum": 0},
                        "identifiers_merged": {"type": "integer", "minimum": 0},
                        "released_at": {"type": "string", "minLength": 1},
                    },
                    "additionalProperties": False,
                },
            },
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
        ["schema_version", "standard", "counts", "fields", "profiles"],
        {
            "schema_version": {"const": "0.1"}, "standard": {"const": STANDARD},
            "status": {"type": "string"}, "bundle_sha256": {"type": ["string", "null"]},
            "counts": {"type": "object"},
            "fields": {"type": "array", "items": {"type": "object"}},
            "profiles": {"type": "array", "items": {"type": "object"}},
        },
    )
    return {
        "profile-reference": ref,
        "rule": rule,
        "port-contract": contract_schema(fields),
        "profile-definition": profile,
        "manifest-extension": manifest_extension,
        "catalogue": catalogue,
        "adapter-capability": adapter,
        "inference-capability": inference,
        "compatibility-policy": policy,
        "compatibility-finding": finding,
        "compatibility-report": report,
        "resolution-plan": plan,
        "ontology-snapshot": ontology_snapshot,
        "mapping-snapshot": mapping_snapshot,
        "namespace-transition-snapshot": namespace_snapshot,
        "signal-envelope": envelope,
        "compatibility-lock": lock,
        "conformance-manifest": conformance,
    }


def build(root: Path) -> None:
    load_declarations()
    raw_fields = load_fields()
    enriched_fields: list[dict[str, Any]] = []
    field_index: dict[str, dict[str, Any]] = {}
    for raw in raw_fields:
        field = {
            "path": raw["path"],
            "family": raw["family"],
            "description": raw["description"],
            "comparison_operator": raw["comparison"],
            "missing_behavior": "unknown",
            "json_schema": raw["schema"],
            "value_type": "JSON value constrained by json_schema",
            "ordered": raw["ordered"],
            "requirement": "profile-dependent",
        }
        REASON_CODES.setdefault(
            reason_code_for(str(field["path"])),
            f"The value at {field['path']} is incompatible with the target profile.",
        )
        enriched_fields.append(field)
        field_index[str(field["path"])] = field
    FIELD_INDEX.clear()
    FIELD_INDEX.update(field_index)

    profiles = load_profiles()
    definitions: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for raw in profiles:
        raw = dict(raw, required_items=effective_required_items(raw))
        requirements: list[dict[str, Any]] = []
        for path, decision in raw["field_dispositions"].items():
            disposition = decision["disposition"]
            if disposition not in {"required", "conditional", "recommended"}:
                continue
            requirement = {
                "path": path,
                "level": disposition,
                "schema": requirement_schema(raw, path),
            }
            if disposition == "conditional":
                requirement["when"] = decision["when"]
            requirements.append(requirement)
        rules = [
            {
                # representation.kind is compared by conditional equivalence against the whole
                # representation object, so the operator can see whether the fields that would make
                # a re-encoding lossless are declared.
                "source": gating_pointer(path),
                "target": gating_pointer(path),
                "operator": "representation-equivalent" if path == "representation.kind" else field_index.get(path, {}).get("comparison_operator", "equal"),
                "missing": "unknown",
                "severity": "error",
                "reason_code": reason_code_for(path),
            }
            # A requirement addressing every member of an array is validated, not compared: JSON
            # Pointer cannot say "each element", and comparison of the array itself is already
            # covered by the rule on the array.
            for path in raw["required_items"]
            if "[]" not in path
        ]
        for entry in rules:
            # Governance rules are reported separately from technical compatibility.
            entry["layer"] = "policy" if entry["target"].startswith("/contract/security/") else "technical"
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
            "status": raw["status"],
            "applies_to": raw["applies_to"],
            "extends": [],
            "fixed": profile_fixed(raw),
            "allowed": profile_allowed(raw),
            "intended_use": raw["intended_use"],
            "limitations": raw["limitations"],
            "sources": raw["sources"],
            "field_dispositions": raw["field_dispositions"],
            "requirements": requirements,
            "comparison_rules": rules,
            "examples": raw["examples"],
            "transformation_policy": {"lossless": "allow", "lossy": "approval", "inference": "approval"},
            "compatibility_notes": raw["compatibility_notes"],
            "scientific_claim": raw["scientific_claim"],
        }
        quality_errors = internal_quality_errors(raw, definition)
        if quality_errors:
            raise SystemExit(
                f"{raw['id']} failed generated-profile checks:\n- "
                + "\n- ".join(quality_errors)
            )
        definition_digest = digest(definition)
        definitions.append(definition)
        summaries.append(
            {
                "id": raw["id"], "ref": raw["ref"], "sha256": definition_digest,
                "version": raw["version"], "domain": raw["domain"], "domain_label": raw["domain_label"],
                "name": raw["name"], "label": raw["label"], "description": raw["description"],
                "status": raw["status"], "applies_to": raw["applies_to"],
                "required_field_count": len(raw["required_items"]),
                "intended_use": raw["intended_use"],
            }
        )

    for name, schema in schemas(enriched_fields).items():
        write_json(root, f"schemas/{name}.schema.json", schema)

    write_json(root, "rules/operators.json", {"standard": STANDARD, "operators": OPERATORS})
    write_json(root, "rules/reason-codes.json", {"standard": STANDARD, "reason_codes": REASON_CODES})
    write_json(root, "rules/statuses.json", {"standard": STANDARD, "technical": STATUSES, "policy": POLICY_DECISIONS, "quality": QUALITY_DECISIONS})
    write_json(root, "rules/normalization.json", {"standard": STANDARD, "canonicalization": "RFC8785", "set_like_paths": SET_LIKE_PATHS})
    write_json(root, "rules/units.json", {"standard": STANDARD, **UCUM_TABLE})
    write_json(root, "rules/quantity-kinds.json", {"standard": STANDARD, "id_prefix": f"{STANDARD.rsplit('/', 1)[0]}/quantity-kinds/", "kinds": QUANTITY_KINDS})
    write_json(root, "catalogue/fields.json", {"schema_version": "0.1", "standard": STANDARD, "fields": enriched_fields})
    # The concept IRI is minted outside the versioned profile document so its scientific meaning
    # does not change merely because the profile contract receives a new version.
    terms = [
        {
            "id": profile_concept(profile),
            "label": profile["label"],
            "definition": profile["description"],
            "domain": profile["domain"],
            "domain_label": profile["domain_label"],
            "name": profile["name"],
            "term_version": "1.0.0",
            "minted_in": profile["version"],
            "profile_ref": profile["ref"],
            "scientific_claim": profile["scientific_claim"],
            "external_terms": [],
        }
        for profile in sorted(profiles, key=lambda item: (item["domain"], item["name"]))
    ]
    write_json(
        root,
        "catalogue/terms.json",
        {
            "schema_version": "0.1",
            "standard": STANDARD,
            "note": (
                "A term identifies what a port means and does not move when the profile version does. "
                "external_terms is empty when the profile does not declare an equivalent maintained "
                "external term at the same granularity."
            ),
            "count": len(terms),
            "terms": terms,
        },
    )

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
                {"name": "lossless-unit", "source": {"measurement": {"unit": "nmol/L"}}, "target": {"measurement": {"unit": "umol/L"}}, "status": "LOSSLESS_CONVERSION_AVAILABLE"},
                {"name": "context-contradiction", "source": {"biological_context": {"compartment": "extracellular"}}, "target": {"biological_context": {"compartment": "intracellular"}}, "status": "INCOMPATIBLE"},
            ]
        },
    )
    scientific_cases: list[dict[str, Any]] = []
    for profile in profiles:
        profile_path = f"{profile['domain']}/{profile['name']}"
        for example in profile["examples"]:
            scientific_cases.append({"kind": "guard", "profile": profile_path, **example})
    write_json(
        root,
        "fixtures/scientific.json",
        {
            "schema_version": "0.1",
            "title": "Scientific guards for the active v0 pilot profiles",
            "purpose": "Language-neutral scientific expectations authored with each active profile.",
            "profile_ref_prefix": f"{STANDARD.rsplit('/', 1)[0]}/profiles/",
            "profile_ref_suffix": "/v0.1",
            "cases": scientific_cases,
        },
    )

    source_profiles_by_ref = {profile["ref"]: profile for profile in profiles}
    for definition in definitions:
        source_profile = source_profiles_by_ref[definition["$id"]]
        write_json(root, f"profiles/{definition['domain']}/{definition['name']}/v0.1.json", definition)
        valid_contract: dict[str, Any] = {}
        for requirement in definition["requirements"]:
            if requirement["level"] != "required":
                continue
            path = requirement["path"]
            if "[]" in path:
                # The parent item builds the array from its profile declaration, so a member
                # requirement must not write a generic example over it: that is the same clobbering
                # Only fill a field the parent left empty.
                declared = get_path(valid_contract, path)
                if isinstance(declared, list) and declared and all(value is not None for value in declared):
                    continue
            set_path(valid_contract, path, example_value(path, source_profile))
        direct_contract = json.loads(json.dumps(valid_contract))
        if "origin.type" in {item["path"] for item in definition["requirements"] if item["level"] == "required"}:
            set_path(direct_contract, "origin.method", "declared")
        else:
            set_path(direct_contract, "origin.type", "declared")
        cases = [
            {"name": "positive", "contract": valid_contract, "valid": True},
            {"name": "comparison-direct", "source": direct_contract, "target": valid_contract, "status": "DIRECT_COMPATIBLE"},
        ]
        for requirement in definition["requirements"]:
            if requirement["level"] != "required":
                continue
            path = requirement["path"]
            slug = fixture_slug(path)
            missing_contract = json.loads(json.dumps(valid_contract))
            delete_path(missing_contract, path)
            invalid_contract = json.loads(json.dumps(valid_contract))
            set_path(
                invalid_contract,
                path,
                invalid_value_for(requirement["schema"], get_path(valid_contract, path)),
            )
            incompatible_contract = json.loads(json.dumps(valid_contract))
            set_path(
                incompatible_contract,
                path,
                incompatible_value(get_path(valid_contract, path), path),
            )
            cases.extend(
                [
                    {
                        "name": f"negative-required-missing-{slug}",
                        "contract": missing_contract,
                        "valid": False,
                        "reason_code": "BMCS_REQUIRED_MISSING",
                        "field": path,
                    },
                    {
                        "name": f"negative-value-invalid-{slug}",
                        "contract": invalid_contract,
                        "valid": False,
                        "reason_code": "BMCS_PROFILE_VALUE_INVALID",
                        "field": path,
                    },
                    {
                        "name": (
                            f"comparison-unknown-no-snapshot-{slug}" if needs_snapshot(path)
                            else f"comparison-policy-{slug}" if policy_layer(path)
                            else f"comparison-incompatible-{slug}"
                        ),
                        "source": incompatible_contract,
                        "target": valid_contract,
                        # A policy contradiction is reported as a policy finding and leaves the
                        # technical status alone, so the contracts still fit together.
                        "status": (
                            "UNKNOWN" if needs_snapshot(path)
                            else "DIRECT_COMPATIBLE" if policy_layer(path)
                            else "INCOMPATIBLE"
                        ),
                        **({} if needs_snapshot(path) or policy_layer(path) else {"reason_code": contradiction_reason_code(path, definition)}),
                        "field": path,
                    },
                    {
                        # A port that does not declare its consent or data-use terms raises a
                        # governance question, not a technical one, so the status is unchanged and
                        # the absence is reported as a policy finding.
                        "name": f"comparison-policy-missing-{slug}" if policy_layer(path) else f"comparison-unknown-{slug}",
                        "source": missing_contract,
                        "target": valid_contract,
                        "status": "DIRECT_COMPATIBLE" if policy_layer(path) else "UNKNOWN",
                        "field": path,
                    },
                    {
                        "name": f"comparison-policy-missing-target-{slug}" if policy_layer(path) else f"comparison-unknown-target-{slug}",
                        "source": valid_contract,
                        "target": missing_contract,
                        "status": "DIRECT_COMPATIBLE" if policy_layer(path) else "UNKNOWN",
                        "field": path,
                    },
                ]
            )
        declared_unit = get_path(valid_contract, "measurement.unit")
        alternative = convertible_unit(str(declared_unit)) if declared_unit else None
        if alternative:
            source_units = json.loads(json.dumps(valid_contract))
            set_path(source_units, "measurement.unit", alternative)
            cases.append(
                {
                    "name": "comparison-lossless-unit-conversion",
                    "source": source_units,
                    "target": valid_contract,
                    "status": "LOSSLESS_CONVERSION_AVAILABLE",
                }
            )
        # A member requirement is validated per member and never compared, so it keeps its two
        # negative fixtures and none of the three comparison ones.
        cases = [
            case for case in cases
            if not (case["name"].startswith("comparison-") and "[]" in str(case.get("field", "")))
        ]
        write_json(
            root,
            f"fixtures/profiles/{definition['domain']}/{definition['name']}.json",
            {
                "profile_ref": definition["$id"],
                "cases": cases,
            },
        )
    catalogue = {
        "$schema": f"{STANDARD}/schemas/catalogue.schema.json",
        "$id": f"{STANDARD}/catalogue.json",
        "schema_version": "0.1",
        "standard": STANDARD,
        "status": "active",
        "bundle_sha256": None,
        "counts": {"profiles": len(summaries), "fields": len(enriched_fields)},
        "fields": enriched_fields,
        "profiles": summaries,
    }
    write_json(root, "catalogue/catalogue.json", catalogue)

    (root / "examples").mkdir(parents=True, exist_ok=True)
    (root / "examples" / "legacy-model.yaml").write_text(
        'schema_version: "2.0"\nstandard: other\nbiosim:\n  entrypoint: src.model:Model\n  communication_step: 1.0\nio:\n  inputs:\n    - name: expression\n      signal_type: array\n      dtype: float32\n      shape: ["*"]\n  outputs: []\n'
    )
    example_ref = "https://biosimulant.com/standards/model-compatibility/profiles/proteome/protein-sequence/v0.1"
    example_digest = next(entry["sha256"] for entry in summaries if entry["ref"] == example_ref)
    example_concept = profile_concept({"domain": "proteome", "name": "protein-sequence"})
    (root / "examples" / "compatible-model.yaml").write_text(
        f'schema_version: "2.0"\nstandard: other\ncompatibility:\n  standard: https://biosimulant.com/standards/model-compatibility/v0.1\n  profiles:\n    - ref: {example_ref}\n      sha256: {example_digest}\nbiosim:\n  entrypoint: src.model:Model\n  communication_step: 1.0\nio:\n  inputs:\n    - name: protein_sequence\n      signal_type: record\n      contract:\n        profile_refs:\n          - {example_ref}\n        semantic:\n          concept: {example_concept}\n          subject: protein\n        representation:\n          kind: record\n          alphabet: amino-acid\n          encoding: single-letter\n        identifiers:\n          namespace: uniprot\n          namespace_version: release-pinned\n        biological_context:\n          species: NCBITaxon:9606\n  outputs: []\n'
    )

    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "bundle.manifest.json":
            data = path.read_bytes()
            files.append({"path": path.relative_to(root).as_posix(), "sha256": "sha256:" + hashlib.sha256(data).hexdigest(), "size_bytes": len(data)})
    manifest_without_digest = {
        "schema_version": "0.1", "standard": STANDARD, "release": RELEASE,
        "canonicalization": "RFC8785", "files": files,
        "counts": {
            "profiles": len(summaries),
            "fields": len(enriched_fields),
        },
    }
    bundle_digest = digest(manifest_without_digest)
    write_json(root, "bundle.manifest.json", {**manifest_without_digest, "bundle_sha256": bundle_digest})


def compare_trees(left: Path, right: Path) -> list[str]:
    left_files = {p.relative_to(left).as_posix(): p.read_bytes() for p in left.rglob("*") if p.is_file()}
    right_files = {p.relative_to(right).as_posix(): p.read_bytes() for p in right.rglob("*") if p.is_file()}
    return sorted(name for name in set(left_files) | set(right_files) if left_files.get(name) != right_files.get(name))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate spec/v0.1 from the YAML files under source/.")
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
