# What the remediation changed, by domain

Baseline: `f7480a7`, the last commit before the foundations landed. Compared against
the regenerated `spec/v0.1` in the working tree.

This is a mechanical diff of the generated profile documents. It reports what moved, never
whether the new value is scientifically right — a required-item count falling, or an operator
appearing, says nothing about whether the profile now describes the science correctly. That
judgement belongs to the domain review waves, which is why this table is not an approval.

| Domain | Profiles | Required items | Operators added | Gained a fixed concept | Gained a kind constraint | Untyped schemas |
|---|---|---|---|---|---|---|
| cardiopulmonary-renal | 25 | 121 → 102 | namespace-version-compatible, representation-equivalent | 25 | 25 | 121 → 0 |
| cell | 25 | 118 → 97 | namespace-version-compatible, representation-equivalent | 25 | 25 | 118 → 0 |
| chemical | 25 | 91 → 71 | context-compatible, namespace-version-compatible, representation-equivalent | 25 | 25 | 91 → 0 |
| clinical | 25 | 156 → 131 | labels-equal, namespace-version-compatible, representation-equivalent, unit-convertible | 25 | 25 | 156 → 0 |
| core | 25 | 105 → 98 | context-compatible, namespace-version-compatible, representation-equivalent | 25 | 25 | 105 → 0 |
| developmental | 25 | 113 → 91 | namespace-version-compatible, representation-equivalent | 25 | 25 | 113 → 0 |
| ecology | 25 | 122 → 105 | namespace-version-compatible, representation-equivalent | 25 | 25 | 122 → 0 |
| epidemiology | 25 | 173 → 164 | namespace-version-compatible, representation-equivalent | 25 | 25 | 173 → 0 |
| epigenome | 25 | 122 → 107 | namespace-version-compatible, representation-equivalent | 25 | 25 | 122 → 0 |
| evolution | 25 | 130 → 112 | namespace-version-compatible, representation-equivalent | 25 | 25 | 130 → 0 |
| genome | 25 | 125 → 105 | namespace-version-compatible, representation-equivalent | 25 | 25 | 125 → 0 |
| imaging | 25 | 140 → 161 | digest-equal, namespace-version-compatible, representation-equivalent | 25 | 25 | 140 → 0 |
| immunology | 25 | 131 → 114 | namespace-version-compatible, representation-equivalent | 25 | 25 | 131 → 0 |
| lipidome-glycome | 25 | 146 → 133 | namespace-version-compatible, representation-equivalent | 25 | 25 | 146 → 0 |
| metabolome | 25 | 160 → 149 | namespace-version-compatible, representation-equivalent | 25 | 25 | 160 → 0 |
| microbiology | 25 | 136 → 122 | namespace-version-compatible, representation-equivalent | 25 | 25 | 136 → 0 |
| multiomics | 25 | 137 → 133 | namespace-version-compatible, representation-equivalent | 25 | 25 | 137 → 0 |
| neuroscience | 25 | 122 → 111 | namespace-version-compatible, representation-equivalent | 25 | 25 | 122 → 0 |
| pharmacology | 25 | 141 → 128 | namespace-version-compatible, representation-equivalent | 25 | 25 | 141 → 0 |
| phenotype | 25 | 126 → 114 | namespace-version-compatible, representation-equivalent | 25 | 25 | 126 → 0 |
| physiology | 25 | 148 → 131 | namespace-version-compatible, representation-equivalent | 25 | 25 | 148 → 0 |
| proteome | 25 | 142 → 127 | namespace-version-compatible, representation-equivalent | 25 | 25 | 142 → 0 |
| simulation | 25 | 86 → 76 | context-compatible, namespace-version-compatible, representation-equivalent | 25 | 25 | 86 → 0 |
| spatial | 25 | 129 → 128 | namespace-version-compatible, representation-equivalent | 25 | 25 | 129 → 0 |
| transcriptome | 25 | 119 → 110 | namespace-version-compatible, representation-equivalent | 25 | 25 | 119 → 0 |
| virology | 25 | 132 → 118 | namespace-version-compatible, representation-equivalent | 25 | 25 | 132 → 0 |

## What the columns mean

- **Required items** — how many fields each domain's profiles oblige a port to declare.
  Most domains fall, because `semantic.subject` stopped being a required, compared field
  (D4) and because a profile that declares no measurement no longer requires measurement
  fields. Imaging rises, because profiles that declare axes now require each axis to name
  itself (D9).
- **Operators added** — comparison operators that appear where the baseline had none.
- **Gained a fixed concept** — the baseline fixed no concept at all, so its `semantic.concept`
  rule compared two values that nothing constrained. Every profile now fixes a
  version-independent term (D3).
- **Gained a kind constraint** — the baseline allowed any representation kind for every
  profile. Each now publishes the kinds its meaning admits, though ~500 of those sets are
  still wider than the science warrants and narrowing them is review work (D6).
- **Untyped schemas** — requirements whose value schema accepted every JSON type, and so
  constrained nothing. This is the change the pre-review asked for most directly.

Across all 650 profiles: 650 gained a fixed concept, 650 gained a kind constraint, and requirements accepting any JSON type fell from 3371 to 0.

## How to reproduce

```bash
python scripts/domain_diff.py --baseline f7480a7 --out docs/scientific-remediation/measurements/domain-diff-2026-09-15.md
```
