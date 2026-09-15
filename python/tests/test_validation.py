import json
from pathlib import Path

import yaml

from biosimulant_model_compatibility_standard import (
    compare_contracts,
    get_bundle,
    validate_contract,
    validate_manifest,
)


def test_positive_negative_and_unknown_fixtures_for_every_profile():
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
        report = compare_contracts(unknown["source"], unknown["target"], target_profile_refs=[ref])
        assert report["status"] == unknown["status"], ref


def test_manifest_without_compatibility_block_is_valid():
    bundle = get_bundle()
    manifest = yaml.safe_load((Path(bundle.root) / "examples" / "legacy-model.yaml").read_text())
    assert validate_manifest(manifest) == []


def test_manifest_with_compatibility_block_is_valid():
    bundle = get_bundle()
    manifest = yaml.safe_load((Path(bundle.root) / "examples" / "compatible-model.yaml").read_text())
    assert validate_manifest(manifest) == []


def test_wrong_profile_digest_is_rejected():
    bundle = get_bundle()
    manifest = yaml.safe_load((Path(bundle.root) / "examples" / "compatible-model.yaml").read_text())
    manifest["compatibility"]["profiles"][0]["sha256"] = "sha256:" + ("0" * 64)
    findings = validate_manifest(manifest)
    assert any(item.reason_code == "BMCS_DIGEST_MISMATCH" for item in findings)


def test_unknown_profile_uses_a_defined_reason_code():
    bundle = get_bundle()
    reason_codes = bundle.read_json("rules/reason-codes.json")["reason_codes"]
    findings = validate_contract({}, ["https://biosimulant.com/standards/model-compatibility/profiles/core/missing/v0.1"])
    assert [item.reason_code for item in findings] == ["BMCS_PROFILE_UNRESOLVED"]
    assert all(item.reason_code in reason_codes for item in findings)
