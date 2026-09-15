"""Check contracts and manifests against the bundled JSON Schemas and profile requirements."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from copy import deepcopy
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .bundle import Bundle, get_bundle
from .units import UnitError, parse_unit
from .pointers import MISSING, get_dotted
from .security import ResourceLimitError, ResourceLimits, ensure_json_limits


@dataclass(frozen=True)
class ValidationFinding:
    reason_code: str
    message: str
    path: str = ""
    severity: str = "error"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _registry(bundle: Bundle) -> Registry:
    registry = Registry()
    for identifier, schema in bundle.schema_index.items():
        if identifier.startswith("https://"):
            registry = registry.with_resource(identifier, Resource.from_contents(schema))
    return registry


def _schema_errors(instance: Any, schema_name: str, bundle: Bundle) -> list[ValidationFinding]:
    try:
        ensure_json_limits(instance, limits=bundle.limits)
    except ResourceLimitError as error:
        return [ValidationFinding("BMCS_RESOURCE_LIMIT_EXCEEDED", str(error))]
    schema = bundle.schema_index[schema_name]
    validator = Draft202012Validator(schema, registry=_registry(bundle))
    findings = []
    for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.path)):
        path = "/" + "/".join(str(part) for part in error.absolute_path)
        findings.append(ValidationFinding("BMCS_SCHEMA_INVALID", error.message, path))
    return findings


def validate_object(
    instance: Any,
    schema_name: str,
    *,
    bundle: Bundle | None = None,
    limits: ResourceLimits | None = None,
) -> list[ValidationFinding]:
    """Validate an object against a bundled schema, e.g. 'compatibility-report.schema.json'."""

    active = bundle or get_bundle()
    if limits is not None:
        active = Bundle(active.root, limits=limits)
    normalized_name = schema_name if schema_name.endswith(".json") else f"{schema_name}.json"
    if normalized_name not in active.schema_index:
        raise KeyError(f"Unknown standard schema: {schema_name}")
    return _schema_errors(instance, normalized_name, active)


def validate_contract(
    contract: dict[str, Any],
    profile_refs: Iterable[str] = (),
    *,
    bundle: Bundle | None = None,
    limits: ResourceLimits | None = None,
) -> list[ValidationFinding]:
    active = bundle or get_bundle()
    if limits is not None:
        active = Bundle(active.root, limits=limits)
    findings = _schema_errors(contract, "port-contract.schema.json", active)
    if any(item.reason_code == "BMCS_RESOURCE_LIMIT_EXCEEDED" for item in findings):
        return findings
    refs = list(profile_refs)
    if len(refs) > active.limits.max_profile_refs:
        findings.append(
            ValidationFinding(
                "BMCS_RESOURCE_LIMIT_EXCEEDED",
                f"Contract references more than {active.limits.max_profile_refs} profiles.",
                "/profile_refs",
            )
        )
        return findings
    for ref in refs:
        try:
            profile = active.profile(ref)
        except KeyError:
            findings.append(ValidationFinding("BMCS_PROFILE_UNRESOLVED", f"Profile not found in the installed bundle: {ref}", "/profile_refs"))
            continue
        requirements = profile.get("requirements", [])
        rules = profile.get("comparison_rules", [])
        if len(rules) > active.limits.max_rules:
            findings.append(
                ValidationFinding(
                    "BMCS_RESOURCE_LIMIT_EXCEEDED",
                    f"Profile {ref} contains more than {active.limits.max_rules} comparison rules.",
                    "/profile_refs",
                )
            )
            continue
        for requirement in requirements:
            if requirement.get("level") != "required":
                continue
            if "[]" in requirement["path"]:
                findings.extend(_array_member_findings(ref, requirement, contract))
                continue
            value = get_dotted(contract, requirement["path"])
            if value is MISSING or value is None:
                findings.append(
                    ValidationFinding(
                        "BMCS_REQUIRED_MISSING",
                        f"Profile {ref} requires '{requirement['path']}', but it is missing.",
                        "/" + requirement["path"].replace(".", "/"),
                    )
                )
                continue
            for error in Draft202012Validator(requirement["schema"], format_checker=FormatChecker()).iter_errors(value):
                findings.append(
                    ValidationFinding(
                        "BMCS_PROFILE_VALUE_INVALID",
                        f"{requirement['path']}: {error.message}",
                        "/" + requirement["path"].replace(".", "/"),
                    )
                )
        findings.extend(_unit_findings(active, profile, contract))
    return findings


def _array_member_findings(ref: str, requirement: dict[str, Any], contract: dict[str, Any]) -> list[ValidationFinding]:
    """Check a requirement that addresses every member of an array (decision D9).

    "dimensions.axes[].unit" means every axis declares a unit, so the requirement is checked once per
    member and reports which member failed. An empty or absent array cannot satisfy it.
    """

    path = requirement["path"]
    head, _, tail = path.partition("[]")
    container_path = head.strip(".")
    leaf = tail.strip(".")
    pointer = "/" + container_path.replace(".", "/")
    container = get_dotted(contract, container_path)
    if container is MISSING or not isinstance(container, list) or not container:
        return [ValidationFinding("BMCS_REQUIRED_MISSING", f"Profile {ref} requires '{path}', but it is missing.", pointer)]
    validator = Draft202012Validator(requirement["schema"], format_checker=FormatChecker())
    findings: list[ValidationFinding] = []
    for index, member in enumerate(container):
        value = get_dotted(member, leaf) if isinstance(member, dict) else MISSING
        if value is MISSING or value is None:
            findings.append(ValidationFinding("BMCS_REQUIRED_MISSING", f"Profile {ref} requires '{path}', but member {index} does not declare it.", f"{pointer}/{index}/{leaf.replace('.', '/')}"))
            continue
        for error in validator.iter_errors(value):
            findings.append(ValidationFinding("BMCS_PROFILE_VALUE_INVALID", f"{path}[{index}]: {error.message}", f"{pointer}/{index}/{leaf.replace('.', '/')}"))
    return findings


def _unit_findings(bundle: Bundle, profile: dict[str, Any], contract: dict[str, Any]) -> list[ValidationFinding]:
    """Check a declared unit against the profile's quantity kind (decision D1).

    A unit alone does not identify a quantity: hertz and becquerel are both per second, and a
    Hounsfield unit is dimensionless like a bare ratio. The dimension has to match, and a kind may
    refuse a unit whose UCUM property belongs to another quantity.
    """

    table = bundle.units
    value = get_dotted(contract, "measurement.unit")
    if not table or value is MISSING or value is None:
        return []
    path = "/measurement/unit"
    if not isinstance(value, str):
        return [ValidationFinding("BMCS_UNIT_INVALID", "measurement.unit must be a UCUM expression.", path)]
    try:
        declared = parse_unit(value, table)
    except UnitError as error:
        return [ValidationFinding("BMCS_UNIT_INVALID", f"measurement.unit: {error}", path)]
    quantity = get_dotted(profile.get("fixed", {}), "measurement.quantity")
    if quantity is MISSING or not isinstance(quantity, str):
        return []
    kind_id = quantity.rsplit("/", 1)[-1]
    kind = bundle.quantity_kinds.get(kind_id)
    if not kind:
        return []
    allowed = kind.get("allowed_units")
    if allowed and value not in allowed:
        return [ValidationFinding(
            "BMCS_UNIT_NOT_ALLOWED",
            f"measurement.unit: {value} is not one of the units {kind_id} accepts ({', '.join(allowed)}).",
            path)]
    forbidden = set(kind.get("forbidden_unit_properties", []))
    if forbidden:
        for code in sorted(declared.codes):
            entry = table.get("units", {}).get(code, {})
            if entry.get("property") in forbidden:
                return [ValidationFinding(
                    "BMCS_UNIT_NOT_ALLOWED",
                    f"measurement.unit: {code} measures {entry.get('property')}, which {kind_id} does not.",
                    path)]
    canonical = kind.get("canonical_unit")
    if canonical:
        try:
            expected = parse_unit(canonical, table)
        except UnitError:
            return []
        if declared.dimension != expected.dimension:
            return [ValidationFinding(
                "BMCS_UNIT_DIMENSION_MISMATCH",
                f"measurement.unit: {value} does not have the dimension of {kind_id} ({canonical}).",
                path)]
    return []


def _merge_refinement(
    base: dict[str, Any], refinement: dict[str, Any], *, path: str = ""
) -> tuple[dict[str, Any], list[str]]:
    """Merge an accepted representation while preserving every common invariant."""

    merged = deepcopy(base)
    conflicts: list[str] = []
    for key, value in refinement.items():
        child_path = f"{path}/{key}"
        if key not in merged:
            merged[key] = deepcopy(value)
        elif isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key], nested = _merge_refinement(merged[key], value, path=child_path)
            conflicts.extend(nested)
        elif merged[key] != value:
            conflicts.append(child_path)
    return merged, conflicts


def validate_manifest(
    manifest: dict[str, Any],
    *,
    bundle: Bundle | None = None,
    limits: ResourceLimits | None = None,
) -> list[ValidationFinding]:
    active = bundle or get_bundle()
    if limits is not None:
        active = Bundle(active.root, limits=limits)
    if "compatibility" not in manifest:
        return []
    findings = _schema_errors(manifest, "manifest-extension.schema.json", active)
    if any(item.reason_code == "BMCS_RESOURCE_LIMIT_EXCEEDED" for item in findings):
        return findings
    imported = {entry["ref"]: entry for entry in manifest.get("compatibility", {}).get("profiles", [])}
    for ref, entry in imported.items():
        catalogue_entry = active.profile_index.get(ref)
        if catalogue_entry is None:
            findings.append(ValidationFinding("BMCS_PROFILE_UNRESOLVED", f"Profile not found in the installed bundle: {ref}", "/compatibility/profiles"))
        elif entry.get("sha256") != catalogue_entry["sha256"]:
            findings.append(ValidationFinding("BMCS_DIGEST_MISMATCH", f"The sha256 for {ref} doesn't match the installed profile.", "/compatibility/profiles"))

    for direction in ("inputs", "outputs"):
        for index, port in enumerate(manifest.get("io", {}).get(direction, [])):
            contract = port.get("contract")
            if contract is not None:
                refs = contract.get("profile_refs", [])
                for ref in refs:
                    if ref not in imported:
                        findings.append(
                            ValidationFinding(
                                "BMCS_PROFILE_NOT_IMPORTED",
                                f"This port uses {ref}, but it isn't listed in compatibility.profiles.",
                                f"/io/{direction}/{index}/contract/profile_refs",
                            )
                        )
                findings.extend(validate_contract(contract, refs, bundle=active))
            for accepted_index, accepted in enumerate(port.get("accepted_profiles", [])):
                refinement = accepted.get("contract")
                if refinement is not None:
                    if contract is None:
                        findings.append(
                            ValidationFinding(
                                "BMCS_REFINEMENT_WITHOUT_BASE",
                                "An accepted profile contract must refine an input-level contract.",
                                f"/io/{direction}/{index}/accepted_profiles/{accepted_index}/contract",
                            )
                        )
                        continue
                    merged, conflicts = _merge_refinement(contract, refinement)
                    for conflict in conflicts:
                        findings.append(
                            ValidationFinding(
                                "BMCS_REFINEMENT_WEAKENS_CONTRACT",
                                f"The accepted profile changes the common invariant at {conflict}.",
                                f"/io/{direction}/{index}/accepted_profiles/{accepted_index}/contract{conflict}",
                            )
                        )
                    for item in validate_contract(
                        merged, contract.get("profile_refs", []), bundle=active
                    ):
                        findings.append(
                            ValidationFinding(
                                item.reason_code,
                                item.message,
                                f"/io/{direction}/{index}/accepted_profiles/{accepted_index}/contract{item.path}",
                                item.severity,
                            )
                        )
    return findings
