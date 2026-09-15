# Pilot profile dossiers

Twenty profiles prepared for qualified scientific review. Fixing the foundations (Phase 1 of the
[remediation plan](../REMEDIATION_PLAN.md)) needs worked examples that show what a corrected profile
looks like; reviewing 650 profiles before the foundations are settled would waste reviewer time.

**Status of every dossier: prepared for qualified review, not approved.** Each was drafted with AI
assistance and must be checked by a domain-qualified scientific reviewer who did not author the
profile, plus a different schema reviewer. Nothing here is review evidence. Evidence files under
`source/reviews/` come only after Phase 1 lands and a qualified reviewer signs off.

## How to read a dossier

Each one states the scientific meaning it proposes, then what a port must declare, split into:

- **Required** — the port cannot be compared without it.
- **Conditional** — required when a stated condition holds, and inapplicable otherwise.
- **Recommended** — worth carrying, but it must not decide compatibility.
- **Deliberately not gating** — tempting fields that must not block a coupling, with the reason.
- **Proposed new items** — fields the contract vocabulary does not have yet, each tied to a decision.

Every requirement carries its own justification. A field is required only where it changes the
compatibility answer for *that* profile, which is what the pre-review's blanket item table got
wrong (erratum E3).

Anything not listed in a dossier defaults to declared-but-not-gating for that profile. That default
is deliberate: it keeps UNKNOWN floods away and forces each gating field to earn its place.

## The set

| Dossier | Domain | Principal failure modes it exercises |
|---|---|---|
| [core--scalar-quantity](core--scalar-quantity.md) | core | Allowed kinds contradict the profile; units not compared |
| [core--regular-time-series](core--regular-time-series.md) | core | Value unit vs time axis unit; sampling regime |
| [genome--single-nucleotide-variant](genome--single-nucleotide-variant.md) | genome | Assembly and coordinate conventions; no measured magnitude |
| [transcriptome--single-cell-expression-matrix](transcriptome--single-cell-expression-matrix.md) | transcriptome | Normalisation; feature universe; zeros vs missing |
| [epigenome--methylation-m-value](epigenome--methylation-m-value.md) | epigenome | Log transform, invertibility, bounds |
| [proteome--protein-abundance](proteome--protein-abundance.md) | proteome | Arbitrary intensity; quantification method |
| [metabolome--metabolite-concentration](metabolome--metabolite-concentration.md) | metabolome | Scale error; compartment; mass vs molar |
| [chemical--molecular-weight](chemical--molecular-weight.md) | chemical | Two quantities, one number; organism-independent |
| [pharmacology--binding-affinity](pharmacology--binding-affinity.md) | pharmacology | Endpoint identity; log-transformed values |
| [pharmacology--dose-response-curve](pharmacology--dose-response-curve.md) | pharmacology | Dose axis; response direction |
| [immunology--antibody-titer](immunology--antibody-titer.md) | immunology | Dilution titres; standardisation |
| [microbiology--taxonomic-abundance](microbiology--taxonomic-abundance.md) | microbiology | Community cardinality; taxonomy release |
| [virology--infectious-titer](virology--infectious-titer.md) | virology | Host vs pathogen taxa; assay-defined units |
| [imaging--ct-volume](imaging--ct-volume.md) | imaging | 3-D geometry; voxel value vs volume |
| [neuroscience--firing-rate](neuroscience--firing-rate.md) | neuroscience | False conversion; counting window |
| [physiology--body-temperature](physiology--body-temperature.md) | physiology | Affine units; interval scale; site |
| [epidemiology--incidence-rate](epidemiology--incidence-rate.md) | epidemiology | Person-time; aggregate vs individual data |
| [phenotype--time-to-event](phenotype--time-to-event.md) | phenotype | Censoring; time origin |
| [clinical--diagnosis-code](clinical--diagnosis-code.md) | clinical | Coding system versions; consent and data use |
| [simulation--state-trajectory](simulation--state-trajectory.md) | simulation | Simulated origin; artifact-only requirements |

## Reviewer checklist

1. Is the proposed scientific meaning right, and narrow enough that a different quantity cannot match?
2. Does each required field actually change the compatibility answer for this profile?
3. Is each conditional's condition stated precisely enough to implement?
4. Are the proposed units, scales and axes right, and are the UCUM spellings valid?
5. Do the proposed fixtures include a case that must be UNKNOWN and one that must be INCOMPATIBLE?
6. What is missing that would let two ports pass while being scientifically incomparable?
7. Which of the open questions can you settle, and which need a second specialist?
