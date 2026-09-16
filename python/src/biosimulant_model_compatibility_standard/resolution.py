"""Find the cheapest chain of reviewed adapters or inference models from a source contract to a target."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from itertools import count
from typing import Any, Iterable

from .bundle import Bundle, get_bundle
from .canonical import digest
from .compare import _evaluate, _verified_snapshots, compare_contracts
from .constants import STANDARD
from .pointers import MISSING, get_pointer
from .validation import validate_object

_LOSS_RANK = {"none": 0, "bounded": 1, "lossy": 2}


@dataclass(frozen=True)
class ResolutionLimits:
    max_transformations: int = 8
    max_inferences: int = 2
    max_examined_edges: int = 10_000


def _capability_kind(capability: dict[str, Any]) -> str:
    return "inference" if "inferred_modality" in capability else "adapter"


def _cost(path: tuple[dict[str, Any], ...]) -> tuple[Any, ...]:
    inference_count = sum(_capability_kind(item) == "inference" for item in path)
    loss_rank = max(
        (_LOSS_RANK.get(str(item.get("information_loss", "lossy")), 2) for item in path),
        default=0,
    )
    loss_score = sum(float(item.get("loss_score", 0)) for item in path)
    execution_cost = sum(float(item.get("execution_cost", 0)) for item in path)
    identifiers = tuple(f"{item['ref']}#{item['sha256']}" for item in path)
    return (
        inference_count,
        loss_rank,
        loss_score,
        len(path),
        execution_cost,
        identifiers,
    )


_POLICY_STRENGTH = {"allow": 0, "approval": 1, "block": 2}
_PUBLISHED_TO_DECISION = {"allow": "ALLOW", "approval": "APPROVAL_REQUIRED", "block": "BLOCK"}
_DECISIONS = {"ALLOW", "APPROVAL_REQUIRED", "BLOCK"}


def _declared_policy(contract: dict[str, Any] | None, bundle: Bundle) -> dict[str, Any]:
    """The transformation policy published by the target contract's own profiles.

    Every profile publishes `transformation_policy`, and until now nothing read it: a profile that
    declared `lossy: block` still produced APPROVAL_REQUIRED, because the only policy consulted was
    the one a caller passed in by hand. Where a contract names several profiles the
    most restrictive setting wins, since a profile that blocks a path is not overruled by one that
    permits it.
    """

    if not isinstance(contract, dict):
        return {}
    refs = contract.get("profile_refs")
    if not isinstance(refs, list):
        return {}
    combined: dict[str, Any] = {}
    for ref in sorted({value for value in refs if isinstance(value, str)}):
        try:
            profile = bundle.profile(ref)
        except Exception:
            continue
        policy = profile.get("transformation_policy")
        if not isinstance(policy, dict):
            continue
        for key, value in policy.items():
            current = combined.get(key)
            if current is None or _POLICY_STRENGTH.get(str(value), 0) > _POLICY_STRENGTH.get(str(current), 0):
                combined[key] = value
    return {key: _PUBLISHED_TO_DECISION.get(str(value), value) for key, value in combined.items()}


def _policy_decision(status: str, policy: dict[str, Any]) -> str:
    key = {
        "UNKNOWN": "unknown",
        "CONDITIONAL": "conditional",
        "LOSSLESS_CONVERSION_AVAILABLE": "lossless",
        "LOSSY_CONVERSION_REQUIRES_APPROVAL": "lossy",
        "INFERENCE_MODEL_REQUIRED": "inference",
    }.get(status)
    # Only a value already in the decision vocabulary overrides the default mapping, which is what
    # the TypeScript engine does. Anything else falls through rather than becoming the decision.
    if key is not None and str(policy.get(key)) in _DECISIONS:
        return str(policy[key])
    if status in {"EXACT", "DIRECT_COMPATIBLE", "LOSSLESS_CONVERSION_AVAILABLE"}:
        return "ALLOW"
    if status in {
        "LOSSY_CONVERSION_REQUIRES_APPROVAL",
        "INFERENCE_MODEL_REQUIRED",
        "CONDITIONAL",
    }:
        return "APPROVAL_REQUIRED"
    return "BLOCK"


def _technical_status(path: tuple[dict[str, Any], ...]) -> str:
    if any(_capability_kind(item) == "inference" for item in path):
        return "INFERENCE_MODEL_REQUIRED"
    if any(item.get("information_loss") in {"bounded", "lossy"} for item in path):
        return "LOSSY_CONVERSION_REQUIRES_APPROVAL"
    return "LOSSLESS_CONVERSION_AVAILABLE"


def _plan(
    source: dict[str, Any],
    target: dict[str, Any],
    path: tuple[dict[str, Any], ...],
    *,
    policy: dict[str, Any],
    bundle: Bundle,
    ontology_snapshots: tuple[dict[str, Any], ...],
    mapping_snapshots: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    source_digest = digest(source)
    target_digest = digest(target)
    status = "DIRECT_COMPATIBLE" if not path else _technical_status(path)
    nodes: list[dict[str, Any]] = [
        {"id": "source", "kind": "contract", "contract_digest": source_digest}
    ]
    edges: list[dict[str, Any]] = []
    previous = "source"
    for index, capability in enumerate(path):
        node_id = f"{_capability_kind(capability)}-{index + 1}"
        nodes.append(
            {
                "id": node_id,
                "kind": _capability_kind(capability),
                "ref": capability["ref"],
                "sha256": capability["sha256"],
                "information_loss": capability.get("information_loss", "lossy"),
            }
        )
        edges.append({"from": previous, "to": node_id})
        previous = node_id
    nodes.append({"id": "target", "kind": "contract", "contract_digest": target_digest})
    edges.append({"from": previous, "to": "target"})

    terminal_report = compare_contracts(
        path[-1]["target"] if path else source,
        target,
        bundle=bundle,
        ontology_snapshots=ontology_snapshots,
        mapping_snapshots=mapping_snapshots,
    )
    snapshot_references = [
        {"kind": kind, "ref": item["ref"], "sha256": item["sha256"]}
        for kind, values in (
            ("ontology_snapshot", ontology_snapshots),
            ("mapping_snapshot", mapping_snapshots),
        )
        for item in values
    ]
    partial = {
        "schema_version": "0.1",
        "standard": STANDARD,
        "bundle_sha256": bundle.digest,
        # The status the chain itself carries. reports[] holds the terminal comparison, which is
        # EXACT whenever the last adapter lands exactly on the target, so without this a reader
        # cannot tell a lossy chain from an inference one or from a direct match.
        "technical_status": status,
        "nodes": nodes,
        "edges": edges,
        "reports": [{"digest": terminal_report["digest"], "status": terminal_report["status"]}],
        "policy": {**policy, "decision": _policy_decision(status, policy)},
        "approvals": [],
        "immutable_references": [
            {"ref": item["ref"], "sha256": item["sha256"]} for item in path
        ]
        + snapshot_references,
    }
    return {**partial, "digest": digest(partial)}


def resolve_contracts(
    source: dict[str, Any] | None,
    target: dict[str, Any] | None,
    capabilities: Iterable[dict[str, Any]] = (),
    *,
    policy: dict[str, Any] | None = None,
    limits: ResolutionLimits | None = None,
    bundle: Bundle | None = None,
    ontology_snapshots: Iterable[dict[str, Any]] = (),
    mapping_snapshots: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Plan how to connect a source contract to a target.

    Returns RESOLVED with a plan, AMBIGUOUS when several plans cost the same, or
    UNRESOLVED with a reason. Only capabilities with state "reviewed" are used.
    """

    active = bundle or get_bundle()
    ontology_values = tuple(
        value for _, value in sorted(_verified_snapshots(ontology_snapshots).items())
    )
    mapping_values = tuple(
        value for _, value in sorted(_verified_snapshots(mapping_snapshots).items())
    )
    ontology_index = _verified_snapshots(ontology_values)
    mapping_index = _verified_snapshots(mapping_values)
    # A policy the caller supplies wins; otherwise use the one the target's profiles publish.
    active_policy = dict(policy) if policy else _declared_policy(target, active)
    direct = compare_contracts(
        source,
        target,
        bundle=active,
        ontology_snapshots=ontology_values,
        mapping_snapshots=mapping_values,
    )
    if source is None or target is None:
        return {"resolution": "UNRESOLVED", "report": direct, "reason": "UNKNOWN_CONTRACT"}
    if direct["status"] in {"EXACT", "DIRECT_COMPATIBLE"}:
        plan = _plan(
            source,
            target,
            (),
            policy=active_policy,
            bundle=active,
            ontology_snapshots=ontology_values,
            mapping_snapshots=mapping_values,
        )
        return {"resolution": "RESOLVED", "report": direct, "plan": plan}
    if direct["status"] == "INCOMPATIBLE" and not capabilities:
        return {"resolution": "UNRESOLVED", "report": direct, "reason": "NO_CAPABILITY_PATH"}

    reviewed: list[dict[str, Any]] = []
    for capability in capabilities:
        schema = (
            "inference-capability.schema.json"
            if _capability_kind(capability) == "inference"
            else "adapter-capability.schema.json"
        )
        findings = validate_object(capability, schema, bundle=active)
        if findings:
            raise ValueError(
                f"Invalid capability {capability.get('ref', '<unknown>')}: "
                + "; ".join(item.message for item in findings)
            )
        if capability.get("state") == "reviewed":
            reviewed.append(capability)

    by_source: dict[str, list[dict[str, Any]]] = {}
    for capability in reviewed:
        by_source.setdefault(digest(capability["source"]), []).append(capability)
    for values in by_source.values():
        values.sort(key=lambda item: (item["ref"], item["sha256"]))

    bounds = limits or ResolutionLimits()
    serial = count()
    queue: list[tuple[tuple[Any, ...], int, dict[str, Any], tuple[dict[str, Any], ...]]] = []
    heapq.heappush(queue, (_cost(()), next(serial), source, ()))
    best: dict[str, tuple[Any, ...]] = {digest(source): _cost(())[:-1]}
    candidates: list[tuple[tuple[Any, ...], tuple[dict[str, Any], ...]]] = []
    examined = 0

    while queue and examined < bounds.max_examined_edges:
        path_cost, _, contract, path = heapq.heappop(queue)
        terminal = compare_contracts(
            contract,
            target,
            bundle=active,
            ontology_snapshots=ontology_values,
            mapping_snapshots=mapping_values,
        )
        if terminal["status"] in {"EXACT", "DIRECT_COMPATIBLE"}:
            candidates.append((path_cost, path))
            continue
        if len(path) >= bounds.max_transformations:
            continue
        for capability in by_source.get(digest(contract), []):
            examined += 1
            if examined > bounds.max_examined_edges:
                break
            wrapped_current = {"contract": contract}
            wrapped_declared = {"contract": capability["source"]}
            preconditions_met = True
            for rule in capability.get("preconditions", []):
                left = get_pointer(wrapped_current, rule["source"])
                right = get_pointer(wrapped_declared, rule["target"])
                if left is MISSING or right is MISSING:
                    if rule.get("missing", "unknown") != "ignore":
                        preconditions_met = False
                        break
                    continue
                compatible, result_kind = _evaluate(
                    rule,
                    left,
                    right,
                    active,
                    ontology_snapshots=ontology_index,
                    mapping_snapshots=mapping_index,
                )
                if not compatible or result_kind in {"invalid", "unsupported"}:
                    preconditions_met = False
                    break
            if not preconditions_met:
                continue
            new_path = (*path, capability)
            if sum(_capability_kind(item) == "inference" for item in new_path) > bounds.max_inferences:
                continue
            next_contract = capability["target"]
            next_digest = digest(next_contract)
            new_cost = _cost(new_path)
            if next_digest in {digest(item["source"]) for item in path}:
                continue
            semantic_cost = new_cost[:-1]
            if next_digest in best and best[next_digest] < semantic_cost:
                continue
            best[next_digest] = semantic_cost
            heapq.heappush(queue, (new_cost, next(serial), next_contract, new_path))

    if not candidates:
        reason = "SEARCH_LIMIT_EXCEEDED" if examined >= bounds.max_examined_edges else "NO_CAPABILITY_PATH"
        return {"resolution": "UNRESOLVED", "report": direct, "reason": reason}
    candidates.sort(key=lambda item: item[0])
    best_cost = candidates[0][0][:-1]
    equal = [path for cost_value, path in candidates if cost_value[:-1] == best_cost]
    plans = [
        _plan(
            source,
            target,
            path,
            policy=active_policy,
            bundle=active,
            ontology_snapshots=ontology_values,
            mapping_snapshots=mapping_values,
        )
        for path in equal
    ]
    if len(plans) > 1:
        return {
            "resolution": "AMBIGUOUS",
            "report": direct,
            "candidate_plans": plans,
            "reason": "EQUAL_COST_SCIENTIFIC_PATHS",
        }
    return {"resolution": "RESOLVED", "report": direct, "plan": plans[0]}
