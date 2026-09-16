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
    source = {"measurement": {"unit": "nmol/L"}}
    target = {"measurement": {"unit": "umol/L"}}
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


class _PermutationBundle:
    # The real bundle, except every profile has a single labels-permutation rule.
    def __init__(self):
        real = get_bundle()
        self.digest = real.digest
        self.units = real.units

    def profile(self, ref):
        rule = {
            "source": "/contract/dimensions/axes",
            "target": "/contract/dimensions/axes",
            "operator": "labels-permutation",
            "missing": "unknown",
            "reason_code": "BMCS_VALUE_MISMATCH",
        }
        return {"comparison_rules": [rule]}


def test_reordered_axis_labels_are_a_lossless_conversion():
    source = {"dimensions": {"axes": ["gene", "sample"]}}
    target = {"dimensions": {"axes": ["sample", "gene"]}}
    report = compare_contracts(source, target, target_profile_refs=["test"], bundle=_PermutationBundle())
    assert report["status"] == "LOSSLESS_CONVERSION_AVAILABLE"
    assert report["policy_decision"] == "ALLOW"


class _RuleBundle:
    def __init__(self, rule):
        real = get_bundle()
        self.digest = real.digest
        self.units = real.units
        self.rule = rule

    def profile(self, ref):
        return {"comparison_rules": [self.rule]}


def _rule_report(operator, source, target, *, parameters=None, ontology=(), mappings=()):
    rule = {
        "source": "/contract/value/current",
        "target": "/contract/value/current",
        "operator": operator,
        "missing": "unknown",
        "reason_code": "BMCS_VALUE_MISMATCH",
    }
    if parameters:
        rule["parameters"] = parameters
    return compare_contracts(
        {"value": {"current": source}},
        {"value": {"current": target}},
        target_profile_refs=["test"],
        bundle=_RuleBundle(rule),
        ontology_snapshots=ontology,
        mapping_snapshots=mappings,
    )


def test_scalar_collection_range_pattern_and_dimension_operators():
    assert _rule_report("in", "a", ["a", "b"])["status"] == "DIRECT_COMPATIBLE"
    assert _rule_report("not-in", "c", ["a", "b"])["status"] == "DIRECT_COMPATIBLE"
    assert _rule_report("range", {"minimum": 2, "maximum": 4}, {"minimum": 1, "maximum": 5})["status"] == "DIRECT_COMPATIBLE"
    assert _rule_report("pattern", "ENSG0001", "ignored", parameters={"pattern": "ENSG[0-9]+"})["status"] == "DIRECT_COMPATIBLE"
    # same-dimension is convertibility, decided against the published UCUM table. It used to read a
    # four-row table whose rows were nM/uM, so it answered for those two spellings and nothing else.
    assert _rule_report("same-dimension", "g", "kg")["status"] == "DIRECT_COMPATIBLE"
    assert _rule_report("same-dimension", "Cel", "K")["status"] == "DIRECT_COMPATIBLE"
    assert _rule_report("same-dimension", "g", "s")["status"] == "INCOMPATIBLE"
    # nM and uM are not UCUM codes: M is the mega prefix. Unreadable is undecidable, never a match.
    assert _rule_report("same-dimension", "nM", "uM")["status"] == "UNKNOWN"


