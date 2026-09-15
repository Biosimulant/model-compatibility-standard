"""Measure what the comparison engine actually answers, across all 650 profiles.

The remediation plan's main risk is over-requirement: fixes that turn real couplings into UNKNOWN.
This script runs a fixed set of scenarios against every profile and tallies the statuses, so the
effect of a change is a number rather than an opinion.

    python3 scripts/compatibility_census.py                        # write a snapshot
    python3 scripts/compatibility_census.py --baseline <file>      # compare against an earlier one

Each scenario starts from a profile's own generated positive fixture and changes one thing, so the
census measures the profile's rules rather than the fixture's content.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python" / "src"))

from biosimulant_model_compatibility_standard import compare_contracts, get_bundle  # noqa: E402

FIXTURES = ROOT / "spec" / "v0.1" / "fixtures" / "profiles"
PROFILES = ROOT / "spec" / "v0.1" / "profiles"
OUT_DIR = ROOT / "docs" / "scientific-remediation" / "measurements"

SCENARIOS = {
    "identical": "The same contract on both ports. Anything but EXACT is a bug.",
    "required-missing-source": "A required field absent from the source. Absent evidence must be UNKNOWN.",
    "required-missing-target": "The same field absent from the target instead. Must behave the same way.",
    "required-value-differs": "A required field with a different value on each side. Should be INCOMPATIBLE.",
    "unit-mismatch": "Both ports declare measurement.unit, mg against s. Different dimensions, so INCOMPATIBLE.",
    "unit-convertible": "Both ports declare measurement.unit, g against kg. Same quantity, so a lossless conversion.",
    "origin-mismatch": "Both ports declare origin.type, simulated against measured. Must not be a silent match.",
    "namespace-mismatch": "Both ports declare an identifier namespace, ensembl.gene against hgnc.symbol.",
    "species-any": "The source declares species 'any' against a specific target. Absent evidence, not contradiction.",
}


def set_path(contract: dict, path: str, value) -> None:
    parts = path.split(".")
    node = contract
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def drop_path(contract: dict, path: str) -> None:
    parts = path.split(".")
    node = contract
    for part in parts[:-1]:
        node = node.get(part, {})
        if not isinstance(node, dict):
            return
    node.pop(parts[-1], None)


def get_path(contract: dict, path: str):
    node = contract
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def other_value(value, path: str, allowed: list | None):
    if path == "biological_context.species":
        return "NCBITaxon:10090"
    if allowed:
        for candidate in allowed:
            if candidate != value:
                return candidate
    if isinstance(value, str):
        return value + "-different"
    if isinstance(value, list):
        return [*value, "different"]
    return "different"


def build(profile: dict, positive: dict, scenario: str):
    """Return (source, target) for a scenario, or None when it does not apply."""
    required = [r["path"] for r in profile.get("requirements", []) if r["level"] == "required"]
    allowed_kinds = profile.get("allowed", {}).get("representation", {}).get("kind")
    source, target = copy.deepcopy(positive), copy.deepcopy(positive)
    if scenario == "identical":
        return source, target
    if scenario in {"required-missing-source", "required-missing-target", "required-value-differs"}:
        path = next((p for p in required if p not in {"semantic.concept"}), None)
        if path is None:
            return None
        if scenario == "required-missing-source":
            drop_path(source, path)
        elif scenario == "required-missing-target":
            drop_path(target, path)
        else:
            allowed = allowed_kinds if path == "representation.kind" else None
            set_path(source, path, other_value(get_path(source, path), path, allowed))
        return source, target
    if scenario == "unit-mismatch":
        set_path(source, "measurement.unit", "mg")
        set_path(target, "measurement.unit", "s")
        return source, target
    if scenario == "unit-convertible":
        set_path(source, "measurement.unit", "g")
        set_path(target, "measurement.unit", "kg")
        return source, target
    if scenario == "origin-mismatch":
        set_path(source, "origin.type", "simulated")
        set_path(target, "origin.type", "measured")
        return source, target
    if scenario == "namespace-mismatch":
        set_path(source, "identifiers.namespace", "ensembl.gene")
        set_path(target, "identifiers.namespace", "hgnc.symbol")
        return source, target
    if scenario == "species-any":
        if "biological_context.species" not in required:
            return None
        set_path(source, "biological_context.species", "any")
        return source, target
    raise ValueError(scenario)


def census() -> dict:
    per_scenario: dict[str, Counter] = defaultdict(Counter)
    per_domain: dict[str, Counter] = defaultdict(Counter)
    totals: Counter = Counter()
    profiles_seen = 0
    for path in sorted(FIXTURES.glob("*/*.json")):
        domain, name = path.parent.name, path.stem
        fixture = json.loads(path.read_text(encoding="utf-8"))
        profile = json.loads((PROFILES / domain / name / "v0.1.json").read_text(encoding="utf-8"))
        positive = next(c for c in fixture["cases"] if c["name"] == "positive")["contract"]
        ref = fixture["profile_ref"]
        profiles_seen += 1
        for scenario in SCENARIOS:
            pair = build(profile, positive, scenario)
            if pair is None:
                per_scenario[scenario]["NOT_APPLICABLE"] += 1
                continue
            report = compare_contracts(pair[0], pair[1], source_profile_refs=[ref], target_profile_refs=[ref])
            status = report["status"]
            per_scenario[scenario][status] += 1
            per_domain[domain][status] += 1
            totals[status] += 1
    return {
        "schema_version": "0.1",
        "generated_at": dt.date.today().isoformat(),
        "bundle_sha256": get_bundle().digest,
        "profiles": profiles_seen,
        "scenarios": SCENARIOS,
        "totals": dict(totals.most_common()),
        "per_scenario": {k: dict(v.most_common()) for k, v in per_scenario.items()},
        "per_domain": {k: dict(v.most_common()) for k, v in sorted(per_domain.items())},
    }


def rate(counts: dict, status: str) -> float:
    total = sum(counts.values()) or 1
    return 100.0 * counts.get(status, 0) / total


def render(result: dict) -> str:
    lines = [f"# Compatibility census, {result['generated_at']}", ""]
    lines.append(f"{result['profiles']} profiles, {sum(result['totals'].values())} comparisons, "
                 f"bundle `{result['bundle_sha256'][:19]}...`.")
    lines.append("")
    lines.append(f"**UNKNOWN {rate(result['totals'], 'UNKNOWN'):.1f}%** &middot; "
                 f"INCOMPATIBLE {rate(result['totals'], 'INCOMPATIBLE'):.1f}% &middot; "
                 f"EXACT {rate(result['totals'], 'EXACT'):.1f}% &middot; "
                 f"DIRECT_COMPATIBLE {rate(result['totals'], 'DIRECT_COMPATIBLE'):.1f}%")
    lines += ["", "| Scenario | Statuses | What it should be |", "|---|---|---|"]
    for scenario, description in result["scenarios"].items():
        counts = result["per_scenario"].get(scenario, {})
        summary = ", ".join(f"{k} {v}" for k, v in counts.items())
        lines.append(f"| `{scenario}` | {summary} | {description} |")
    return "\n".join(lines) + "\n"


def diff(current: dict, baseline: dict) -> str:
    lines = ["", f"## Change since {baseline['generated_at']}", ""]
    for scenario in current["scenarios"]:
        now, before = current["per_scenario"].get(scenario, {}), baseline["per_scenario"].get(scenario, {})
        if now == before:
            continue
        moved = sorted(set(now) | set(before))
        lines.append(f"- `{scenario}`: " + ", ".join(
            f"{status} {before.get(status, 0)} -> {now.get(status, 0)}" for status in moved
            if before.get(status, 0) != now.get(status, 0)))
    if len(lines) == 3:
        lines.append("- no change")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, help="an earlier census JSON to compare against")
    parser.add_argument("--out", type=Path, default=OUT_DIR, help="output directory")
    args = parser.parse_args()
    result = census()
    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"census-{result['generated_at']}"
    (args.out / f"{stem}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    report = render(result)
    if args.baseline:
        report += diff(result, json.loads(args.baseline.read_text(encoding="utf-8")))
    (args.out / f"{stem}.md").write_text(report, encoding="utf-8")
    print(report)
    print(f"written: {args.out / (stem + '.json')}")


if __name__ == "__main__":
    main()
