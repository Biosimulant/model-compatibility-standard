#!/usr/bin/env python3
"""Generate spec/v0.1 from source/catalogue.review.json.

Run with --check to confirm the committed spec/v0.1 is up to date without changing it.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import importlib.util
import json
import sys
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any


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
SOURCE = ROOT / "source" / "catalogue.review.json"

# Reviewed declarations replace the name-substring guessing that decision D9 retired.
QUANTITY_KINDS: dict[str, Any] = {}
MEASUREMENT_DECLARATIONS: dict[str, Any] = {}
STRUCTURE_DECLARATIONS: dict[str, Any] = {}
CONTEXT_DECLARATIONS: dict[str, Any] = {}
ITEM_INDEX: dict[str, Any] = {}
UCUM_TABLE: dict[str, Any] = {}


def load_declarations() -> None:
    global QUANTITY_KINDS, MEASUREMENT_DECLARATIONS, STRUCTURE_DECLARATIONS, CONTEXT_DECLARATIONS, UCUM_TABLE
    QUANTITY_KINDS = json.loads((SOURCE.parent / "quantity-kinds.json").read_text())["kinds"]
    MEASUREMENT_DECLARATIONS = json.loads((SOURCE.parent / "measurement-declarations.json").read_text())["profiles"]
    STRUCTURE_DECLARATIONS = json.loads((SOURCE.parent / "structure-declarations.json").read_text())["profiles"]
    CONTEXT_DECLARATIONS = json.loads((SOURCE.parent / "context-declarations.json").read_text())
    UCUM_TABLE = json.loads((SOURCE.parent / "vendor" / "ucum" / "ucum-table.json").read_text())


def declaration_key(profile: dict[str, Any]) -> str:
    return f"{profile.get('domain')}/{profile.get('name')}"


def measured(profile: dict[str, Any]) -> dict[str, Any]:
    return MEASUREMENT_DECLARATIONS.get(declaration_key(profile), {})


def structured(profile: dict[str, Any]) -> dict[str, Any]:
    return STRUCTURE_DECLARATIONS.get(declaration_key(profile), {})


def example_species(profile: dict[str, Any]) -> str:
    key = declaration_key(profile)
    per_profile = CONTEXT_DECLARATIONS.get("profiles", {}).get(key, {})
    if "species" in per_profile:
        return str(per_profile["species"])
    domain = CONTEXT_DECLARATIONS.get("domains", {}).get(str(profile.get("domain")), {})
    return str(domain.get("species", "NCBITaxon:9606"))
REVIEWS = ROOT / "source" / "reviews"
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
    "representation-equivalent",
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

REPRESENTATION_KINDS = {
    "scalar": ["scalar"],
    "array": ["dense_vector", "sparse_vector", "matrix", "tensor", "array"],
    "record": ["record", "table"],
    "event": ["event"],
    "artifact": ["artifact", "file"],
}

DOMAIN_SUBJECTS = {
    "core": "data_value",
    "genome": "genomic_entity",
    "transcriptome": "biological_sample",
    "epigenome": "biological_sample",
    "proteome": "biological_sample",
    "metabolome": "biological_sample",
    "lipidome-glycome": "biological_sample",
    "chemical": "chemical_entity",
    "pharmacology": "exposed_biological_system",
    "cell": "cell",
    "immunology": "immune_system",
    "microbiology": "microbial_system",
    "virology": "viral_system",
    "developmental": "developing_biological_system",
    "phenotype": "organism_or_sample",
    "imaging": "imaged_subject",
    "spatial": "spatial_entity",
    "physiology": "biological_system",
    "neuroscience": "nervous_system",
    "cardiopulmonary-renal": "cardiopulmonary_or_renal_system",
    "ecology": "ecological_system",
    "evolution": "evolving_population_or_taxon",
    "epidemiology": "population",
    "simulation": "simulation_state_or_configuration",
    "multiomics": "biological_sample_or_subject",
    "clinical": "patient_or_cohort",
}

BOOLEAN_LEAVES = {
    "canonical", "ordered", "sparse", "encrypted", "required", "dynamic",
    "reversible", "directed", "multigraph", "self_loops", "left_normalized",
}
INTEGER_LEAVES = {"byte_size", "cardinality", "size", "passage", "random_seed"}
NUMBER_LEAVES = {
    "min", "max", "minimum", "maximum", "confidence", "confidence_level",
    "variance", "loss_score", "execution_cost", "relative_tolerance",
    "absolute_tolerance", "confluence", "oxygen",
}
ARRAY_LEAVES = {
    "axes", "labels", "qualifiers", "disease", "intervention", "data_use",
    "mapping_refs", "ontology_terms", "quality_flags", "parameters",
    "transformation_chain", "evidence_refs", "validation_results",
}

SET_LIKE_PATHS = [
    "/contract/profile_refs",
    "/contract/semantic/qualifiers",
    "/contract/biological_context/disease",
    "/contract/biological_context/intervention",
    "/contract/security/data_use",
]

REVIEW_SECTIONS = {
    "structure",
    "semantic",
    "representation",
    "dimensions",
    "identifiers",
    "measurement",
    "biological_context",
    "lifecycle",
    "origin",
    "uncertainty",
    "artifact",
    "constraints",
    "security",
}


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


def applicable_review_sections(profile: dict[str, Any]) -> set[str]:
    """Return every section a reviewer must include or explicitly exclude."""

    return set(REVIEW_SECTIONS)


def review_evidence_errors(profile: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    """Check the human evidence needed before a profile can be released as reviewed."""

    errors: list[str] = []
    if evidence.get("profile_id") != profile.get("id"):
        errors.append("profile_id must match the catalogue profile")

    authors = evidence.get("authors")
    if not isinstance(authors, list) or not authors or not all(isinstance(v, str) and v.strip() for v in authors):
        errors.append("authors must contain at least one name")
        authors = []
    scientific_reviewer = evidence.get("scientific_reviewer")
    schema_reviewer = evidence.get("schema_reviewer")
    for key, value in (
        ("scientific_reviewer", scientific_reviewer),
        ("schema_reviewer", schema_reviewer),
        ("domain_owner", evidence.get("domain_owner")),
    ):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{key} must name a person")
    author_names = {str(value).strip().casefold() for value in authors}
    if isinstance(scientific_reviewer, str) and scientific_reviewer.strip().casefold() in author_names:
        errors.append("scientific_reviewer must not be one of the profile authors")
    if isinstance(schema_reviewer, str) and schema_reviewer.strip().casefold() in author_names:
        errors.append("schema_reviewer must not be one of the profile authors")
    if (
        isinstance(scientific_reviewer, str)
        and isinstance(schema_reviewer, str)
        and scientific_reviewer.strip().casefold() == schema_reviewer.strip().casefold()
    ):
        errors.append("scientific_reviewer and schema_reviewer must be different people")

    reviewed_at = evidence.get("reviewed_at")
    try:
        date.fromisoformat(reviewed_at) if isinstance(reviewed_at, str) else None
        if not isinstance(reviewed_at, str):
            raise ValueError
    except ValueError:
        errors.append("reviewed_at must be an ISO date")

    intended_use = evidence.get("intended_use")
    if not isinstance(intended_use, str) or len(intended_use.strip()) < 20:
        errors.append("intended_use must explain the profile's intended use")
    limitations = evidence.get("limitations")
    if not isinstance(limitations, list) or not limitations or not all(
        isinstance(value, str) and len(value.strip()) >= 10 for value in limitations
    ):
        errors.append("limitations must contain at least one clear limitation")

    sources = evidence.get("sources")
    source_ids: set[str] = set()
    if not isinstance(sources, list) or not sources:
        errors.append("sources must contain at least one authoritative source")
    else:
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                errors.append(f"sources[{index}] must be an object")
                continue
            for field in ("id", "title", "kind", "url"):
                value = source.get(field)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"sources[{index}].{field} is required")
            version = source.get("version")
            if not isinstance(version, str) or not version.strip():
                errors.append(f"sources[{index}].version is required")
            source_digest = source.get("sha256")
            if not isinstance(source_digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", source_digest):
                errors.append(f"sources[{index}].sha256 must pin the reviewed source")
            source_id = source.get("id")
            if isinstance(source_id, str):
                if source_id in source_ids:
                    errors.append(f"source id is repeated: {source_id}")
                source_ids.add(source_id)

    decisions = evidence.get("decisions")
    if not isinstance(decisions, dict):
        errors.append("decisions must record each applicable contract section")
        decisions = {}
    missing_sections = sorted(applicable_review_sections(profile) - set(decisions))
    if missing_sections:
        errors.append("decisions are missing: " + ", ".join(missing_sections))
    for section, decision in decisions.items():
        if section not in REVIEW_SECTIONS:
            errors.append(f"unknown review section: {section}")
            continue
        if not isinstance(decision, dict):
            errors.append(f"decisions.{section} must be an object")
            continue
        rationale = decision.get("rationale")
        if not isinstance(rationale, str) or len(rationale.strip()) < 20:
            errors.append(f"decisions.{section}.rationale is too short")
        disposition = decision.get("disposition")
        if disposition not in {"included", "conditional", "excluded"}:
            errors.append(f"decisions.{section}.disposition is invalid")
        field_paths = decision.get("field_paths")
        if not isinstance(field_paths, list) or not all(
            isinstance(value, str) and value.strip() for value in field_paths
        ):
            errors.append(f"decisions.{section}.field_paths must be an array of field paths")
        elif disposition in {"included", "conditional"} and not field_paths:
            errors.append(f"decisions.{section}.field_paths cannot be empty when the section is {disposition}")
        references = decision.get("source_ids")
        if not isinstance(references, list) or not references:
            errors.append(f"decisions.{section}.source_ids must cite at least one source")
        elif any(ref not in source_ids for ref in references):
            errors.append(f"decisions.{section}.source_ids contains an unknown source")

    fixture_review = evidence.get("fixture_review")
    if not isinstance(fixture_review, dict):
        errors.append("fixture_review is required")
    else:
        for group in ("positive", "negative", "invalid", "direct", "incompatible", "unknown"):
            cases = fixture_review.get(group)
            if not isinstance(cases, list) or not cases or not all(
                isinstance(value, str) and value.strip() for value in cases
            ):
                errors.append(f"fixture_review.{group} must name at least one checked fixture")
        transformations = fixture_review.get("transformations")
        if not isinstance(transformations, list) or not all(
            isinstance(value, str) and value.strip() for value in transformations
        ):
            errors.append("fixture_review.transformations must be an array")
        expected_groups = required_fixture_groups(profile)
        for group, expected_names in expected_groups.items():
            declared = fixture_review.get(group)
            if not isinstance(declared, list):
                continue
            missing_names = sorted(set(expected_names) - set(declared))
            if missing_names:
                errors.append(
                    f"fixture_review.{group} is missing required cases: "
                    + ", ".join(missing_names)
                )
    return errors


def load_profile_reviews(profiles: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Load complete review records. Draft notes do not change release state."""

    profile_index = {str(profile["id"]): profile for profile in profiles}
    reviews: dict[str, dict[str, Any]] = {}
    if not REVIEWS.exists():
        return reviews
    for path in sorted(REVIEWS.rglob("*.json")):
        if path.name.endswith(".template.json"):
            continue
        evidence = json.loads(path.read_text())
        profile_id = evidence.get("profile_id") if isinstance(evidence, dict) else None
        if not isinstance(profile_id, str) or profile_id not in profile_index:
            raise SystemExit(f"{path.relative_to(ROOT)}: profile_id is missing or unknown")
        if profile_id in reviews:
            raise SystemExit(f"{path.relative_to(ROOT)}: duplicate review for {profile_id}")
        errors = review_evidence_errors(profile_index[profile_id], evidence)
        if errors:
            raise SystemExit(
                f"{path.relative_to(ROOT)} is not complete:\n- " + "\n- ".join(errors)
            )
        reviews[profile_id] = evidence
    return reviews


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
    if path in {"semantic.concept", "semantic.subject", "identifiers.namespace", "identifiers.namespace_version"}:
        return "equal"
    if family in {"semantic", "identifiers"}:
        return "term-equivalent"
    if path.endswith(".sha256") or path.endswith(".digest"):
        return "digest-equal"
    return "equal"


