# Measurements

The remediation plan's stated risk is over-requirement: fixes that turn real couplings into
UNKNOWN. `scripts/compatibility_census.py` makes that measurable. It runs nine scenarios against
every profile and tallies what the engine answers, so the effect of a change is a number.

```bash
python3 scripts/compatibility_census.py --label my-change
python3 scripts/compatibility_census.py --label my-change \
  --baseline docs/scientific-remediation/measurements/census-baseline-2026-09-15.json
```

Always pass `--label`, so a run cannot overwrite the snapshot it is being compared against.

## Before and after the foundation fixes

5,775 comparisons over 650 profiles. The baseline is the release as reviewed; the second column is
after decisions D1, D2, D5, D8, D9 and D12 were implemented.

| Scenario | Before | After |
|---|---|---|
| `identical` | EXACT 650 | EXACT 650 |
| `required-missing-source` | UNKNOWN 650 | UNKNOWN 650 |
| `required-missing-target` | UNKNOWN 650 | UNKNOWN 650 |
| `required-value-differs` | INCOMPATIBLE 650 | INCOMPATIBLE 650 |
| `unit-mismatch` (mg vs s) | **DIRECT 526**, INCOMPATIBLE 124 | INCOMPATIBLE 650 |
| `unit-convertible` (g vs kg) | **DIRECT 526**, **INCOMPATIBLE 124** | LOSSLESS 543, INCOMPATIBLE 107 |
| `origin-mismatch` (simulated vs measured) | **DIRECT 650** | INCOMPATIBLE 650 |
| `namespace-mismatch` (Ensembl vs HGNC) | **DIRECT 552**, INCOMPATIBLE 98 | INCOMPATIBLE 650 |
| `species-any` | **INCOMPATIBLE 575** | UNKNOWN 575 |

Overall, DIRECT_COMPATIBLE fell from 39.0% to 0%, UNKNOWN rose from 22.5% to 32.5%, and
INCOMPATIBLE rose from 27.2% to 46.9%. Bold entries are the wrong answers the review found.

### Reading the two-sided results

**`unit-convertible` is 543 lossless and 107 incompatible, and both are correct.** The scenario
forces grams against kilograms onto every profile. For the 543 that do not fix a quantity kind,
that is a mass conversion and the engine finds it. For the other 107 — a firing rate, a temperature,
a titre — grams is not a unit of what the profile measures, so the quantity-kind check refuses it
before any conversion is considered. Refusing there is the behaviour BMCS-SCI-016 exists to protect.

**UNKNOWN rising is the point, not a regression.** Contracts that used to pass silently now say
they do not carry enough evidence. The number to watch is whether it keeps climbing as more fields
become required: that would mean over-requirement, and the census is how it would show up.

## Files

- `census-baseline-2026-09-15.json` — the release as reviewed, before any fix.
- `census-2026-09-15-after-remediation.json` and `.md` — after the foundation decisions landed.
- `census-2026-09-15-after-d1-d2-d5-d8-d9.json` — an intermediate run, kept for the record.

The scenarios are deliberately synthetic. A census over real manifests would be better evidence and
needs a corpus that does not exist yet; this is the version that can run today.
