"""Summarise, per domain, what the remediation changed in the generated profiles.

Phase 3 of the remediation plan asks for "a per-domain diff of what changed and why". This reads the
profile documents at a baseline commit and in the working tree and reports, for each domain, what
moved.

It reports what changed, never whether the new value is right. A domain's required-item count
falling, or an operator appearing, says nothing about whether the profile now describes the science
correctly: that judgement belongs to the domain review waves.

    python scripts/domain_diff.py --baseline f7480a7 --out docs/.../domain-diff.md
"""

from __future__ import annotations

import argparse
import collections
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANY_JSON_TYPE = ["string", "number", "integer", "boolean", "array", "object", "null"]


def _extract(ref: str, destination: Path) -> Path:
    """Unpack the generated profiles at `ref` into `destination`."""

    archive = subprocess.run(
        ["git", "archive", ref, "spec/v0.1/profiles"],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout
    subprocess.run(["tar", "-x", "-C", str(destination)], input=archive, check=True)
    return destination / "spec" / "v0.1" / "profiles"


def _read(profile_root: Path) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for path in sorted(profile_root.glob("*/*/v0.1.json")):
        profile = json.loads(path.read_text())
        requirements = profile.get("requirements", [])
        required = [item for item in requirements if item.get("level") == "required"]
        result[f"{profile['domain']}/{profile['name']}"] = {
            "required": len(required),
            "operators": collections.Counter(rule["operator"] for rule in profile.get("comparison_rules", [])),
            "kinds": sorted(((profile.get("allowed") or {}).get("representation") or {}).get("kind") or []),
            "concept": ((profile.get("fixed") or {}).get("semantic") or {}).get("concept"),
            # A schema accepting every JSON type constrains nothing, which is what the pre-review
            # found across the catalogue.
            "untyped": sum(1 for item in requirements if item.get("schema", {}).get("type") == ANY_JSON_TYPE),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, help="git ref to compare against")
    parser.add_argument("--out", required=True, help="markdown file to write")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        before = _read(_extract(args.baseline, Path(tmp)))
    after = _read(ROOT / "spec" / "v0.1" / "profiles")

    domains = sorted({key.split("/")[0] for key in set(before) | set(after)})
    lines = [
        "# What the remediation changed, by domain",
        "",
        f"Baseline: `{args.baseline}`, the last commit before the foundations landed. Compared against",
        "the regenerated `spec/v0.1` in the working tree.",
        "",
        "This is a mechanical diff of the generated profile documents. It reports what moved, never",
        "whether the new value is scientifically right — a required-item count falling, or an operator",
        "appearing, says nothing about whether the profile now describes the science correctly. That",
        "judgement belongs to the domain review waves, which is why this table is not an approval.",
        "",
        "| Domain | Profiles | Required items | Operators added | Gained a fixed concept | Gained a kind constraint | Untyped schemas |",
        "|---|---|---|---|---|---|---|",
    ]
    totals = collections.Counter()
    for domain in domains:
        keys = sorted(key for key in set(before) | set(after) if key.split("/")[0] == domain)
        required_before = sum(before[key]["required"] for key in keys if key in before)
        required_after = sum(after[key]["required"] for key in keys if key in after)
        untyped_before = sum(before[key]["untyped"] for key in keys if key in before)
        untyped_after = sum(after[key]["untyped"] for key in keys if key in after)
        ops_before: collections.Counter = collections.Counter()
        ops_after: collections.Counter = collections.Counter()
        gained_concept = gained_kinds = 0
        for key in keys:
            if key in before:
                ops_before.update(before[key]["operators"])
            if key in after:
                ops_after.update(after[key]["operators"])
            if key in before and key in after:
                if not before[key]["concept"] and after[key]["concept"]:
                    gained_concept += 1
                if not before[key]["kinds"] and after[key]["kinds"]:
                    gained_kinds += 1
        added = sorted(set(ops_after) - set(ops_before))
        totals.update({"profiles": len(keys), "concept": gained_concept, "kinds": gained_kinds,
                       "untyped_before": untyped_before, "untyped_after": untyped_after})
        lines.append(
            f"| {domain} | {len(keys)} | {required_before} → {required_after} | "
            f"{', '.join(added) or '—'} | {gained_concept} | {gained_kinds} | "
            f"{untyped_before} → {untyped_after} |"
        )

    lines += [
        "",
        "## What the columns mean",
        "",
        "- **Required items** — how many fields each domain's profiles oblige a port to declare.",
        "  Most domains fall, because `semantic.subject` stopped being a required, compared field",
        "  (D4) and because a profile that declares no measurement no longer requires measurement",
        "  fields. Imaging rises, because profiles that declare axes now require each axis to name",
        "  itself (D9).",
        "- **Operators added** — comparison operators that appear where the baseline had none.",
        "- **Gained a fixed concept** — the baseline fixed no concept at all, so its `semantic.concept`",
        "  rule compared two values that nothing constrained. Every profile now fixes a",
        "  version-independent term (D3).",
        "- **Gained a kind constraint** — the baseline allowed any representation kind for every",
        "  profile. Each now publishes the kinds its meaning admits, though ~500 of those sets are",
        "  still wider than the science warrants and narrowing them is review work (D6).",
        "- **Untyped schemas** — requirements whose value schema accepted every JSON type, and so",
        "  constrained nothing. This is the change the pre-review asked for most directly.",
        "",
        f"Across all {totals['profiles']} profiles: {totals['concept']} gained a fixed concept, "
        f"{totals['kinds']} gained a kind constraint, and requirements accepting any JSON type fell "
        f"from {totals['untyped_before']} to {totals['untyped_after']}.",
        "",
        "## How to reproduce",
        "",
        "```bash",
        f"python scripts/domain_diff.py --baseline {args.baseline} --out {args.out}",
        "```",
        "",
    ]
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print(f"wrote {out} covering {len(domains)} domains")


if __name__ == "__main__":
    main()