def item_json_schema(path: str) -> dict[str, Any]:
    """Return a useful base type for a catalogue item.

    Profiles can narrow this schema with ``const`` or ``enum``.  The base schema
    deliberately validates representation, not scientific correctness.
    """

    leaf = path.replace("[]", "").split(".")[-1]
    if path == "accepted_units":
        return {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "minLength": 1}}
    if path == "shape":
        return {"type": "array", "items": {"anyOf": [{"type": "integer", "minimum": 0}, {"const": "*"}]}}
    if path == "schema":
        return {"type": "object"}
    if path == "default":
        return {}
    if path == "constraints[].inputs":
        return {"type": "array", "minItems": 1, "items": {"type": "string", "pattern": "^/"}}
    if leaf in BOOLEAN_LEAVES:
        return {"type": "boolean"}
    if leaf in INTEGER_LEAVES:
        return {"type": "integer", "minimum": 0}
    if leaf in NUMBER_LEAVES:
        return {"type": "number"}
    if leaf in ARRAY_LEAVES:
        if leaf == "axes":
            return {
                "type": "array",
                "minItems": 1,
                "items": {
                    "anyOf": [
                        {"type": "string", "minLength": 1},
                        {
                            "type": "object",
                            "required": ["name"],
                            "properties": {
                                "name": {"type": "string", "minLength": 1},
                                "meaning": {"type": "string", "minLength": 1},
                                "size": {"type": "integer", "minimum": 0},
                                "unit": {"type": "string", "minLength": 1},
                                "ordering": {"type": "string", "minLength": 1},
                                "dynamic": {"type": "boolean"},
                                "labels_ref": {"type": "string", "format": "uri"},
                                "labels_sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
                                "coordinates_ref": {"type": "string", "format": "uri"},
                            },
                            "additionalProperties": False,
                        },
                    ]
                },
            }
        if leaf == "ontology_terms":
            return {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["uri", "ontology", "version"],
                    "properties": {
                        "uri": {"type": "string", "format": "uri"},
                        "ontology": {"type": "string", "minLength": 1},
                        "version": {"type": "string", "minLength": 1},
                        "label": {"type": "string", "minLength": 1},
                        "relation": {"type": "string", "minLength": 1},
                    },
                    "additionalProperties": False,
                },
            }
        if leaf == "mapping_refs":
            return {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["ref", "sha256", "source_namespace", "target_namespace", "release"],
                    "properties": {
                        "ref": {"type": "string", "format": "uri"},
                        "sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
                        "source_namespace": {"type": "string", "minLength": 1},
                        "target_namespace": {"type": "string", "minLength": 1},
                        "release": {"type": "string", "minLength": 1},
                        "coverage": {"type": "number", "minimum": 0, "maximum": 1},
                        "cardinality": {"type": "string", "minLength": 1},
                        "license": {"type": "string", "minLength": 1},
                    },
                    "additionalProperties": False,
                },
            }
        if leaf in {"disease", "intervention"}:
            return {
                "type": "array",
                "minItems": 1,
                "items": {"anyOf": [{"type": "string", "minLength": 1}, {"type": "object"}]},
            }
        if leaf in {"qualifiers", "data_use", "quality_flags", "evidence_refs", "validation_results"}:
            return {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "minLength": 1}}
        return {"type": "array", "minItems": 1}
    if leaf in {"sha256", "digest", "schema_sha256", "labels_sha256", "source_sha256", "contract_sha256"}:
        return {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}
    if leaf.endswith("_ref") or leaf in {"ref", "url", "uri"}:
        return {"type": "string", "format": "uri"}
    if leaf == "species":
        return {
            "type": "string",
            "anyOf": [
                {"const": "any"},
                {"pattern": "^NCBITaxon:[1-9][0-9]*$"},
            ],
        }
    if leaf == "taxonomy_namespace":
        # The registry the taxon labels come from, such as ncbitaxon or gtdb.
        return {"type": "string", "pattern": "^[a-z][a-z0-9.\\-]*$", "maxLength": 64}
    if leaf == "implicit_entry":
        # What an entry absent from a sparse encoding means. Re-encoding dense as sparse is lossless
        # only when both sides agree on this: an unobserved value is not an observed zero (D6).
        return {"enum": ["observed_zero", "unobserved", "not_applicable"]}
    if leaf == "sparsity":
        return {"enum": ["dense", "sparse"]}
    if leaf == "scale":
        # Stevens' level, separated from the value domain and from any transform (decision D8).
        return {"enum": ["nominal", "ordinal", "interval", "ratio", "proportion", "probability", "count"]}
    if leaf == "transform":
        return {"enum": ["identity", "log2", "log10", "ln", "logit"]}
    if leaf in {"severity"}:
        return {"enum": ["info", "warning", "error"]}
    if leaf in {"classification"}:
        return {"enum": ["public", "internal", "confidential", "restricted"]}
    if leaf in {"unit", "time_unit", "accepted_units", "emitted_unit"}:
        return {"type": "string", "minLength": 1, "maxLength": 128}
    if leaf in {"actual_context", "provenance", "uncertainty", "value", "expected", "inputs", "schema"}:
        return {"type": ["string", "number", "integer", "boolean", "array", "object"]}
    return {"type": "string", "minLength": 1, "maxLength": 4096}


