"""Read-only access to the specification bundle shipped with the package."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property, lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any, Iterator


def _spec_root() -> Any:
    packaged = files(__package__).joinpath("spec/v0.1")
    if packaged.joinpath("bundle.manifest.json").is_file():
        return packaged
    # Not installed from a wheel: use spec/ from the repository checkout.
    return Path(__file__).resolve().parents[3] / "spec" / "v0.1"


@dataclass(frozen=True)
class Bundle:
    root: Any

    def read_json(self, relative_path: str) -> Any:
        target = self.root.joinpath(relative_path)
        with target.open("r", encoding="utf-8") as stream:
            return json.load(stream)

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


@lru_cache(maxsize=1)
def get_bundle() -> Bundle:
    return Bundle(_spec_root())
