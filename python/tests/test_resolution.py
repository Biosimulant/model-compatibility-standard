from biosimulant_model_compatibility_standard import (
    digest,
    resolve_contracts,
    validate_object,
)

REF = "https://biosimulant.com/standards/model-compatibility/profiles/neuroscience/firing-rate/v0.1"


def _adapter(ref: str, source: dict, target: dict, *, loss: str = "none") -> dict:
    return {
        "schema_version": "0.1",
        "ref": ref,
        "sha256": digest({"release": ref}),
        "source": source,
        "target": target,
        "state": "reviewed",
        "transformation_class": "unit",
        "information_loss": loss,
        "loss_score": 0 if loss == "none" else 1,
        "execution_cost": 1,
        "release": {"version": "1.0.0"},
    }


def test_lossless_adapter_is_a_visible_plan_node():
    source = {"measurement": {"unit": "nmol/L"}}
    target = {"measurement": {"unit": "umol/L"}}
    result = resolve_contracts(
        source,
        target,
        [_adapter("https://biosimulant.com/adapters/nmol-to-umol/1.0.0", source, target)],
    )
    assert result["resolution"] == "RESOLVED"
    plan = result["plan"]
    assert [node["kind"] for node in plan["nodes"]] == ["contract", "adapter", "contract"]
    assert plan["policy"]["decision"] == "ALLOW"
    assert validate_object(plan, "resolution-plan.schema.json") == []


def test_revoked_capability_is_not_plannable():
    source = {"semantic": {"concept": "genome"}}
    target = {"semantic": {"concept": "expression"}}
    capability = _adapter("https://biosimulant.com/adapters/revoked/1.0.0", source, target)
    capability["state"] = "revoked"
    result = resolve_contracts(source, target, [capability])
    assert result["resolution"] == "UNRESOLVED"


def test_equal_cost_paths_require_explicit_selection():
    source = {"semantic": {"concept": "a"}}
    target = {"semantic": {"concept": "b"}}
    capabilities = [
        _adapter("https://biosimulant.com/adapters/a/1.0.0", source, target),
        _adapter("https://biosimulant.com/adapters/b/1.0.0", source, target),
    ]
    result = resolve_contracts(source, target, capabilities)
    assert result["resolution"] == "AMBIGUOUS"
    assert len(result["candidate_plans"]) == 2


def test_matching_preconditions_are_checked_instead_of_skipped():
    source = {"semantic": {"concept": "source"}}
    target = {"semantic": {"concept": "target"}}
    capability = _adapter(
        "https://biosimulant.com/adapters/precondition/1.0.0", source, target
    )
    capability["preconditions"] = [
        {
            "source": "/contract/semantic/concept",
            "target": "/contract/semantic/concept",
            "operator": "equal",
            "missing": "incompatible",
            "reason_code": "BMCS_PRECONDITION_FAILED",
        }
    ]
    assert resolve_contracts(source, target, [capability])["resolution"] == "RESOLVED"

    capability["preconditions"][0]["operator"] = "not-equal"
    assert resolve_contracts(source, target, [capability])["resolution"] == "UNRESOLVED"


def test_resolution_pins_verified_snapshots():
    contract = {"semantic": {"concept": "concentration"}}
    unsigned = {
        "ref": "https://biosimulant.com/snapshots/test-ontology/1.0.0",
        "equivalences": [],
    }
    snapshot = {**unsigned, "sha256": digest(unsigned)}
    result = resolve_contracts(
        contract,
        contract,
        ontology_snapshots=[snapshot],
    )
    assert result["report"]["snapshots"]["ontology"] == [
        {"ref": snapshot["ref"], "sha256": snapshot["sha256"]}
    ]
    assert {
        "kind": "ontology_snapshot",
        "ref": snapshot["ref"],
        "sha256": snapshot["sha256"],
    } in result["plan"]["immutable_references"]


def test_profile_transformation_policy_reaches_the_plan():
    # Every profile publishes transformation_policy and nothing read it: the only policy consulted
    # was the one a caller passed in by hand, so a profile's declared approval paths had no effect
    # on any plan (decision D11).
    source = {"measurement": {"unit": "Hz", "scale": "nominal"}, "profile_refs": [REF]}
    target = {"measurement": {"unit": "Hz", "scale": "ordinal"}, "profile_refs": [REF]}
    capability = _adapter(
        "https://biosimulant.com/adapters/rate-to-ordinal-band/1.0.0", source, target, loss="lossy"
    )
    capability["transformation_class"] = "aggregation"
    result = resolve_contracts(source, target, [capability])
    assert result["resolution"] == "RESOLVED"
    plan = result["plan"]
    assert plan["technical_status"] == "LOSSY_CONVERSION_REQUIRES_APPROVAL"
    # Read from the profile, translated out of the published allow/approval/block vocabulary.
    assert plan["policy"]["lossy"] == "APPROVAL_REQUIRED"
    assert plan["policy"]["lossless"] == "ALLOW"
    assert plan["policy"]["decision"] == "APPROVAL_REQUIRED"
    assert validate_object(plan, "resolution-plan.schema.json") == []
