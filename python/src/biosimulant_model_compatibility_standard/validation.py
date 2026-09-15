"""Check contracts and manifests against the bundled JSON Schemas and profile requirements."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .bundle import Bundle, get_bundle
from .pointers import MISSING, get_dotted


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
) -> list[ValidationFinding]:
    """Validate an object against a bundled schema, e.g. 'compatibility-report.schema.json'."""

    active = bundle or get_bundle()
    normalized_name = schema_name if schema_name.endswith(".json") else f"{schema_name}.json"
    if normalized_name not in active.schema_index:
        raise KeyError(f"Unknown standard schema: {schema_name}")
    return _schema_errors(instance, normalized_name, active)


def validate_contract(
    contract: dict[str, Any],
    profile_refs: Iterable[str] = (),
    *,
    bundle: Bundle | None = None,
) -> list[ValidationFinding]:
    active = bundle or get_bundle()
    findings = _schema_errors(contract, "port-contract.schema.json", active)
    for ref in profile_refs:
        try:
            profile = active.profile(ref)
        except KeyError:
            findings.append(ValidationFinding("BMCS_PROFILE_UNRESOLVED", f"Profile not found in the installed bundle: {ref}", "/profile_refs"))
            continue
        for requirement in profile.get("requirements", []):
            if requirement.get("level") != "required":
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
            for error in Draft202012Validator(requirement["schema"]).iter_errors(value):
                findings.append(
                    ValidationFinding(
                        "BMCS_PROFILE_VALUE_INVALID",
                        f"{requirement['path']}: {error.message}",
                        "/" + requirement["path"].replace(".", "/"),
                    )
                )
    return findings


def validate_manifest(manifest: dict[str, Any], *, bundle: Bundle | None = None) -> list[ValidationFinding]:
    active = bundle or get_bundle()
    if "compatibility" not in manifest:
        return []
    findings = _schema_errors(manifest, "manifest-extension.schema.json", active)
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
                    findings.extend(validate_contract(refinement, (), bundle=active))
    return findings