def profile_concept(profile: dict[str, Any]) -> str:
    """A term identifier that does not change when the profile version does (decision D3)."""

    return f"{STANDARD.rsplit('/', 1)[0]}/terms/{profile.get('domain')}/{profile.get('name')}"


def quantity_kind_id(kind: str) -> str:
    return f"{STANDARD.rsplit('/', 1)[0]}/quantity-kinds/{kind}"


def allowed_representation_kinds(profile: dict[str, Any]) -> list[str]:
    narrowed = structured(profile).get("kinds")
    if narrowed:
        return list(narrowed)
    values: list[str] = []
    for signal_type in profile.get("applies_to", []):
        values.extend(REPRESENTATION_KINDS.get(str(signal_type), []))
    values = list(dict.fromkeys(values)) or ["record"]
    # A profile whose reviewed structure declares at least one axis is indexed, so it is not a
    # scalar (decision D6). Narrowing beyond this needs a per-profile judgement that no reviewed
    # declaration carries yet, and guessing it from the profile name is what D9 abolished.
    axes = structured(profile).get("axes")
    if isinstance(axes, list) and axes and "scalar" in values:
        values = [value for value in values if value != "scalar"]
    return values


# These operators need a pinned snapshot to decide anything. Without one the engine answers
# UNKNOWN, so a differing value is absent evidence rather than a contradiction (decisions D3, D7).
SNAPSHOT_OPERATORS = {"term-equivalent", "term-subsumes", "mapping-total", "mapping-bijective"}


