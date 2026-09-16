from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Mapping

import yaml

MAX_YAML_BYTES = 256 * 1024
PROFILE_REF_RE = re.compile(r"^(?P<id>[a-z0-9]+(?:[.-][a-z0-9]+)*)/v(?P<version>[1-9][0-9]*)$")
PROFILE_ID_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")

_STANDARD_KEYS = {"schema_version", "standard"}
_STANDARD_BODY_KEYS = {"id", "version"}
_PROFILE_KEYS = {
    "schema_version",
    "profile",
    "definition",
    "representations",
    "checker",
    "context_fields",
    "limitations",
    "sources",
}
_PROFILE_BODY_KEYS = {"id", "version", "title"}
_REPRESENTATION_KEYS = {"signal_type", "dtypes", "formats", "value_type", "shape", "unit"}
_SOURCE_KEYS = {"title", "url"}
_CONTEXT_FIELDS = {"species", "identifier_namespace"}
_SIGNAL_TYPES = {"scalar", "array", "record", "event"}
_VALUE_TYPES = {"file"}


class StandardError(ValueError):
    """Raised when the packaged compatibility catalogue is invalid."""


@dataclass(frozen=True)
class Catalogue:
    standard: Mapping[str, Any]
    profiles: Mapping[str, Mapping[str, Any]]
    profile_digests: Mapping[str, str]
    digest: str


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StandardError(f"{label} must be a mapping")
    if not all(isinstance(key, str) for key in value):
        raise StandardError(f"{label} keys must be strings")
    return value


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing:
        raise StandardError(f"{label} is missing required fields: {', '.join(sorted(missing))}")
    if unknown:
        raise StandardError(f"{label} contains unknown fields: {', '.join(sorted(unknown))}")


def _require_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StandardError(f"{label} must be a non-empty string")
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise StandardError(f"cannot read {path}: {exc}") from exc
    if size > MAX_YAML_BYTES:
        raise StandardError(f"{path.name} exceeds the {MAX_YAML_BYTES}-byte limit")
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise StandardError(f"cannot parse {path}: {exc}") from exc
    return _require_mapping(parsed, path.name)


def _validate_standard(raw: dict[str, Any]) -> dict[str, Any]:
    _require_exact_keys(raw, _STANDARD_KEYS, "standard.yaml")
    if raw["schema_version"] != "1":
        raise StandardError("standard.yaml schema_version must be '1'")
    standard = _require_mapping(raw["standard"], "standard")
    _require_exact_keys(standard, _STANDARD_BODY_KEYS, "standard")
    if standard["id"] != "biosimulant.model-compatibility":
        raise StandardError("standard.id must be biosimulant.model-compatibility")
    if standard["version"] != "0":
        raise StandardError("standard.version must be '0'")
    return raw


