# Measurements

The remediation plan's stated risk is over-requirement: fixes that turn real couplings into
UNKNOWN. `scripts/compatibility_census.py` makes that measurable. It runs nine scenarios against
every profile and tallies what the engine answers, so the effect of a change is a number.

```bash
python3 scripts/compatibility_census.py
python3 scripts/compatibility_census.py --baseline docs/scientific-remediation/measurements/census-2026-09-15.json
```

## Baseline, 15 September 2026

5,775 comparisons over 650 profiles, before any remediation.

| Scenario | What the engine answers | What it should answer |
|---|---|---|
| `identical` | EXACT 650 | Correct |
| `required-missing-source` | UNKNOWN 650 | Correct |
| `required-missing-target` | UNKNOWN 650 | Correct, and until now untested (guard BMCS-SCI-107) |
| `required-value-differs` | INCOMPATIBLE 650 | Correct |
| `unit-mismatch` (mg vs s) | DIRECT_COMPATIBLE 526, INCOMPATIBLE 124 | INCOMPATIBLE 650 |
| `unit-convertible` (g vs kg) | DIRECT_COMPATIBLE 526, INCOMPATIBLE 124 | A lossless conversion, 650 |
| `origin-mismatch` (simulated vs measured) | DIRECT_COMPATIBLE 650 | Never a silent match |
| `namespace-mismatch` (Ensembl vs HGNC) | DIRECT_COMPATIBLE 552, INCOMPATIBLE 98 | Mapping required, or UNKNOWN |
| `species-any` | INCOMPATIBLE 575 | Not a contradiction |

Two patterns run through this, and they are the same two defects seen from a different angle.

**The 526/124 split is decision D2.** The 124 profiles that require `measurement.unit` compare it;
the other 526 ignore it even when both ports declare one. So `mg` against `s` passes for 526
profiles, and the same split appears for identifiers at 552/98.

**Where units are compared, they are compared wrongly.** For those 124 profiles, `g` against `kg`
is INCOMPATIBLE — the same quantity, refused — while for the other 526 it is a silent pass. Both
halves are wrong, in opposite directions. That is decision D1.

`origin-mismatch` is unanimous: all 650 profiles let a simulated value satisfy a port asking for
measured data.

## How to read a change

After each fix, re-run with `--baseline` pointing at the previous snapshot. The diff lists the
statuses that moved. Two things to watch:

- **UNKNOWN should rise, but not everywhere.** Requiring more context turns some silent passes into
  honest UNKNOWNs. If it climbs toward the whole corpus, the requirements went too far.
- **`identical` must stay EXACT 650.** If it moves, a fix broke the trivial case.

The scenarios are deliberately synthetic. A census over real manifests would be better evidence and
needs a corpus that does not exist yet; this is the version that can run today.