def contradiction_reason_code(path: str, definition: dict[str, Any]) -> str:
    """The code the engine actually reports for this contradiction.

    Where the profile fixes a quantity kind, a unit of another quantity is caught by the kind check
    before the unit rule is reached, and that check reports its own code (decision D1).
    """

    if path == "measurement.unit" and get_path(definition.get("fixed", {}), "measurement.quantity"):
        return "BMCS_UNIT_DIMENSION_MISMATCH"
    return reason_code_for(path)


def needs_snapshot(path: str) -> bool:
    return item_operator(path, path.split(".")[0]) in SNAPSHOT_OPERATORS


def reason_code_for(path: str) -> str:
    normalized = path.replace("[]", "").replace(".", "_").replace("-", "_").upper()
    return f"BMCS_{normalized}_MISMATCH"


def profile_fixed(profile: dict[str, Any]) -> dict[str, Any]:
    fixed: dict[str, Any] = {}
    if "semantic.concept" in profile.get("required_items", []):
        set_path(fixed, "semantic.concept", profile_concept(profile))
    kind = measured(profile).get("kind")
    if "measurement.quantity" in profile.get("required_items", []) and kind and kind != "port-declared":
        set_path(fixed, "measurement.quantity", quantity_kind_id(str(kind)))
    return fixed


def profile_allowed(profile: dict[str, Any]) -> dict[str, Any]:
    allowed: dict[str, Any] = {}
    if "representation.kind" in profile.get("required_items", []):
        set_path(allowed, "representation.kind", allowed_representation_kinds(profile))
    return allowed


def get_path(document: dict[str, Any], path: str) -> Any:
    current: Any = document
    for part in path.replace("[]", "").split("."):
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
    return item_json_schema(path)


def measurement_unit(profile: dict[str, Any]) -> str:
    """The reviewed UCUM unit for this profile (decision D9)."""

    declared = measured(profile).get("unit")
    return str(declared) if declared else "1"


def axis_names(profile: dict[str, Any]) -> list[str]:
    """The reviewed axes for this profile, in order (decision D9)."""

    axes = structured(profile).get("axes")
    if axes in (None, "port-declared"):
        return ["axis"]
    return [str(axis["name"]) for axis in axes]


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
        return axis_names(profile)
    if leaf in {"axes", "labels", "qualifiers", "disease", "intervention", "data_use"}:
        return [f"example-{leaf}"]
    if leaf in BOOLEAN_LEAVES:
        return True
    derived = example_from_schema((ITEM_INDEX.get(path) or {}).get("json_schema"), leaf)
    if derived is not None:
        return derived
    if leaf in {"min", "max", "minimum", "maximum", "confidence", "variance", "byte_size"}:
        return 1
    if leaf == "mapping_refs":
        # An array of pinned mappings, not a label (decision D7). Each entry is built from the
        # catalogue's own sub-item definitions, so the example cannot drift from their schemas.
        prefix = "identifiers.mapping_refs[]."
        entry = {sub[len(prefix):]: example_value(sub) for sub in ITEM_INDEX if sub.startswith(prefix)}
        return [entry] if entry else []
    if leaf.endswith("sha256") or leaf in {"digest", "structure_hash"}:
        # A digest item has a pattern to satisfy; "example-sha256" is not a digest.
        return "sha256:" + "0" * 64
    if leaf == "species":
        return example_species(profile or {})
    if leaf == "taxonomy_namespace":
        return "ncbitaxon"
    if leaf == "taxonomy_version":
        return "2026-01-01"
    if leaf == "unit":
        return measurement_unit(profile or {})
    if leaf == "kind":
        return allowed_representation_kinds(profile or {})[0]
    if leaf == "concept" and profile is not None:
        return profile_concept(profile)
    if leaf == "subject" and profile is not None:
        return DOMAIN_SUBJECTS.get(str(profile.get("domain")), "biological_entity")
    if leaf == "quantity" and profile is not None:
        kind = measured(profile).get("kind", "port-declared")
        return quantity_kind_id(str(kind))
    if leaf == "scale":
        return str(measured(profile or {}).get("scale", "ratio"))
    if leaf == "transform":
        return str(measured(profile or {}).get("transform", "identity"))
    if leaf == "ordering":
        return "explicit"
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
    parts = [part for part in path.replace("[]", "").split(".") if part]
    current: Any = document
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    if isinstance(current, dict) and parts:
        current.pop(parts[-1], None)


COMPARED_WHEN_BOTH_DECLARE = [
    # Decision D2: a field that changes how a number or a feature is read must be compared
    # whenever both ports declare it, even where the profile does not require it.
    "measurement.unit", "measurement.scale", "measurement.transform", "measurement.quantity",
    "measurement.normalization", "measurement.baseline", "measurement.aggregation",
    "identifiers.namespace", "identifiers.namespace_version",
    "representation.ordering", "representation.feature_space", "representation.reference_assembly",
    "representation.coordinate_system", "dimensions.axes", "lifecycle.time_unit",
    "lifecycle.temporal_meaning", "origin.type", "biological_context.compartment",
]

# Decision D4: an uncontrolled free-text subject compares unequal for synonyms and equal for
# homonyms, so it stops being a required, compared field until it is term-bound.
RETIRED_REQUIRED_ITEMS = {"semantic.subject"}


def effective_required_items(profile: dict[str, Any]) -> list[str]:
    required = [path for path in profile.get("required_items", []) if path not in RETIRED_REQUIRED_ITEMS]
    declaration, structure = measured(profile), structured(profile)
    if declaration.get("drop_measurement"):
        required = [path for path in required if not path.startswith("measurement.")]
    if "axes" in structure and structure.get("axes") is None:
        required = [path for path in required if path not in {"dimensions.axes", "representation.ordering"}]
    for extra in list(declaration.get("requires", [])) + list(structure.get("requires", [])):
        if extra not in required:
            required.append(extra)
    return required


