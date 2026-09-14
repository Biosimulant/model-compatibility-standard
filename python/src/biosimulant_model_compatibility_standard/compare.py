"""Data-driven, deterministic comparison of two port contracts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from .bundle import Bundle, get_bundle
from .canonical import digest
from .pointers import MISSING, get_pointer


def _finding(dimension: str, state: str, code: str, explanation: str, *, evidence: Any = None) -> dict[str, Any]:
    value = {
        "dimension": dimension,
        "state": state,
        "severity": "error" if state == "incompatible" else "info",
        "reason_code": code,
        "explanation": explanation,
    }
    if evidence is not None:
        value["evidence"] = evidence
    return value


def _unit_conversion(source: Any, target: Any, bundle: Bundle) -> dict[str, Any] | None:
    return next(
        (entry for entry in bundle.unit_conversions if entry["from"] == source and entry["to"] == target),
        None,
    )


def _evaluate(operator: str, source: Any, target: Any, bundle: Bundle) -> tuple[bool, str | None]:
    if operator in {"equal", "digest-equal", "term-equivalent", "same-dimension", "labels-equal"}:
        return source == target, None
    if operator == "not-equal":
        return source != target, None
    if operator == "in":
        return source in target, None
    if operator == "not-in":
        return source not in target, None
    if operator == "subset":
        return set(source).issubset(set(target)), None
    if operator == "superset":
        return set(source).issuperset(set(target)), None
    if operator == "labels-permutation":
        return len(source) == len(target) and sorted(source) == sorted(target), "lossless"
    if operator == "range":
        return source["minimum"] >= target["minimum"] and source["maximum"] <= target["maximum"], None
    if operator == "unit-convertible":
        if source == target:
            return True, None
        conversion = _unit_conversion(source, target, bundle)
        return conversion is not None, conversion and conversion["loss"]
    if operator == "context-compatible":
        return source == target or target in (None, "any", "unspecified"), None
    # Mapping and ontology operators require a pinned mapping/ontology snapshot.
    return False, "unsupported"


def _rules(profile_refs: Iterable[str], bundle: Bundle) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for ref in sorted(set(profile_refs)):
        for rule in bundle.profile(ref).get("comparison_rules", []):
            key = (rule["source"], rule["target"], rule["operator"])
            if key not in seen:
                seen.add(key)
                result.append(rule)
    return result


def compare_contracts(
    source_contract: dict[str, Any] | None,
    target_contract: dict[str, Any] | None,
    *,
    source_profile_refs: Iterable[str] = (),
    target_profile_refs: Iterable[str] = (),
    bundle: Bundle | None = None,
) -> dict[str, Any]:
    active = bundle or get_bundle()
    if source_contract is None or target_contract is None:
        status = "UNKNOWN"
        findings = [_finding("contract", "unknown", "BMCS_CONTRACT_NOT_DECLARED", "Compatibility metadata is not declared on both ports.")]
    elif digest(source_contract) == digest(target_contract):
        status = "EXACT"
        findings = [_finding("contract", "compatible", "BMCS_EXACT_CONTRACT", "Canonical contract digests are identical.")]
    else:
        refs = list(target_profile_refs) or list(source_profile_refs)
        rules = _rules(refs, active) if refs else []
        findings = []
        unknown = False
        incompatible = False
        conversion: str | None = None
        if not rules:
            # Exact recursive equality on declared target leaves. This is conservative:
            # absent required evidence is UNKNOWN, an explicit contradiction is incompatible.
            rules = []
            for family, members in target_contract.items():
                if family in {"profile_refs", "extensions"} or not isinstance(members, dict):
                    continue
                for name in members:
                    rules.append({
                        "source": f"/contract/{family}/{name}",
                        "target": f"/contract/{family}/{name}",
                        "operator": "unit-convertible" if family == "measurement" and name in {"unit", "units"} else "equal",
                        "missing": "unknown",
                        "reason_code": "BMCS_VALUE_MISMATCH",
                    })
        wrapped_source = {"contract": source_contract}
        wrapped_target = {"contract": target_contract}
        for rule in rules:
            left = get_pointer(wrapped_source, rule["source"])
            right = get_pointer(wrapped_target, rule["target"])
            dimension = rule["target"].split("/")[2] if len(rule["target"].split("/")) > 2 else "contract"
            if left is MISSING or right is MISSING:
                behavior = rule.get("missing", "unknown")
                if behavior == "ignore":
                    continue
                unknown = True
                findings.append(_finding(dimension, "unknown", "BMCS_REQUIRED_EVIDENCE_MISSING", f"Evidence is missing for {rule['target']}."))
                continue
            compatible, transformation = _evaluate(rule["operator"], left, right, active)
            if transformation == "unsupported":
                unknown = True
                findings.append(_finding(dimension, "unknown", "BMCS_OPERATOR_REQUIRES_SNAPSHOT", f"{rule['operator']} requires pinned external evidence."))
            elif compatible:
                if transformation:
                    conversion = transformation
                findings.append(_finding(dimension, "compatible", "BMCS_RULE_SATISFIED", f"{rule['operator']} comparison passed."))
            else:
                incompatible = True
                findings.append(_finding(dimension, "incompatible", rule.get("reason_code", "BMCS_VALUE_MISMATCH"), f"{rule['operator']} comparison failed.", evidence={"source": left, "target": right}))
        if incompatible:
            status = "INCOMPATIBLE"
        elif unknown:
            status = "UNKNOWN"
        elif conversion == "none":
            status = "LOSSLESS_CONVERSION_AVAILABLE"
        elif conversion:
            status = "LOSSY_CONVERSION_REQUIRES_APPROVAL"
        else:
            status = "DIRECT_COMPATIBLE"

    report = {
        "schema_version": "0.1",
        "standard": "https://biosimulant.com/standards/model-compatibility/v0.1",
        "status": status,
        "policy_decision": "APPROVAL_REQUIRED" if status in {"LOSSY_CONVERSION_REQUIRES_APPROVAL", "INFERENCE_MODEL_REQUIRED", "CONDITIONAL"} else ("BLOCK" if status in {"INCOMPATIBLE", "UNKNOWN"} else "ALLOW"),
        "source_contract_digest": digest(source_contract) if source_contract is not None else None,
        "target_contract_digest": digest(target_contract) if target_contract is not None else None,
        "findings": findings,
    }
    report["digest"] = digest(report)
    return report
