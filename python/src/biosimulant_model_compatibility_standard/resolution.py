"""Find the cheapest chain of reviewed adapters or inference models from a source contract to a target."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from itertools import count
from typing import Any, Iterable

from .bundle import Bundle, get_bundle
from .canonical import digest
from .compare import compare_contracts
from .constants import STANDARD
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


def _policy_decision(status: str, policy: dict[str, Any]) -> str:
    key = {
        "UNKNOWN": "unknown",
        "CONDITIONAL": "conditional",
        "LOSSLESS_CONVERSION_AVAILABLE": "lossless",
        "LOSSY_CONVERSION_REQUIRES_APPROVAL": "lossy",
        "INFERENCE_MODEL_REQUIRED": "inference",
    }.get(status)
    if key is not None and key in policy:
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
    )
    partial = {
        "schema_version": "0.1",
        "standard": STANDARD,
        "bundle_sha256": bundle.digest,
        "nodes": nodes,
        "edges": edges,
        "reports": [{"digest": terminal_report["digest"], "status": terminal_report["status"]}],
        "policy": {**policy, "decision": _policy_decision(status, policy)},
        "approvals": [],
        "immutable_references": [
            {"ref": item["ref"], "sha256": item["sha256"]} for item in path
        ],
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
) -> dict[str, Any]:
    """Plan how to connect a source contract to a target.

    Returns RESOLVED with a plan, AMBIGUOUS when several plans cost the same, or
    UNRESOLVED with a reason. Only capabilities with state "reviewed" are used.
    """

    active = bundle or get_bundle()
    active_policy = dict(policy or {})
    direct = compare_contracts(source, target, bundle=active)
    if source is None or target is None:
        return {"resolution": "UNRESOLVED", "report": direct, "reason": "UNKNOWN_CONTRACT"}
    if direct["status"] in {"EXACT", "DIRECT_COMPATIBLE"}:
        plan = _plan(source, target, (), policy=active_policy, bundle=active)
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
        terminal = compare_contracts(contract, target, bundle=active)
        if terminal["status"] in {"EXACT", "DIRECT_COMPATIBLE"}:
            candidates.append((path_cost, path))
            continue
        if len(path) >= bounds.max_transformations:
            continue
        for capability in by_source.get(digest(contract), []):
            examined += 1
            if examined > bounds.max_examined_edges:
                break
            if capability.get("preconditions"):
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
    plans = [_plan(source, target, path, policy=active_policy, bundle=active) for path in equal]
    if len(plans) > 1:
        return {
            "resolution": "AMBIGUOUS",
            "report": direct,
            "candidate_plans": plans,
            "reason": "EQUAL_COST_SCIENTIFIC_PATHS",
        }
    return {"resolution": "RESOLVED", "report": direct, "plan": plans[0]}
