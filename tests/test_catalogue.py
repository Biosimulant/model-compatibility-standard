from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

from biosimulant_model_compatibility_standard import (
    CATALOGUE_SHA256,
    STANDARD_ID,
    STANDARD_VERSION,
    get_profile,
    list_profiles,
    profile_digest,
)
from biosimulant_model_compatibility_standard.catalogue import (
    MAX_YAML_BYTES,
    StandardError,
    _load_catalogue,
)

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_REFS = [
    "boltz.binding-probability/v1",
    "boltz.log10-ic50-micromolar/v1",
    "chemical.smiles/v1",
    "protein-ligand.complex-structure-mmcif/v1",
    "protein.multiple-sequence-alignment/v1",
    "protein.sequence/v1",
]


def _copy_catalogue(tmp_path: Path) -> Path:
    shutil.copy(ROOT / "standard.yaml", tmp_path / "standard.yaml")
    shutil.copytree(ROOT / "profiles", tmp_path / "profiles")
    return tmp_path


def test_loads_expected_standard_and_profiles() -> None:
    assert STANDARD_ID == "biosimulant.model-compatibility"
    assert STANDARD_VERSION == "0"
    refs = [f"{p['profile']['id']}/v{p['profile']['version']}" for p in list_profiles()]
    assert refs == EXPECTED_REFS
    assert CATALOGUE_SHA256.startswith("sha256:")
    for ref in EXPECTED_REFS:
        assert get_profile(ref)["checker"]
        assert profile_digest(ref).startswith("sha256:")


def test_digests_are_deterministic_and_ignore_yaml_layout(tmp_path: Path) -> None:
    root = _copy_catalogue(tmp_path)
    first = _load_catalogue(root)
    path = root / "profiles" / "chemical.smiles.v1.yaml"
    parsed = yaml.safe_load(path.read_text())
    path.write_text(yaml.safe_dump(parsed, sort_keys=True), encoding="utf-8")
    second = _load_catalogue(root)
    assert first.digest == second.digest
    assert first.profile_digests == second.profile_digests


def test_filename_must_match_profile_reference(tmp_path: Path) -> None:
    root = _copy_catalogue(tmp_path)
    original = root / "profiles" / "chemical.smiles.v1.yaml"
    original.rename(root / "profiles" / "wrong.yaml")
    with pytest.raises(StandardError, match="must be named"):
        _load_catalogue(root)


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (lambda p: p.pop("definition"), "missing required fields"),
        (lambda p: p.update({"defintion": "typo"}), "unknown fields"),
        (lambda p: p["representations"][0].update({"unknown": True}), "unknown fields"),
        (lambda p: p["sources"][0].update({"url": "file:///tmp/source"}), "must be HTTP"),
    ],
)
def test_invalid_profile_is_rejected(tmp_path: Path, mutation, match: str) -> None:
    root = _copy_catalogue(tmp_path)
    path = root / "profiles" / "chemical.smiles.v1.yaml"
    profile = yaml.safe_load(path.read_text())
    mutation(profile)
    path.write_text(yaml.safe_dump(profile), encoding="utf-8")
    with pytest.raises(StandardError, match=match):
        _load_catalogue(root)


def test_oversized_yaml_is_rejected(tmp_path: Path) -> None:
    root = _copy_catalogue(tmp_path)
    path = root / "profiles" / "chemical.smiles.v1.yaml"
    path.write_text("x" * (MAX_YAML_BYTES + 1), encoding="utf-8")
    with pytest.raises(StandardError, match="exceeds"):
        _load_catalogue(root)


def test_unexpected_profile_directory_entries_are_rejected(tmp_path: Path) -> None:
    root = _copy_catalogue(tmp_path)
    (root / "profiles" / "nested").mkdir()
    with pytest.raises(StandardError, match="unexpected entry"):
        _load_catalogue(root)


def test_source_objects_are_defensive_copies() -> None:
    profile = get_profile("chemical.smiles/v1")
    profile["definition"] = "changed"
    assert get_profile("chemical.smiles/v1")["definition"] != "changed"


def test_wheel_contains_catalogue_and_matches_source_digest(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist), str(ROOT)],
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(dist.glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        prefix = "biosimulant_model_compatibility_standard/data/"
        assert prefix + "standard.yaml" in names
        for filename in (ROOT / "profiles").glob("*.yaml"):
            assert prefix + "profiles/" + filename.name in names

    target = tmp_path / "installed"
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(target), str(wheel)],
        check=True,
        capture_output=True,
        text=True,
    )
    code = (
        "import sys; "
        f"sys.path.insert(0, {str(target)!r}); "
        "from biosimulant_model_compatibility_standard import CATALOGUE_SHA256; "
        "print(CATALOGUE_SHA256)"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == CATALOGUE_SHA256
