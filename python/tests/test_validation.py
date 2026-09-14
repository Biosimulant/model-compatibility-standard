import json
from pathlib import Path

import yaml

from biosimulant_model_compatibility_standard import get_bundle, validate_contract, validate_manifest


def test_all_profile_positive_negative_and_unknown_fixtures():
    bundle = get_bundle()
    fixture_root = Path(bundle.root) / "fixtures" / "profiles"
    files = sorted(fixture_root.rglob("*.json"))
    assert len(files) == 650
    for path in files:
        fixture = json.loads(path.read_text())
        ref = fixture["profile_ref"]
        positive, negative, unknown = fixture["cases"]
        assert validate_contract(positive["contract"], [ref]) == [], ref
        findings = validate_contract(negative["contract"], [ref])
        assert any(item.reason_code == negative["reason_code"] for item in findings), ref
        assert unknown["status"] == "UNKNOWN"


def test_legacy_manifest_does_not_opt_in_or_fail():
    bundle = get_bundle()
    manifest = yaml.safe_load((Path(bundle.root) / "examples" / "legacy-model.yaml").read_text())
    assert validate_manifest(manifest) == []


def test_opted_in_manifest_and_profile_digest_validate():
    bundle = get_bundle()
    manifest = yaml.safe_load((Path(bundle.root) / "examples" / "compatible-model.yaml").read_text())
    assert validate_manifest(manifest) == []


def test_wrong_profile_digest_is_rejected():
    bundle = get_bundle()
    manifest = yaml.safe_load((Path(bundle.root) / "examples" / "compatible-model.yaml").read_text())
    manifest["compatibility"]["profiles"][0]["sha256"] = "sha256:" + ("0" * 64)
    findings = validate_manifest(manifest)
    assert any(item.reason_code == "BMCS_DIGEST_MISMATCH" for item in findings)
