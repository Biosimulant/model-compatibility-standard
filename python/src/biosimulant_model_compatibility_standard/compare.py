"""Compare two port contracts using the rules in the spec bundle."""

from __future__ import annotations

from typing import Any, Iterable

from .bundle import Bundle, get_bundle
from .canonical import digest
from .constants import STANDARD
from .pointers import MISSING, get_pointer


def _finding(dimension: str, state: str, code: str, explanation: str, *, evidence: Any = None) -> dict[str, Any]:
    value = {
        "dimension": dimension,
        "state": state,
        "severity": "error" if state == "INCOMPATIBLE" else "info",
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
        same_labels = len(source) == len(target) and sorted(source) == sorted(target)
        # A reordering loses nothing; labels already in the same order need no conversion.
        return same_labels, (None if source == target else "none")
    if operator == "range":
        return source["minimum"] >= target["minimum"] and source["maximum"] <= target["maximum"], None
    if operator == "unit-convertible":
        if source == target:
            return True, None
        conversion = _unit_conversion(source, target, bundle)
        return conversion is not None, conversion and conversion["loss"]
    if operator == "context-compatible":
        return source == target or target in (None, "any", "unspecified"), None
    # pattern, term-subsumes and the mapping operators aren't implemented yet. They need
    # pinned ontology or mapping data, so the comparison reports UNKNOWN for them.
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
        findings = [_finding("contract", "UNKNOWN", "BMCS_CONTRACT_NOT_DECLARED", "One or both ports have no compatibility contract.")]
    elif digest(source_contract) == digest(target_contract):
        status = "EXACT"
        findings = [_finding("contract", "EXACT", "BMCS_EXACT_CONTRACT", "The two contracts are identical.")]
    else:
        refs = list(target_profile_refs) or list(source_profile_refs)
        rules = _rules(refs, active) if refs else []
        findings = []
        unknown = False
        incompatible = False
        conversion: str | None = None
        if not rules:
            # No profile rules apply, so compare every field the target declares, one level deep.
            # A field missing on either side gives UNKNOWN; a different value gives INCOMPATIBLE.
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
                findings.append(_finding(dimension, "UNKNOWN", "BMCS_REQUIRED_EVIDENCE_MISSING", f"{rule['target']} is missing from the source or target contract."))
                continue
            compatible, transformation = _evaluate(rule["operator"], left, right, active)
            if transformation == "unsupported":
                unknown = True
                findings.append(_finding(dimension, "UNKNOWN", "BMCS_OPERATOR_REQUIRES_SNAPSHOT", f"The '{rule['operator']}' check isn't available yet, so {rule['target']} can't be compared."))
            elif compatible:
                if transformation:
                    conversion = transformation
                findings.append(_finding(dimension, "DIRECT_COMPATIBLE", "BMCS_RULE_SATISFIED", f"{rule['target']}: '{rule['operator']}' check passed."))
            else:
                incompatible = True
                findings.append(_finding(dimension, "INCOMPATIBLE", rule.get("reason_code", "BMCS_VALUE_MISMATCH"), f"{rule['target']}: '{rule['operator']}' check failed.", evidence={"source": left, "target": right}))
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
        "standard": STANDARD,
        "bundle_sha256": active.digest,
        "source": {
            "contract_digest": digest(source_contract) if source_contract is not None else None,
            "profile_refs": sorted(set(source_profile_refs)),
        },
        "target": {
            "contract_digest": digest(target_contract) if target_contract is not None else None,
            "profile_refs": sorted(set(target_profile_refs)),
        },
        "status": status,
        "policy_decision": "APPROVAL_REQUIRED" if status in {"LOSSY_CONVERSION_REQUIRES_APPROVAL", "INFERENCE_MODEL_REQUIRED", "CONDITIONAL"} else ("BLOCK" if status in {"INCOMPATIBLE", "UNKNOWN"} else "ALLOW"),
        "findings": findings,
    }
    report["digest"] = digest(report)
    return report
