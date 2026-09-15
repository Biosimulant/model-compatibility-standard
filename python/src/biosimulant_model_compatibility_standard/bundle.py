"""Read-only access to the specification bundle shipped with the package."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from functools import cached_property, lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any, Iterator

from .canonical import digest
from .security import DEFAULT_RESOURCE_LIMITS, ResourceLimitError, ResourceLimits, ensure_json_limits


def _spec_root() -> Any:
    packaged = files(__package__).joinpath("spec/v0.1")
    if packaged.joinpath("bundle.manifest.json").is_file():
        return packaged
    # Not installed from a wheel: use spec/ from the repository checkout.
    return Path(__file__).resolve().parents[3] / "spec" / "v0.1"


@dataclass(frozen=True)
class Bundle:
    root: Any
    limits: ResourceLimits = DEFAULT_RESOURCE_LIMITS

    def _target(self, relative_path: str) -> Any:
        parts = Path(relative_path).parts
        if not parts or Path(relative_path).is_absolute() or ".." in parts:
            raise ValueError(f"Bundle path must be relative and contained in the bundle: {relative_path}")
        return self.root.joinpath(*parts)

    def read_json(self, relative_path: str) -> Any:
        target = self._target(relative_path)
        data = target.read_bytes()
        if len(data) > self.limits.max_document_bytes:
            raise ResourceLimitError(
                f"Bundle file {relative_path} is {len(data)} bytes; the limit is "
                f"{self.limits.max_document_bytes} bytes."
            )
        value = json.loads(data)
        ensure_json_limits(value, limits=self.limits)
        return value

    @cached_property
    def manifest(self) -> dict[str, Any]:
        return self.read_json("bundle.manifest.json")

    @property
    def digest(self) -> str:
        return self.manifest["bundle_sha256"]

    @cached_property
    def catalogue(self) -> dict[str, Any]:
        return self.read_json("catalogue/catalogue.json")

    @cached_property
    def profile_index(self) -> dict[str, dict[str, Any]]:
        return {entry["ref"]: entry for entry in self.catalogue["profiles"]}

    @cached_property
    def schema_index(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        schema_root = self.root.joinpath("schemas")
        for child in schema_root.iterdir():
            if child.name.endswith(".json"):
                schema = self.read_json(f"schemas/{child.name}")
                result[schema["$id"]] = schema
                result[child.name] = schema
        return result

    @cached_property
    def unit_conversions(self) -> list[dict[str, Any]]:
        return self.read_json("rules/unit-conversions.json")["conversions"]

    def profile(self, ref: str) -> dict[str, Any]:
        entry = self.profile_index.get(ref)
        if entry is None:
            raise KeyError(f"Unknown profile reference: {ref}")
        profile_prefix = "https://biosimulant.com/standards/model-compatibility/profiles/"
        relative = ref.removeprefix(profile_prefix) + ".json"
        return self.read_json(f"profiles/{relative}")

    def profiles(self) -> Iterator[dict[str, Any]]:
        for ref in sorted(self.profile_index):
            yield self.profile(ref)

    def verify_integrity(self) -> None:
        """Verify every released file and the bundle manifest's own digest."""

        manifest = self.manifest
        declared_digest = manifest.get("bundle_sha256")
        unsigned = {key: value for key, value in manifest.items() if key != "bundle_sha256"}
        if declared_digest != digest(unsigned):
            raise ValueError("The bundle manifest digest does not match its contents.")

        seen: set[str] = set()
        for entry in manifest.get("files", []):
            relative_path = entry.get("path")
            if not isinstance(relative_path, str) or relative_path in seen:
                raise ValueError("The bundle manifest contains an invalid or duplicate file path.")
            seen.add(relative_path)
            target = self._target(relative_path)
            if not target.is_file():
                raise ValueError(f"Bundle file is missing: {relative_path}")
            data = target.read_bytes()
            if len(data) != entry.get("size_bytes"):
                raise ValueError(f"Bundle file size does not match the manifest: {relative_path}")
            actual = "sha256:" + hashlib.sha256(data).hexdigest()
            if actual != entry.get("sha256"):
                raise ValueError(f"Bundle file digest does not match the manifest: {relative_path}")


@lru_cache(maxsize=1)
def get_bundle() -> Bundle:
    return Bundle(_spec_root())
