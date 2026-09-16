import json
from pathlib import Path

import yaml

from biosimulant_model_compatibility_standard import (
    Bundle,
    ResourceLimits,
    compare_contracts,
    get_bundle,
    validate_contract,
    validate_manifest,
)


def test_full_external_review_fixture_set_for_every_profile():
    bundle = get_bundle()
    fixture_root = Path(bundle.root) / "fixtures" / "profiles"
    files = sorted(fixture_root.rglob("*.json"))
    assert len(files) == bundle.catalogue["counts"]["profiles"]
    for path in files:
        fixture = json.loads(path.read_text())
        ref = fixture["profile_ref"]
        cases = {case["name"]: case for case in fixture["cases"]}
        profile = bundle.profile(ref)
        required = [item for item in profile["requirements"] if item["level"] == "required"]
        # Count the lossless cases rather than test that any exist: a profile can now carry both a
        # unit conversion and a representation re-encoding.
        lossless = sum(1 for case in cases if case.startswith("comparison-lossless"))
        # A requirement addressing every member of an array is validated, not compared: no pointer
        # means "each element", so it carries the two negative fixtures and none of the three
        # comparison ones.
        member_required = [item for item in required if "[]" in item["path"]]
        expected_count = 2 + (5 * (len(required) - len(member_required))) + (2 * len(member_required)) + lossless
        assert len(cases) == expected_count, ref
        positive = cases["positive"]
        assert validate_contract(positive["contract"], [ref]) == [], ref
        for name, case in cases.items():
            if name.startswith("negative-"):
                findings = validate_contract(case["contract"], [ref])
                assert any(item.reason_code == case["reason_code"] for item in findings), f"{ref}: {name}"
            elif name.startswith("comparison-"):
                report = compare_contracts(case["source"], case["target"], target_profile_refs=[ref])
                assert report["status"] == case["status"], f"{ref}: {name}"
                if case.get("reason_code"):
                    assert any(item["reason_code"] == case["reason_code"] for item in report["findings"]), f"{ref}: {name}"


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


def test_accepted_profile_contract_may_add_but_not_change_common_invariants():
    bundle = get_bundle()
    manifest = yaml.safe_load((Path(bundle.root) / "examples" / "compatible-model.yaml").read_text())
    port = manifest["io"]["inputs"][0]
    port["accepted_profiles"] = [{"contract": {"measurement": {"unit": "1"}}}]
    assert validate_manifest(manifest) == []

    port["accepted_profiles"][0]["contract"] = {
        "biological_context": {"species": "NCBITaxon:10090"}
    }
    findings = validate_manifest(manifest)
    assert any(item.reason_code == "BMCS_REFINEMENT_WEAKENS_CONTRACT" for item in findings)


def test_accepted_profile_contract_requires_a_common_contract():
    manifest = {
        "schema_version": "2.0",
        "compatibility": {"standard": "https://biosimulant.com/standards/model-compatibility/v0.1"},
        "io": {"inputs": [{"name": "x", "accepted_profiles": [{"contract": {"semantic": {"concept": "x"}}}]}], "outputs": []},
    }
    findings = validate_manifest(manifest)
    assert any(item.reason_code == "BMCS_REFINEMENT_WITHOUT_BASE" for item in findings)


def test_resource_limits_return_a_stable_finding():
    real = get_bundle()
    limited = Bundle(real.root, limits=ResourceLimits(max_depth=2))
    findings = validate_contract({"semantic": {"ontology_terms": [{"uri": "x"}]}}, bundle=limited)
    assert [item.reason_code for item in findings] == ["BMCS_RESOURCE_LIMIT_EXCEEDED"]
