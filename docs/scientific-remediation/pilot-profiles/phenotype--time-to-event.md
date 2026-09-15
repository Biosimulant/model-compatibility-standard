# Time to Event — `phenotype/time-to-event@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D2, D10, D11.

## Proposed scientific meaning

The time from a declared origin to a declared event, for one subject, together with whether the
observation was censored. A time-to-event value without its censoring indicator is not a
measurement of survival; it is a number that silently asserts the event happened.

This is the one profile in the pilot where `uncertainty.censoring` is unambiguously required, which
is why it is here: it tests whether the standard can express a conditional requirement that is
genuinely mandatory in one place and inappropriate in most others.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity (D3). |
| `representation.kind` | Event or record: the value is a duration plus a status, not a bare scalar. |
| `semantic.endpoint` | Which event: death from any cause, disease progression, relapse, device failure. Overall survival and progression-free survival are different endpoints with different clinical meaning. |
| `measurement.quantity`, `measurement.unit` | A duration, in `d`, `mo` or `a`. |
| `measurement.scale` | `ratio`: duration has a true zero. |
| `uncertainty.censoring` | Whether the value is an observed event time or a right-censored follow-up time, and the censoring type. Without it, censored observations are treated as events and every downstream estimate is biased. |
| `lifecycle.time_origin` | What t=0 is: diagnosis, randomisation, first dose, transplant. Two survival times from different origins are not comparable. |
| `biological_context.species` | Human and model-organism survival data are not interchangeable. |

**Conditional**

| Field | Condition |
|---|---|
| `lifecycle.observation_period` | Required when administrative censoring applies: the follow-up window determines what could have been observed. |
| `biological_context.disease` | Required when the endpoint is disease-specific. |
| `biological_context.intervention` | Required for trial or treatment data, where the arm is part of the meaning. |
| `biological_context.cohort`, `biological_context.population` | Required for cohort-level ports. |
| `security.data_use`, `security.consent_scope`, `security.deidentification` | Required for human subject data: survival dates are identifying, and event dates are quasi-identifiers. |
| `uncertainty.interval`, `uncertainty.confidence_level` | Required for summary estimates (median survival with its CI) rather than per-subject times. |
| `measurement.aggregation` | Required when the value is a summary (median, restricted mean) rather than an individual observation. |

**Recommended.** `origin.type`; `origin.observed_at`; `lifecycle.temporal_meaning`.

**Deliberately not gating.** `measurement.reference_range`. `biological_context.tissue`.
`artifact.*` for inline records.

**Proposed new items.** A competing-risks declaration: with competing events, a cause-specific time
and a subdistribution time are different quantities. `semantic.qualifiers` could carry it, but it is
not compared today.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `semantic.endpoint` | equal | unknown | Overall survival vs progression-free survival INCOMPATIBLE |
| `uncertainty.censoring` | equal, or declared handling | unknown | A port that carries no censoring cannot satisfy one that requires it — UNKNOWN, never a direct match |
| `lifecycle.time_origin` | equal | unknown | Different origins INCOMPATIBLE |
| `measurement.unit` | dimensional conversion (D1) | unknown | `d` to `mo` is not exact (months vary); `d` to `a` likewise. Either restrict to exact units or declare the conversion lossy |
| `measurement.aggregation` | compare when both declare (D2) | ignore | Individual times vs a median are different quantities |

## What v0.1 gets wrong here

- `uncertainty.censoring` is a candidate item, not a requirement, so a censored follow-up time and
  an observed event time are exchangeable.
- No endpoint and no time origin are required.
- The conversion fixture asserts `nM -> uM` for a duration (BMCS-SCI-011).
- The pre-review then over-corrected by marking censoring *required* in 400 packets (erratum E3);
  it belongs here and in survival outcomes, not across the catalogue.

## Fixtures to regenerate

- **positive**: unit `d`, `scale: ratio`, endpoint overall survival, origin randomisation, censoring
  declared, species `NCBITaxon:9606`, consent and data use declared.
- **unknown**: censoring absent on the source; time origin absent.
- **contradiction**: overall survival vs progression-free survival; diagnosis origin vs
  randomisation origin.
- **lossy**: individual times aggregated to a median — approval required, and not reversible.
- **conversion**: `d` to `wk` exact; `d` to `mo` flagged as inexact.

## Questions for the reviewer

1. Should interval censoring and left truncation be representable, or is right censoring the scope?
2. Are competing risks in scope, and if so how is the cause declared?
3. Should months and years be allowed at all, given they are not exact multiples of days?
4. Should per-subject and summary survival be one profile or two?
5. Does the endpoint need an external vocabulary (for example a clinical outcome ontology), or is a
   controlled list enough?

## Sources to pin

`clark-2003-survival` (censoring and its consequences); `ucum-2.2` (`d`, `wk`, `mo`, `a` and their
definitions); `vim-jcgm-200-2012`; a trial-endpoint reference for definitions of OS and PFS, to be
chosen by the reviewer. Each needs a SHA-256 at sign-off.

## Tests

BMCS-SCI-011; a new case in Phase 2: a port without censoring offered to one requiring it must be
UNKNOWN, never DIRECT_COMPATIBLE.