def test_pinned_ontology_and_mapping_snapshots_are_enforced():
    ontology_unsigned = {
        "ref": "https://biosimulant.com/snapshots/test-ontology/v1",
        "equivalences": [["TERM:A", "TERM:A_ALIAS"]],
        "subsumptions": [{"parent": "TERM:PARENT", "child": "TERM:CHILD"}],
    }
    ontology = {**ontology_unsigned, "sha256": digest(ontology_unsigned)}
    parameters = {"snapshot_ref": ontology["ref"], "snapshot_sha256": ontology["sha256"]}
    assert _rule_report("term-equivalent", "TERM:A_ALIAS", "TERM:A", parameters=parameters, ontology=[ontology])["status"] == "DIRECT_COMPATIBLE"
    assert _rule_report("term-subsumes", "TERM:CHILD", "TERM:PARENT", parameters=parameters, ontology=[ontology])["status"] == "DIRECT_COMPATIBLE"
    assert _rule_report("term-subsumes", "TERM:CHILD", "TERM:PARENT", parameters=parameters)["status"] == "UNKNOWN"

    mapping_unsigned = {
        "ref": "https://biosimulant.com/snapshots/test-mapping/v1",
        "mappings": [{"source": "A", "target": "1"}, {"source": "B", "target": "2"}],
    }
    mapping = {**mapping_unsigned, "sha256": digest(mapping_unsigned)}
    parameters = {"snapshot_ref": mapping["ref"], "snapshot_sha256": mapping["sha256"]}
    # A pinned mapping that is total and bijective loses nothing, but translating identifiers is
    # still a conversion rather than a direct match.
    assert _rule_report("mapping-total", ["A", "B"], ["1", "2"], parameters=parameters, mappings=[mapping])["status"] == "LOSSLESS_CONVERSION_AVAILABLE"
    assert _rule_report("mapping-bijective", ["A", "B"], ["1", "2"], parameters=parameters, mappings=[mapping])["status"] == "LOSSLESS_CONVERSION_AVAILABLE"

    # A mapping that is total but merges two identifiers onto one is not reversible, so it needs
    # approval rather than passing as a lossless translation.
    merging_unsigned = {
        "ref": "https://biosimulant.com/snapshots/test-merge/v1",
        "mappings": [{"source": "A", "target": "1"}, {"source": "B", "target": "1"}],
    }
    merging = {**merging_unsigned, "sha256": digest(merging_unsigned)}
    merge_parameters = {"snapshot_ref": merging["ref"], "snapshot_sha256": merging["sha256"]}
    merged = _rule_report("mapping-total", ["A", "B"], ["1"], parameters=merge_parameters, mappings=[merging])
    assert merged["status"] == "LOSSY_CONVERSION_REQUIRES_APPROVAL"
    assert merged["policy_decision"] == "APPROVAL_REQUIRED"
    # The same merging snapshot cannot satisfy a bijective requirement at all.
    assert _rule_report("mapping-bijective", ["A", "B"], ["1"], parameters=merge_parameters, mappings=[merging])["status"] == "INCOMPATIBLE"


def test_a_namespace_release_change_is_a_mapping_not_a_contradiction():
    # Two releases of one namespace are not a contradiction: identifiers are retired
    # and merged between releases, so what matters is what the transition did.
    def snapshot(transitions):
        unsigned = {
            "ref": "https://biosimulant.com/snapshots/ensembl-releases/v1",
            "namespace": "ensembl",
            "transitions": transitions,
        }
        signed = {**unsigned, "sha256": digest(unsigned)}
        return signed, {"snapshot_ref": signed["ref"], "snapshot_sha256": signed["sha256"]}

    clean, clean_parameters = snapshot(
        [{"from": "110", "to": "114", "identifiers_retired": 0, "identifiers_merged": 0}]
    )
    lossy, lossy_parameters = snapshot(
        [{"from": "110", "to": "114", "identifiers_retired": 12, "identifiers_merged": 3}]
    )

    # A transition that retired and merged nothing preserves every identifier.
    assert _rule_report("namespace-version-compatible", "110", "114", parameters=clean_parameters, mappings=[clean])["status"] == "LOSSLESS_CONVERSION_AVAILABLE"
    # One that retired or merged identifiers is a real loss and needs approval.
    approval = _rule_report("namespace-version-compatible", "110", "114", parameters=lossy_parameters, mappings=[lossy])
    assert approval["status"] == "LOSSY_CONVERSION_REQUIRES_APPROVAL"
    assert approval["policy_decision"] == "APPROVAL_REQUIRED"
    # Without a pinned snapshot nobody can say, which is undecidable rather than a mismatch.
    assert _rule_report("namespace-version-compatible", "110", "114")["status"] == "UNKNOWN"
    # A snapshot that says nothing about this pair of releases decides nothing either.
    assert _rule_report("namespace-version-compatible", "110", "999", parameters=clean_parameters, mappings=[clean])["status"] == "UNKNOWN"
