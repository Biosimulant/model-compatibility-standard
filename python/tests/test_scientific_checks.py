"""Scientific checks for v0.1: known defects and the guards that remediation must keep.

The cases live in scientific-checks/v0.1/cases.json so Python and TypeScript read the same
expectations. A defect case asserts the scientifically correct outcome and is a strict
expected failure: once the defect is fixed the test fails until the case becomes a guard.
Set BMCS_SCIENTIFIC_STRICT=1, or pass --runxfail, to run the defects as ordinary failures.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

import pytest

from biosimulant_model_compatibility_standard import compare_contracts, normalize_contract, validate_contract
from biosimulant_model_compatibility_standard.units import UnitError, parse_unit

ROOT = Path(__file__).resolve().parents[2]
SUITE = json.loads((ROOT / "scientific-checks" / "v0.1" / "cases.json").read_text(encoding="utf-8"))
FIXTURES = ROOT / "spec" / "v0.1" / "fixtures" / "profiles"
UNITS = json.loads((ROOT / "spec" / "v0.1" / "rules" / "units.json").read_text(encoding="utf-8"))


def _dimension(unit: str | None) -> tuple[int, ...] | None:
    """The dimension the standard's own UCUM table gives this unit, or None when it cannot say."""

    if not isinstance(unit, str):
        return None
    try:
        return parse_unit(unit, UNITS).dimension
    except UnitError:
        return None
STRICT = os.environ.get("BMCS_SCIENTIFIC_STRICT") == "1"
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


def _offenders(invariant: str) -> list[str]:
    offenders: list[str] = []
    for path in sorted(FIXTURES.glob("*/*.json")):
        profile = path.relative_to(FIXTURES).with_suffix("").as_posix()
        cases = _fixture_cases(path)
        unit = cases["positive"]["contract"].get("measurement", {}).get("unit")
        scale = cases["positive"]["contract"].get("measurement", {}).get("scale")
        if invariant == "conversion-within-dimension":
            case = cases.get("comparison-lossless-unit-conversion")
            if case:
                units = [case["source"]["measurement"]["unit"], case["target"]["measurement"]["unit"], unit]
                dims = {_dimension(u) for u in units}
                if None in dims or len(dims) != 1:
                    offenders.append(f"{profile}: {units[0]} -> {units[1]} for a quantity in {unit}")
        elif invariant == "contradiction-cross-dimension":
            case = cases.get("comparison-incompatible-measurement-unit")
            if case:
                left, right = case["source"]["measurement"]["unit"], case["target"]["measurement"]["unit"]
                if _dimension(left) is None or _dimension(right) is None or _dimension(left) == _dimension(right):
                    offenders.append(f"{profile}: {left} vs {right} asserted INCOMPATIBLE")
        elif invariant == "probability-scale-dimensionless":
            if scale == "probability" and _dimension(unit) != (0, 0, 0, 0, 0, 0, 0):
                offenders.append(f"{profile}: probability scale with unit {unit}")
        else:
            raise ValueError(f"unknown invariant {invariant}")
    return offenders


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
    elif case["check"] == "validate":
        errors = [f for f in validate_contract(_contract(case, "source"), [_ref(case["profile"])]) if f.severity == "error"]
        if expect.get("error_findings") == "at-least-one" and not errors:
            found.append("contract validated with no error finding")
    elif case["check"] == "fixture-invariant":
        offenders = _offenders(case["invariant"])
        if offenders:
            found.append(f"{len(offenders)} offending profiles, e.g. " + "; ".join(offenders[:3]))
    else:
        raise ValueError(f"unknown check {case['check']}")
    return found


def _params(kind: str) -> list[Any]:
    params = []
    for case in SUITE["cases"]:
        if case["kind"] != kind:
            continue
        marks = []
        if kind == "defect":
            marks.append(pytest.mark.xfail(condition=not STRICT, strict=True,
                                           reason=f"{case['id']}: known scientific defect, see decision {case['decision']}"))
        params.append(pytest.param(case, id=case["id"], marks=marks))
    return params


@pytest.mark.parametrize("case", _params("defect"))
def test_known_scientific_defect(case: dict[str, Any]) -> None:
    found = violations(case)
    assert not found, f"{case['id']} {case['title']}: " + "; ".join(found)


@pytest.mark.parametrize("case", _params("guard"))
def test_scientific_guard(case: dict[str, Any]) -> None:
    found = violations(case)
    assert not found, f"{case['id']} {case['title']}: " + "; ".join(found)


def test_case_file_is_well_formed() -> None:
    ids = [case["id"] for case in SUITE["cases"]]
    assert len(ids) == len(set(ids))
    for case in SUITE["cases"]:
        assert case["kind"] in {"defect", "guard"}, case["id"]
        assert case["check"] in {"compare", "validate", "fixture-invariant"}, case["id"]
        for key in ("title", "why", "conditions", "decision", "expect", "report_finding"):
            assert case.get(key), (case["id"], key)
        if case["kind"] == "defect":
            assert case.get("observed_at_review"), case["id"]
        if case["check"] != "fixture-invariant":
            assert (FIXTURES / f"{case['profile']}.json").is_file(), case["id"]