def required_fixture_groups(profile: dict[str, Any]) -> dict[str, list[str]]:
    slugs = [fixture_slug(path) for path in effective_required_items(profile)]
    groups = {
        "positive": ["positive"],
        "negative": [f"negative-required-missing-{slug}" for slug in slugs],
        "invalid": [f"negative-value-invalid-{slug}" for slug in slugs],
        "direct": ["comparison-direct"],
        "incompatible": [f"comparison-incompatible-{fixture_slug(path)}" for path in effective_required_items(profile) if not needs_snapshot(path)],
        "unknown": [f"comparison-unknown-{slug}" for slug in slugs],
        "transformations": [],
    }
    groups["unknown"].extend(f"comparison-unknown-target-{slug}" for slug in slugs)
    groups["unknown"].extend(
        f"comparison-unknown-no-snapshot-{fixture_slug(path)}"
        for path in effective_required_items(profile)
        if needs_snapshot(path)
    )
    unit = measurement_unit(profile) if "measurement.unit" in effective_required_items(profile) else None
    if unit and convertible_unit(unit):
        groups["transformations"].append("comparison-lossless-unit-conversion")
    return groups


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


def review_questions(profile: dict[str, Any]) -> list[str]:
    required = set(profile.get("required_items", []))
    questions = [
        f"Does the proposed concept identify {profile['label']} narrowly enough to prevent a different scientific quantity from matching?",
        "Are the allowed representations complete, and can any two allowed representations connect without an explicit adapter?",
        "Which authoritative standards, ontologies, databases or primary publications support each required field and comparison rule?",
        "Which missing value must return UNKNOWN, and which known contradiction must return INCOMPATIBLE?",
    ]
    if "measurement.quantity" in required:
        questions.append("Are the quantity, unit, scale, normalization, baseline and endpoint definitions sufficient for this measurement?")
    else:
        questions.append("Should quantity, unit, scale, normalization, baseline or endpoint be required for this profile?")
    if "identifiers.namespace" in required:
        questions.append("Which identifier namespaces, releases, canonicalization rules and mapping-loss rules are permitted?")
    else:
        questions.append("Does this profile need a versioned identifier namespace or an ordered feature universe?")
    if "dimensions.axes" in required:
        questions.append("Are axis names, order, labels, coordinates and dynamic-size rules fully specified?")
    elif any(kind in profile.get("applies_to", []) for kind in ("array", "artifact")):
        questions.append("Should axes, labels, feature order, coordinates or artifact schema be required for non-scalar values?")
    if profile.get("domain") not in {"core", "simulation", "chemical"}:
        questions.append("Which species, tissue, cell type, disease, intervention, assay, cohort or compartment fields are required or conditional?")
    if "event" in profile.get("applies_to", []) or any(token in profile.get("name", "") for token in ("time", "event", "trajectory", "rate", "stage")):
        questions.append("Are event/state meaning, observation time, sampling, window, freshness and interpolation rules complete?")
    questions.append("What uses and scientific claims must this profile explicitly exclude?")
    return questions


def gating_pointer(path: str) -> str:
    """Where the gating rule for a required field points.

    Almost always the field itself. representation.kind is the exception: conditional equivalence
    needs to see the sibling fields that would make a re-encoding lossless, so its rule points at the
    representation object (decision D6).
    """

    return "/contract/representation" if path == "representation.kind" else item_pointer(path)


