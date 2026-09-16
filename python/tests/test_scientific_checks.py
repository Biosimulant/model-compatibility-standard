"""Scientific guards shared by the Python and TypeScript implementations."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from biosimulant_model_compatibility_standard import compare_contracts, normalize_contract, resolve_contracts, validate_contract

ROOT = Path(__file__).resolve().parents[2]
SUITE = json.loads((ROOT / "scientific-checks" / "v0.1" / "cases.json").read_text(encoding="utf-8"))
FIXTURES = ROOT / "spec" / "v0.1" / "fixtures" / "profiles"
NOT_A_MATCH = "is not scientifically acceptable here"


def _ref(profile: str) -> str:
    return f"{SUITE['profile_ref_prefix']}{profile}{SUITE['profile_ref_suffix']}"


def _fixture_cases(path: Path) -> dict[str, dict[str, Any]]:
    return {case["name"]: case for case in json.loads(path.read_text(encoding="utf-8"))["cases"]}


def _merge(base: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)


def _contract(case: dict[str, Any], side: str) -> dict[str, Any]:
    contract = copy.deepcopy(_fixture_cases(FIXTURES / f"{case['profile']}.json")["positive"]["contract"])
    _merge(contract, case.get(f"{side}_patch", {}))
    for path in case.get(f"{side}_remove", []):
        *parents, leaf = path.split(".")
        node = contract
        for part in parents:
            node = node.get(part, {})
        node.pop(leaf, None)
    return contract


def _capabilities(case: dict[str, Any], source: dict[str, Any], target: dict[str, Any]) -> list[dict[str, Any]]:
    """Capabilities for a resolve case, with the contract sentinels filled in.

    resolve_contracts indexes a capability by the digest of its source contract, so a capability
    written into the case file cannot name a contract the harness builds from the profile fixture.
    "$source" and "$target" stand in for those two contracts.
    """

    filled: list[dict[str, Any]] = []
    for capability in case.get("capabilities", []):
        entry = copy.deepcopy(capability)
        for side in ("source", "target"):
            if entry.get(side) == "$source":
                entry[side] = copy.deepcopy(source)
            elif entry.get(side) == "$target":
                entry[side] = copy.deepcopy(target)
        filled.append(entry)
    return filled


def violations(case: dict[str, Any]) -> list[str]:
    expect = case["expect"]
    found: list[str] = []
    if case["check"] == "compare":
        refs = [_ref(case["profile"])]
        source, target = _contract(case, "source"), _contract(case, "target")
        if case.get("normalize"):
            source, target = normalize_contract(source), normalize_contract(target)
        report = compare_contracts(source, target, source_profile_refs=refs, target_profile_refs=refs)
        status, policy = report["status"], report["policy_decision"]
        if "status" in expect and status != expect["status"]:
            found.append(f"status {status}, expected {expect['status']}")
        if status in expect.get("status_not_in", []):
            found.append(f"status {status} {NOT_A_MATCH}")
        if "policy_decision_not" in expect and policy == expect["policy_decision_not"]:
            found.append(f"policy decision {policy} {NOT_A_MATCH}")
        if "policy_finding_reason_code" in expect and not any(
            item.get("reason_code") == expect["policy_finding_reason_code"]
            for item in report.get("policy_findings", [])
        ):
            # A governance outcome is reported separately from the technical findings.
            found.append(f"no policy finding {expect['policy_finding_reason_code']}")
    elif case["check"] == "validate":
        errors = [f for f in validate_contract(_contract(case, "source"), [_ref(case["profile"])]) if f.severity == "error"]
        if expect.get("error_findings") == "at-least-one" and not errors:
            found.append("contract validated with no error finding")
    elif case["check"] == "resolve":
        # The lossy and inference statuses are produced by the resolution layer, not by comparison,
        # so a case that exercises an approval path has to plan a capability chain.
        source, target = _contract(case, "source"), _contract(case, "target")
        result = resolve_contracts(source, target, _capabilities(case, source, target))
        plan = result.get("plan") or {}
        # The chain's own status, not the terminal comparison: reports[] is EXACT whenever the last
        # adapter lands exactly on the target, which would make an approval-path case vacuous.
        status = plan.get("technical_status")
        decision = (plan.get("policy") or {}).get("decision")
        if "resolution" in expect and result["resolution"] != expect["resolution"]:
            found.append(f"resolution {result['resolution']}, expected {expect['resolution']}")
        if "plan_status" in expect and status != expect["plan_status"]:
            found.append(f"plan status {status}, expected {expect['plan_status']}")
        if "policy_decision" in expect and decision != expect["policy_decision"]:
            found.append(f"policy decision {decision}, expected {expect['policy_decision']}")
        if "policy_decision_not" in expect and decision == expect["policy_decision_not"]:
            found.append(f"policy decision {decision} {NOT_A_MATCH}")
    else:
        raise ValueError(f"unknown check {case['check']}")
    return found


@pytest.mark.parametrize(
    "case",
    [pytest.param(case, id=case["id"]) for case in SUITE["cases"]],
)
def test_scientific_guard(case: dict[str, Any]) -> None:
    found = violations(case)
    assert not found, f"{case['id']} {case['title']}: " + "; ".join(found)


def test_case_file_is_well_formed() -> None:
    ids = [case["id"] for case in SUITE["cases"]]
    assert len(ids) == len(set(ids))
    for case in SUITE["cases"]:
        assert case["kind"] == "guard", case["id"]
        assert case["check"] in {"compare", "validate", "resolve"}, case["id"]
        for key in ("title", "why", "conditions", "decision", "expect", "report_finding"):
            assert case.get(key), (case["id"], key)
        assert (FIXTURES / f"{case['profile']}.json").is_file(), case["id"]