def _validate_string_list(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        prefix = "possibly empty " if allow_empty else "non-empty "
        raise StandardError(f"{label} must be a {prefix}list")
    for item in value:
        _require_non_empty_string(item, label)
    if len(set(value)) != len(value):
        raise StandardError(f"{label} must not contain duplicates")
    return value


def _validate_representation(raw: Any, label: str) -> dict[str, Any]:
    value = _require_mapping(raw, label)
    unknown = set(value) - _REPRESENTATION_KEYS
    if unknown:
        raise StandardError(f"{label} contains unknown fields: {', '.join(sorted(unknown))}")
    if "signal_type" not in value or "dtypes" not in value:
        raise StandardError(f"{label} requires signal_type and dtypes")
    if value["signal_type"] not in _SIGNAL_TYPES:
        raise StandardError(f"{label}.signal_type is unsupported")
    _validate_string_list(value["dtypes"], f"{label}.dtypes")
    if "formats" in value:
        _validate_string_list(value["formats"], f"{label}.formats")
    if "value_type" in value and value["value_type"] not in _VALUE_TYPES:
        raise StandardError(f"{label}.value_type is unsupported")
    if "shape" in value:
        shape = value["shape"]
        if not isinstance(shape, list) or any(
            not (isinstance(item, int) and item >= 0) and item != "*" for item in shape
        ):
            raise StandardError(f"{label}.shape must contain non-negative integers or '*'")
    if "unit" in value:
        _require_non_empty_string(value["unit"], f"{label}.unit")
    return value


def _validate_profile(raw: dict[str, Any], path: Path) -> tuple[str, dict[str, Any]]:
    _require_exact_keys(raw, _PROFILE_KEYS, path.name)
    if raw["schema_version"] != "1":
        raise StandardError(f"{path.name} schema_version must be '1'")
    identity = _require_mapping(raw["profile"], f"{path.name}.profile")
    _require_exact_keys(identity, _PROFILE_BODY_KEYS, f"{path.name}.profile")
    profile_id = _require_non_empty_string(identity["id"], f"{path.name}.profile.id")
    version = _require_non_empty_string(identity["version"], f"{path.name}.profile.version")
    _require_non_empty_string(identity["title"], f"{path.name}.profile.title")
    if not PROFILE_ID_RE.fullmatch(profile_id):
        raise StandardError(f"{path.name} has an invalid profile id")
    if not version.isdigit() or int(version) < 1:
        raise StandardError(f"{path.name} has an invalid profile version")
    ref = f"{profile_id}/v{version}"
    expected_filename = f"{profile_id}.v{version}.yaml"
    if path.name != expected_filename:
        raise StandardError(f"{path.name} must be named {expected_filename}")
    _require_non_empty_string(raw["definition"], f"{path.name}.definition")
    representations = raw["representations"]
    if not isinstance(representations, list) or not representations:
        raise StandardError(f"{path.name}.representations must be a non-empty list")
    for index, representation in enumerate(representations):
        _validate_representation(representation, f"{path.name}.representations[{index}]")
    _require_non_empty_string(raw["checker"], f"{path.name}.checker")
    context_fields = _validate_string_list(
        raw["context_fields"], f"{path.name}.context_fields", allow_empty=True
    )
    unsupported_context = set(context_fields) - _CONTEXT_FIELDS
    if unsupported_context:
        raise StandardError(
            f"{path.name} has unsupported context fields: {', '.join(sorted(unsupported_context))}"
        )
    _validate_string_list(raw["limitations"], f"{path.name}.limitations")
    sources = raw["sources"]
    if not isinstance(sources, list) or not sources:
        raise StandardError(f"{path.name}.sources must be a non-empty list")
    for index, raw_source in enumerate(sources):
        source = _require_mapping(raw_source, f"{path.name}.sources[{index}]")
        _require_exact_keys(source, _SOURCE_KEYS, f"{path.name}.sources[{index}]")
        _require_non_empty_string(source["title"], f"{path.name}.sources[{index}].title")
        url = _require_non_empty_string(source["url"], f"{path.name}.sources[{index}].url")
        if not url.startswith(("https://", "http://")):
            raise StandardError(f"{path.name}.sources[{index}].url must be HTTP(S)")
    return ref, raw


def _default_data_root() -> Path:
    package_data = resources.files("biosimulant_model_compatibility_standard").joinpath("data")
    package_path = Path(str(package_data))
    if package_path.is_dir():
        return package_path
    source_root = Path(__file__).resolve().parents[2]
    if (source_root / "standard.yaml").is_file():
        return source_root
    raise StandardError("packaged standard data is missing")


def _load_catalogue(root: Path) -> Catalogue:
    standard = _validate_standard(_load_yaml(root / "standard.yaml"))
    profiles_path = root / "profiles"
    if not profiles_path.is_dir():
        raise StandardError("profiles directory is missing")
    profiles: dict[str, Mapping[str, Any]] = {}
    digests: dict[str, str] = {}
    for path in sorted(profiles_path.iterdir(), key=lambda item: item.name):
        if path.name.startswith("."):
            continue
        if not path.is_file() or path.suffix != ".yaml":
            raise StandardError(f"unexpected entry in profiles directory: {path.name}")
        ref, profile = _validate_profile(_load_yaml(path), path)
        if ref in profiles:
            raise StandardError(f"duplicate profile reference: {ref}")
        profiles[ref] = profile
        digests[ref] = _sha256(profile)
    if not profiles:
        raise StandardError("catalogue must contain at least one profile")
    ordered_profiles = dict(sorted(profiles.items()))
    ordered_digests = dict(sorted(digests.items()))
    digest_input = {
        "standard": standard,
        "profiles": [
            {"ref": ref, "sha256": ordered_digests[ref]} for ref in ordered_profiles
        ],
    }
    return Catalogue(standard, ordered_profiles, ordered_digests, _sha256(digest_input))


_CATALOGUE = _load_catalogue(_default_data_root())


def load_standard() -> dict[str, Any]:
    return {
        "standard": copy.deepcopy(_CATALOGUE.standard),
        "profiles": copy.deepcopy(_CATALOGUE.profiles),
    }


def list_profiles() -> list[dict[str, Any]]:
    return [copy.deepcopy(_CATALOGUE.profiles[ref]) for ref in _CATALOGUE.profiles]


def get_profile(ref: str) -> dict[str, Any]:
    if not PROFILE_REF_RE.fullmatch(ref):
        raise KeyError(ref)
    try:
        return copy.deepcopy(_CATALOGUE.profiles[ref])
    except KeyError as exc:
        raise KeyError(f"unknown compatibility profile: {ref}") from exc


def profile_digest(ref: str) -> str:
    try:
        return _CATALOGUE.profile_digests[ref]
    except KeyError as exc:
        raise KeyError(f"unknown compatibility profile: {ref}") from exc


def catalogue_digest() -> str:
    return _CATALOGUE.digest
