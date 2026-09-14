from biosimulant_model_compatibility_standard import (
    canonical_bytes,
    compare_contracts,
    digest,
    get_bundle,
    validate_object,
)


def test_canonical_digest_is_order_independent_for_object_keys():
    assert digest({"b": 2, "a": 1}) == digest({"a": 1, "b": 2})


def test_exact_contract():
    contract = {"semantic": {"concept": "concentration", "subject": "compound"}}
    report = compare_contracts(contract, dict(contract))
    assert report["status"] == "EXACT"
    assert report["policy_decision"] == "ALLOW"
    assert validate_object(report, "compatibility-report.schema.json") == []


def test_missing_contract_is_unknown_and_policy_blocked():
    report = compare_contracts(None, {"semantic": {"concept": "concentration"}})
    assert report["status"] == "UNKNOWN"
    assert report["policy_decision"] == "BLOCK"


def test_known_biological_contradiction_beats_unrelated_unknown():
    source = {"semantic": {"concept": "concentration"}, "biological_context": {"compartment": "extracellular"}}
    target = {"semantic": {"concept": "concentration", "subject": "compound"}, "biological_context": {"compartment": "intracellular"}}
    report = compare_contracts(source, target)
    assert report["status"] == "INCOMPATIBLE"


def test_lossless_unit_conversion_is_visible():
    source = {"measurement": {"unit": "nM"}}
    target = {"measurement": {"unit": "uM"}}
    report = compare_contracts(source, target)
    assert report["status"] == "LOSSLESS_CONVERSION_AVAILABLE"
    assert report["policy_decision"] == "ALLOW"


def test_committed_cross_language_golden_vectors():
    bundle = get_bundle()
    canonical = bundle.read_json("fixtures/golden/canonicalization.json")
    for case in canonical["cases"]:
        assert canonical_bytes(case["input"]).decode("utf-8") == case["canonical"]
        assert digest(case["input"]) == case["sha256"]
    comparisons = bundle.read_json("fixtures/golden/comparison-statuses.json")
    for case in comparisons["cases"]:
        assert compare_contracts(case["source"], case["target"])["status"] == case["status"]
