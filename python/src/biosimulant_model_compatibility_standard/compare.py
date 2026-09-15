"""Compare two port contracts using the rules in the spec bundle."""

from __future__ import annotations

import re
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


def _verified_snapshots(values: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for snapshot in values:
        ref = snapshot.get("ref")
        declared = snapshot.get("sha256")
        unsigned = {key: value for key, value in snapshot.items() if key != "sha256"}
        if isinstance(ref, str) and declared == digest(unsigned):
            result[ref] = snapshot
    return result


def _snapshot_for(rule: dict[str, Any], snapshots: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    parameters = rule.get("parameters", {})
    ref = parameters.get("snapshot_ref")
    expected = parameters.get("snapshot_sha256")
    snapshot = snapshots.get(ref) if isinstance(ref, str) else None
    if snapshot is None or (expected is not None and snapshot.get("sha256") != expected):
        return None
    return snapshot


def _term_equivalent(source: Any, target: Any, snapshot: dict[str, Any]) -> bool:
    if source == target:
        return True
    graph: dict[str, set[str]] = {}
    for pair in snapshot.get("equivalences", []):
        if isinstance(pair, list) and len(pair) == 2 and all(isinstance(item, str) for item in pair):
            graph.setdefault(pair[0], set()).add(pair[1])
            graph.setdefault(pair[1], set()).add(pair[0])
    pending = [source] if isinstance(source, str) else []
    seen: set[str] = set()
    while pending:
        current = pending.pop()
        if current == target:
            return True
        if current in seen:
            continue
        seen.add(current)
        pending.extend(sorted(graph.get(current, set()) - seen))
    return False


def _term_subsumes(source: Any, target: Any, snapshot: dict[str, Any]) -> bool:
    """Return true when the source is the target term or one of its descendants."""

    if source == target:
        return True
    parents: dict[str, set[str]] = {}
    for edge in snapshot.get("subsumptions", []):
        if isinstance(edge, dict) and isinstance(edge.get("child"), str) and isinstance(edge.get("parent"), str):
            parents.setdefault(edge["child"], set()).add(edge["parent"])
    pending = [source] if isinstance(source, str) else []
    seen: set[str] = set()
    while pending:
        current = pending.pop()
        if current == target:
            return True
        if current in seen:
            continue
        seen.add(current)
        pending.extend(sorted(parents.get(current, set()) - seen))
    return False


def _mapping_matches(source: Any, target: Any, snapshot: dict[str, Any], *, bijective: bool) -> bool:
    if not isinstance(source, list) or not isinstance(target, list):
        return False
    target_values = {str(value) for value in target}
    mapped: list[str] = []
    table: dict[str, list[str]] = {}
    for entry in snapshot.get("mappings", []):
        if not isinstance(entry, dict) or "source" not in entry:
            continue
        raw_targets = entry.get("targets", [entry.get("target")])
        if isinstance(raw_targets, list):
            table[str(entry["source"])] = [str(value) for value in raw_targets if value is not None]
    for value in source:
        candidates = [item for item in table.get(str(value), []) if item in target_values]
        if not candidates or (bijective and len(candidates) != 1):
            return False
        mapped.extend(candidates)
    return not bijective or (len(mapped) == len(set(mapped)) and set(mapped) == target_values)


def _safe_pattern(pattern: Any, value: Any) -> tuple[bool, str | None]:
    if not isinstance(pattern, str) or not isinstance(value, str):
        return False, "invalid"
    if len(pattern) > 256 or len(value) > 4096:
        return False, "invalid"
    # Keep the common Python/ECMAScript subset and exclude constructs associated with
    # expensive backtracking or engine-specific behavior.
    if "(?" in pattern or re.search(r"\\[1-9]", pattern) or re.search(r"[+*?][+*?]", pattern):
        return False, "invalid"
    try:
        return re.fullmatch(pattern, value, flags=re.ASCII) is not None, None
    except re.error:
        return False, "invalid"


def _evaluate(
    rule: dict[str, Any],
    source: Any,
    target: Any,
    bundle: Bundle,
    *,
    ontology_snapshots: dict[str, dict[str, Any]],
    mapping_snapshots: dict[str, dict[str, Any]],
) -> tuple[bool, str | None]:
    operator = rule["operator"]
    if operator in {"equal", "digest-equal", "labels-equal"}:
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
        if not isinstance(source, dict) or not isinstance(target, dict):
            return False, "invalid"
        try:
            return source["minimum"] >= target["minimum"] and source["maximum"] <= target["maximum"], None
        except (KeyError, TypeError):
            return False, "invalid"
    if operator == "pattern":
        pattern = rule.get("parameters", {}).get("pattern", target)
        return _safe_pattern(pattern, source)
    if operator == "same-dimension":
        if source == target:
            return True, None
        if isinstance(source, str) and isinstance(target, str):
            return (_unit_conversion(source, target, bundle) is not None or _unit_conversion(target, source, bundle) is not None), None
        if isinstance(source, dict) and isinstance(target, dict):
            left = source.get("dimension")
            right = target.get("dimension")
            if left is not None and right is not None:
                return left == right, None
        return False, "invalid"
    if operator == "unit-convertible":
        if source == target:
            return True, None
        conversion = _unit_conversion(source, target, bundle)
        return conversion is not None, conversion and conversion["loss"]
    if operator == "context-compatible":
        return source == target or target in (None, "any", "unspecified"), None
    if operator in {"term-equivalent", "term-subsumes"}:
        if source == target:
            return True, None
        snapshot = _snapshot_for(rule, ontology_snapshots)
        if snapshot is None:
            return False, "unsupported"
        return (
            _term_equivalent(source, target, snapshot)
            if operator == "term-equivalent"
            else _term_subsumes(source, target, snapshot)
        ), None
    if operator in {"mapping-total", "mapping-bijective"}:
        snapshot = _snapshot_for(rule, mapping_snapshots)
        if snapshot is None:
            return False, "unsupported"
        return _mapping_matches(source, target, snapshot, bijective=operator == "mapping-bijective"), None
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
    ontology_snapshots: Iterable[dict[str, Any]] = (),
    mapping_snapshots: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    active = bundle or get_bundle()
    ontology_index = _verified_snapshots(ontology_snapshots)
    mapping_index = _verified_snapshots(mapping_snapshots)
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
            compatible, transformation = _evaluate(
                rule,
                left,
                right,
                active,
                ontology_snapshots=ontology_index,
                mapping_snapshots=mapping_index,
            )
            if transformation == "unsupported":
                unknown = True
                findings.append(_finding(dimension, "UNKNOWN", "BMCS_OPERATOR_REQUIRES_SNAPSHOT", f"The '{rule['operator']}' check isn't available yet, so {rule['target']} can't be compared."))
            elif transformation == "invalid":
                unknown = True
                findings.append(_finding(dimension, "UNKNOWN", "BMCS_OPERATOR_INPUT_INVALID", f"The '{rule['operator']}' check received invalid or unsafe input at {rule['target']}."))
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