def internal_quality_errors(profile: dict[str, Any], definition: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    requirements = definition.get("requirements", [])
    paths = [item.get("path") for item in requirements]
    if len(paths) != len(set(paths)):
        errors.append("requirements contain duplicate paths")
    concept = get_path(definition.get("fixed", {}), "semantic.concept")
    if not concept:
        errors.append("semantic.concept is not fixed to this profile")
    elif isinstance(concept, str) and "/v0." in concept:
        # Decision D3: an IRI carrying /v0.1 would report every v0.2 port as incompatible even when
        # the meaning is unchanged, so profile identity must not be baked into the term.
        errors.append("semantic.concept embeds a profile version")
    kinds = get_path(definition.get("allowed", {}), "representation.kind")
    if not isinstance(kinds, list) or not kinds:
        errors.append("representation.kind has no allowed values")
    required_paths = [item["path"] for item in requirements if item.get("level") == "required"]
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
    if not definition.get("review_questions"):
        errors.append("external review questions are missing")
    return errors


def contract_schema(items: list[dict[str, Any]]) -> dict[str, Any]:
    families: dict[str, dict[str, dict[str, Any]]] = {}
    for item in items:
        path = str(item["path"])
        if path.startswith(("compatibility.", "profiles[].")) or "." not in path:
            continue
        family, rest = path.replace("[]", "").split(".", 1)
        if family in {"contract", "io", "accepted_profiles"}:
            continue
        key = rest.split(".", 1)[0]
        # Prefer the schema for the direct family member. A deeper catalogue
        # item documents part of that member rather than replacing its shape.
        candidate = item.get("json_schema", {}) if "." not in rest else {"type": "object"}
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


def schemas(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
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
            "technical_pre_review", "review_questions",
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
                    "schema_reviewer": {"type": ["string", "null"]},
                    "domain_owner": {"type": ["string", "null"]},
                    "authors": {"type": "array", "items": {"type": "string"}},
                    "reviewed_at": {"type": ["string", "null"], "format": "date"},
                    "sources": {"type": "array", "items": {"type": "object"}},
                    "intended_use": {"type": ["string", "null"]},
                    "limitations": {"type": "array", "items": {"type": "string"}},
                    "decisions": {"type": "object"},
                    "fixture_review": {"type": "object"},
                },
                "additionalProperties": False,
            },
            "release_eligible": {"type": "boolean"},
            "technical_pre_review": {
                "type": "object",
                "required": ["status", "method_version", "checks", "scientific_signoff_required"],
                "properties": {
                    "status": {"enum": ["ready-for-external-review", "needs-work"]},
                    "method_version": {"const": "1.0"},
                    "checks": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string"}},
                    "scientific_signoff_required": {"const": True},
                },
                "additionalProperties": False,
            },
            "review_questions": {
                "type": "array",
                "minItems": 5,
                "uniqueItems": True,
                "items": {"type": "string", "minLength": 20},
            },
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
        ["schema_version", "standard", "bundle_sha256", "technical_status", "nodes", "edges", "reports", "policy", "approvals", "digest"],
        {
            "schema_version": {"const": "0.1"}, "standard": {"const": STANDARD},
            "bundle_sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            # The status the chain carries. reports[] holds the terminal comparison, which is EXACT
            # whenever the last adapter lands exactly on the target, so a reader needs this to tell a
            # lossy chain from an inference one (decision D11).
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
            "counts": {"type": "object"},
            "review_counts": {"type": "object"},
            "technical_pre_review_counts": {"type": "object"},
            "item_definitions": {"type": "array", "items": {"type": "object"}},
            "item_packs": {"type": "array", "items": {"type": "object"}},
            "profiles": {"type": "array", "items": {"type": "object"}},
        },
    )
    review_packet = simple(
        "profile-review-packet", "Profile External Review Packet",
        [
            "profile_id", "profile_ref", "profile_sha256", "label", "domain", "stage",
            "technical_pre_review", "proposed_fixed_values", "proposed_allowed_values",
            "proposed_requirements", "proposed_comparison_rules", "candidate_recommended_items",
            "questions_for_reviewers", "internal_quality_errors", "required_external_approvals",
            "fixture_names", "fixture_groups", "non_claim",
        ],
        {
            "profile_id": {"type": "string", "pattern": "^[a-z0-9-]+/[a-z0-9-]+@0\\.1$"},
            "profile_ref": {"type": "string", "format": "uri"},
            "profile_sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
            "label": {"type": "string", "minLength": 1},
            "domain": {"type": "string", "minLength": 1},
            "stage": {"type": "string", "minLength": 1},
            "technical_pre_review": {"type": "object"},
            "proposed_fixed_values": {"type": "object"},
            "proposed_allowed_values": {"type": "object"},
            "proposed_requirements": {"type": "array", "minItems": 1, "items": {"type": "object"}},
            "proposed_comparison_rules": {"type": "array", "minItems": 1, "items": {"$ref": "rule.schema.json"}},
            "candidate_recommended_items": {"type": "array", "uniqueItems": True, "items": {"type": "string"}},
            "questions_for_reviewers": {"type": "array", "minItems": 5, "uniqueItems": True, "items": {"type": "string", "minLength": 20}},
            "internal_quality_errors": {"type": "array", "items": {"type": "string"}},
            "required_external_approvals": {"type": "array", "minItems": 3, "uniqueItems": True, "items": {"type": "string"}},
            "fixture_names": {"type": "array", "minItems": 6, "uniqueItems": True, "items": {"type": "string"}},
            "fixture_groups": {"type": "object"},
            "non_claim": {"type": "string", "minLength": 20},
        },
    )
    internal_validation = simple(
        "internal-validation", "Profile Internal Validation Summary",
        ["schema_version", "standard", "method_version", "scope", "counts", "profiles"],
        {
            "schema_version": {"const": "0.1"},
            "standard": {"const": STANDARD},
            "method_version": {"const": "1.0"},
            "scope": {"type": "string", "minLength": 20},
            "counts": {"type": "object"},
            "profiles": {"type": "array", "minItems": 650, "maxItems": 650, "items": {"type": "object"}},
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
        "profile-review-packet": review_packet,
        "internal-validation": internal_validation,
    }


def build(root: Path) -> None:
    load_declarations()
    source = json.loads(SOURCE.read_text())
    profiles = source["profiles"]
    items = source["item_definitions"]
    packs = source["item_packs"]
    if (len(profiles), len(items), len(packs)) != (650, 268, 30):
        raise SystemExit(
            "source/catalogue.review.json must have 650 profiles, 268 items and 30 packs; "
            f"found {len(profiles)}, {len(items)} and {len(packs)}"
        )
    reviews = load_profile_reviews(profiles)
    for profile in profiles:
        if profile.get("review_status") == "reviewed" and profile["id"] not in reviews:
            raise SystemExit(
                f"{profile['id']} is marked reviewed but has no complete file under source/reviews"
            )

    enriched_items: list[dict[str, Any]] = []
    item_index: dict[str, dict[str, Any]] = {}
    for raw in items:
        item = dict(raw)
        item["comparison_operator"] = item_operator(str(item["path"]), str(item["family"]))
        item["missing_behavior"] = "unknown"
        item["json_schema"] = item_json_schema(str(item["path"]))
        item["value_type"] = "JSON value constrained by json_schema"
        item["ordered"] = item_pointer(str(item["path"])) not in SET_LIKE_PATHS
        REASON_CODES.setdefault(
            reason_code_for(str(item["path"])),
            f"The value at {item['path']} is incompatible with the target profile.",
        )
        enriched_items.append(item)
        item_index[str(item["path"])] = item
    ITEM_INDEX.clear()
    ITEM_INDEX.update(item_index)

    definitions: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    review_packets: list[dict[str, Any]] = []
    pack_index = {str(pack["id"]): pack for pack in packs}
    for raw in profiles:
        review_evidence = reviews.get(raw["id"])
        release_eligible = review_evidence is not None
        if review_evidence is None:
            review = {
                "status": raw["review_status"],
                "reviewer": None,
                "schema_reviewer": None,
                "domain_owner": None,
                "authors": [],
                "reviewed_at": None,
                "sources": [],
                "intended_use": None,
                "limitations": [],
                "decisions": {},
                "fixture_review": {},
            }
        else:
            review = {
                "status": "reviewed",
                "reviewer": review_evidence["scientific_reviewer"],
                "schema_reviewer": review_evidence["schema_reviewer"],
                "domain_owner": review_evidence["domain_owner"],
                "authors": review_evidence["authors"],
                "reviewed_at": review_evidence["reviewed_at"],
                "sources": review_evidence["sources"],
                "intended_use": review_evidence["intended_use"],
                "limitations": review_evidence["limitations"],
                "decisions": review_evidence["decisions"],
                "fixture_review": review_evidence["fixture_review"],
            }
        raw = dict(raw, required_items=effective_required_items(raw))
        requirements = [
            {"path": path, "level": "required", "schema": requirement_schema(raw, path)}
            for path in raw["required_items"]
        ]
        required_paths = set(raw["required_items"])
        candidate_paths: set[str] = set()
        for pack_name in raw["required_item_packs"]:
            candidate_paths.update(str(path) for path in pack_index[pack_name]["items"])
        candidate_recommended_items = [
            path
            for path in sorted(candidate_paths - required_paths)
            if path in item_index and item_index[path].get("family") not in {"existing-io", "envelope"}
        ]
        # Decision D10. The profile document carried one level only: everything was "required" and
        # the packet listed the rest as candidates a reader had to go and find. An item carried by a
        # pack the profile adopts, but not required by it, is recommended for that profile. Pack
        # membership is authored, reviewed data, so this needs no per-profile judgement. Neither
        # validation nor comparison gates on a recommended item: both skip any level but "required".
        # Decision D10. Emitting these as level "recommended" requirements was built and withdrawn:
        # the review packet already publishes the same list as candidate_recommended_items, which its
        # schema requires and the pre-review tooling reads, so the profile document was carrying a
        # second copy of it for +9.2 MiB, 29.7% of the bundle, that no engine reads. The level
        # vocabulary still has only one producer, and giving it a real one needs the profile classes
        # the pilot exists to inform.
        rules = [
            {
                # representation.kind is compared by conditional equivalence against the whole
                # representation object, so the operator can see whether the fields that would make
                # a re-encoding lossless are declared (decision D6).
                "source": gating_pointer(path),
                "target": gating_pointer(path),
                "operator": "representation-equivalent" if path == "representation.kind" else item_index.get(path, {}).get("comparison_operator", "equal"),
                "missing": "unknown",
                "severity": "error",
                "reason_code": reason_code_for(path),
            }
            for path in raw["required_items"]
        ]
        for path in COMPARED_WHEN_BOTH_DECLARE:
            if path in required_paths or path not in item_index:
                continue
            rules.append(
                {
                    "source": item_pointer(path),
                    "target": item_pointer(path),
                    "operator": item_index[path].get("comparison_operator", "equal"),
                    "missing": "ignore",
                    "severity": "error",
                    "reason_code": reason_code_for(path),
                }
            )
        questions = review_questions(raw)
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
            "review": review,
            "release_eligible": release_eligible,
            "technical_pre_review": {
                "status": "ready-for-external-review",
                "method_version": "1.0",
                "checks": [
                    "profile-definition-schema",
                    "typed-required-values",
                    "profile-specific-concept",
                    "representation-applicability",
                    "stable-field-level-reason-codes",
                    "positive-fixture",
                    "missing-required-fixture",
                    "invalid-value-fixture",
                    "direct-compatible-fixture",
                    "incompatible-fixture",
                    "unknown-fixture",
                    "python-typescript-parity",
                ],
                "scientific_signoff_required": True,
            },
            "review_questions": questions,
            "applies_to": raw["applies_to"],
            "extends": [],
            "fixed": profile_fixed(raw),
            "allowed": profile_allowed(raw),
            "item_packs": raw["required_item_packs"],
            "requirements": requirements,
            "comparison_rules": rules,
            "transformation_policy": {"lossless": "allow", "lossy": "approval", "inference": "approval"},
            "compatibility_notes": raw["compatibility_notes"],
            "scientific_claim": raw["scientific_claim"],
        }
        quality_errors = internal_quality_errors(raw, definition)
        if quality_errors:
            definition["technical_pre_review"]["status"] = "needs-work"
        definition_digest = digest(definition)
        definitions.append(definition)
        review_packets.append(
            {
                "profile_id": raw["id"],
                "profile_ref": raw["ref"],
                "profile_sha256": definition_digest,
                "label": raw["label"],
                "domain": raw["domain"],
                "stage": raw["stage"],
                "technical_pre_review": definition["technical_pre_review"],
                "proposed_fixed_values": definition["fixed"],
                "proposed_allowed_values": definition["allowed"],
                "proposed_requirements": requirements,
                "candidate_recommended_items": candidate_recommended_items,
                "proposed_comparison_rules": rules,
                "questions_for_reviewers": questions,
                "internal_quality_errors": quality_errors,
                "required_external_approvals": [
                    "named domain-qualified scientific reviewer",
                    "different named schema and compatibility reviewer",
                    "domain owner",
                ],
                "non_claim": "Technical pre-review does not establish scientific validity, clinical safety or regulatory suitability.",
            }
        )
        summaries.append(
            {
                "id": raw["id"], "ref": raw["ref"], "sha256": definition_digest,
                "version": raw["version"], "domain": raw["domain"], "domain_label": raw["domain_label"],
                "name": raw["name"], "label": raw["label"], "description": raw["description"],
                "stage": raw["stage"], "review_status": review["status"],
                "release_eligible": release_eligible, "applies_to": raw["applies_to"],
                "technical_pre_review": definition["technical_pre_review"]["status"],
                "required_item_count": len(raw["required_items"]),
                "recommended_item_count": len(candidate_recommended_items),
                "item_packs": raw["required_item_packs"],
            }
        )

    for name, schema in schemas(enriched_items).items():
        write_json(root, f"schemas/{name}.schema.json", schema)

    write_json(root, "rules/operators.json", {"standard": STANDARD, "operators": OPERATORS})
    write_json(root, "rules/reason-codes.json", {"standard": STANDARD, "reason_codes": REASON_CODES})
    write_json(root, "rules/statuses.json", {"standard": STANDARD, "technical": STATUSES, "policy": POLICY_DECISIONS, "quality": QUALITY_DECISIONS})
    write_json(root, "rules/normalization.json", {"standard": STANDARD, "canonicalization": "RFC8785", "set_like_paths": SET_LIKE_PATHS})
    write_json(root, "rules/units.json", {"standard": STANDARD, **UCUM_TABLE})
    write_json(root, "rules/quantity-kinds.json", {"standard": STANDARD, "id_prefix": f"{STANDARD.rsplit('/', 1)[0]}/quantity-kinds/", "kinds": QUANTITY_KINDS})
    write_json(root, "catalogue/items.json", {"schema_version": "0.1", "standard": STANDARD, "items": enriched_items})
    write_json(root, "catalogue/item-packs.json", {"schema_version": "0.1", "standard": STANDARD, "item_packs": packs})
    # Decision D3. The concept IRI is minted outside the versioned profile document, so it needs a
    # registry of its own: a term carries a label, a definition and a version that does not move when
    # the profile version does. Label and definition come from the profile's own reviewed text.
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
                "external_terms is empty until a reviewer decides, per profile, whether a maintained "
                "external term exists at the right granularity."
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

    source_profiles_by_ref = {profile["ref"]: profile for profile in profiles}
    packets_by_ref = {packet["profile_ref"]: packet for packet in review_packets}
    for definition in definitions:
        source_profile = source_profiles_by_ref[definition["$id"]]
        write_json(root, f"profiles/{definition['domain']}/{definition['name']}/v0.1.json", definition)
        valid_contract: dict[str, Any] = {}
        for requirement in definition["requirements"]:
            if requirement["level"] != "required":
                continue
            set_path(valid_contract, requirement["path"], example_value(requirement["path"], source_profile))
        direct_contract = json.loads(json.dumps(valid_contract))
        if "origin.type" in {item["path"] for item in definition["requirements"] if item["level"] == "required"}:
            set_path(direct_contract, "origin.generated_at", "2026-01-01T00:00:00Z")
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
                        "name": f"comparison-unknown-no-snapshot-{slug}" if needs_snapshot(path) else f"comparison-incompatible-{slug}",
                        "source": incompatible_contract,
                        "target": valid_contract,
                        "status": "UNKNOWN" if needs_snapshot(path) else "INCOMPATIBLE",
                        **({} if needs_snapshot(path) else {"reason_code": contradiction_reason_code(path, definition)}),
                        "field": path,
                    },
                    {
                        "name": f"comparison-unknown-{slug}",
                        "source": missing_contract,
                        "target": valid_contract,
                        "status": "UNKNOWN",
                        "field": path,
                    },
                    {
                        "name": f"comparison-unknown-target-{slug}",
                        "source": valid_contract,
                        "target": missing_contract,
                        "status": "UNKNOWN",
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
        write_json(
            root,
            f"fixtures/profiles/{definition['domain']}/{definition['name']}.json",
            {
                "profile_ref": definition["$id"],
                "cases": cases,
            },
        )
        packet = packets_by_ref[definition["$id"]]
        packet["fixture_names"] = [case["name"] for case in cases]
        packet["fixture_groups"] = required_fixture_groups(source_profile)
        write_json(
            root,
            f"review-packets/{definition['domain']}/{definition['name']}.json",
            packet,
        )

    reviewed_count = sum(1 for summary in summaries if summary["release_eligible"])
    ready_for_external_review = sum(
        1 for definition in definitions
        if definition["technical_pre_review"]["status"] == "ready-for-external-review"
    )
    write_json(
        root,
        "catalogue/internal-validation.json",
        {
            "schema_version": "0.1",
            "standard": STANDARD,
            "method_version": "1.0",
            "scope": "Technical and schema pre-review only; independent scientific approval remains required.",
            "counts": {
                "profiles": len(definitions),
                "ready_for_external_review": ready_for_external_review,
                "needs_work": len(definitions) - ready_for_external_review,
                "independently_scientifically_reviewed": reviewed_count,
            },
            "profiles": [
                {
                    "profile_id": definition["profile_id"],
                    "profile_ref": definition["$id"],
                    "status": definition["technical_pre_review"]["status"],
                    "scientific_signoff_required": True,
                }
                for definition in definitions
            ],
        },
    )

    ga_ready = reviewed_count == len(summaries)
    catalogue = {
        "$schema": f"{STANDARD}/schemas/catalogue.schema.json",
        "$id": f"{STANDARD}/catalogue.json",
        "schema_version": "0.1",
        "standard": STANDARD,
        "status": "release-candidate" if ga_ready else "implementation-draft",
        "bundle_sha256": None,
        "counts": {"profiles": len(summaries), "item_definitions": len(enriched_items), "item_packs": len(packs)},
        "review_counts": {
            "reviewed": reviewed_count,
            "remaining": len(summaries) - reviewed_count,
        },
        "technical_pre_review_counts": {
            "ready_for_external_review": ready_for_external_review,
            "needs_work": len(summaries) - ready_for_external_review,
        },
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
    example_concept = profile_concept({"domain": "transcriptome", "name": "gene-expression-counts"})
    (root / "examples" / "compatible-model.yaml").write_text(
        f'schema_version: "2.0"\nstandard: other\ncompatibility:\n  standard: https://biosimulant.com/standards/model-compatibility/v0.1\n  profiles:\n    - ref: {example_ref}\n      sha256: {example_digest}\nbiosim:\n  entrypoint: src.model:Model\n  communication_step: 1.0\nio:\n  inputs:\n    - name: expression\n      signal_type: array\n      dtype: float32\n      shape: ["*"]\n      contract:\n        profile_refs:\n          - {example_ref}\n        semantic:\n          concept: {example_concept}\n        representation:\n          kind: dense_vector\n        identifiers:\n          namespace: ensembl-gene\n          namespace_version: release-pinned\n        biological_context:\n          species: NCBITaxon:9606\n  outputs: []\n'
    )

    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "bundle.manifest.json":
            data = path.read_bytes()
            files.append({"path": path.relative_to(root).as_posix(), "sha256": "sha256:" + hashlib.sha256(data).hexdigest(), "size_bytes": len(data)})
    remaining_reviews = len(summaries) - reviewed_count
    manifest_without_digest = {
        "schema_version": "0.1", "standard": STANDARD, "release": "0.1.0-alpha.5",
        "canonicalization": "RFC8785", "files": files,
        "counts": {"profiles": 650, "item_definitions": 266, "item_packs": 30},
        "ga_ready": ga_ready,
        "ga_blockers": [] if ga_ready else [
            f"{remaining_reviews} profiles still need complete, independent scientific and schema review evidence."
        ],
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
