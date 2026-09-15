from copy import deepcopy
from pathlib import Path

import yaml

from biosimulant_model_compatibility_standard import build_compatibility_lock, get_bundle


def test_lock_is_repeatable_and_leaves_manifest_unchanged():
    bundle = get_bundle()
    manifest = yaml.safe_load((Path(bundle.root) / "examples" / "compatible-model.yaml").read_text())
    original = deepcopy(manifest)
    first = build_compatibility_lock(manifest)
    second = build_compatibility_lock(manifest)
    assert first == second
    assert manifest == original
    assert first["bundle_sha256"] == bundle.digest
    assert first["digest"].startswith("sha256:")
