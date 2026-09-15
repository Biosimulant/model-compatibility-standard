# Antibody Titer — `immunology/antibody-titer@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D4, D8, D11.

## Proposed scientific meaning

The amount of antibody against a declared antigen in a declared specimen, expressed either as an
endpoint dilution titre from a declared assay, or in units calibrated to a declared international
standard.

A dilution titre is a reciprocal dilution on a two-fold series: it is log-spaced, interval-censored,
and comparable only within one assay. Only calibration to an international standard makes values
comparable across assays, which is the whole reason such standards exist.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity (D3). |
| `representation.kind` | Scalar, or a vector over subjects. |
| `measurement.quantity` | Endpoint dilution titre, or calibrated antibody concentration. |
| `measurement.unit` | `1` for a reciprocal dilution; `[IU]/mL` for internationally standardised values. WHO binding antibody units must be written as an annotation such as `{BAU}/mL`: UCUM's `[BAU]` is a bioequivalent *allergen* unit and means something else entirely. |
| `measurement.scale` | Ordinal on a log2 dilution grid for dilution titres; `ratio` for calibrated concentrations (D8). |
| `semantic.entity` | The antigen. Anti-spike and anti-nucleocapsid titres are different measurements of the same serum. |
| `biological_context.assay` | ELISA, chemiluminescence, haemagglutination inhibition and neutralisation give different numbers for the same sample. |
| `biological_context.species` | The host that produced the antibody. |

**Conditional**

| Field | Condition |
|---|---|
| `measurement.calibration_ref` | Required whenever the value claims standardised units: the international standard and its code (for example a WHO/NIBSC preparation). |
| `biological_context.tissue` | The specimen: serum, plasma, dried blood spot, mucosal. Required when more than one is in scope, since they are not interchangeable. |
| `uncertainty.censoring` | Required when values can fall below the starting dilution or above the final one; `<1:20` is not the number 20. |
| antibody isotype | Required when IgG, IgM and IgA are all in scope. No catalogue item carries it today — see proposed items. |
| `biological_context.intervention` | Required for vaccination or challenge studies, where dose and schedule define the sample's meaning. |
| `lifecycle.observation_period`, `origin.observed_at` | Required for kinetics: a titre is meaningless without time since exposure or vaccination. |

**Recommended.** `origin.protocol_ref`; `origin.instrument_model`; `uncertainty.interval` for
replicate dispersion.

**Deliberately not gating.** `measurement.reference_range` — seroprotection thresholds are
interpretations and are assay-specific. `artifact.*`.

**Proposed new items.** An isotype declaration, and an antigen-strain qualifier: influenza and
SARS-CoV-2 titres are strain-specific, and `semantic.entity` alone does not carry the variant.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `measurement.quantity` | equal | unknown | Dilution titre vs `[IU]/mL` is not a direct match |
| `measurement.calibration_ref` | equal | unknown | Two standardised values are comparable only against the same standard |
| dilution titre to standardised units | inference (D11) | — | Requires an assay-specific calibration curve; approval required |
| `semantic.entity` (antigen) | equal, or subsumption | unknown | Different antigen INCOMPATIBLE |
| `biological_context.assay` | equal | unknown | Neutralisation vs binding INCOMPATIBLE |
| `uncertainty.censoring` | compare when both declare | ignore | A censored value against an exact-value consumer is UNKNOWN |

## What v0.1 gets wrong here

- `unit: 1`, `scale: ratio`: a two-fold dilution series is not ratio-scaled, and the profile cannot
  distinguish a reciprocal dilution from an international unit.
- No antigen, assay or specimen is required, so two unrelated titres compare as directly compatible.
- The conversion fixture asserts `nM -> uM` for a titre (BMCS-SCI-011).
- The pre-review suggested `BAU/mL` without noting that UCUM's `[BAU]` means a different unit
  (erratum E8 in the plan).

## Fixtures to regenerate

- **positive**: quantity endpoint dilution titre, `unit: 1`, ordinal log2 scale, antigen declared,
  assay ELISA IgG, specimen serum, species `NCBITaxon:9606`.
- **inference**: dilution titre offered to a port requiring `[IU]/mL` — approval required with a
  declared calibration.
- **contradiction**: anti-spike vs anti-nucleocapsid; binding vs neutralisation assay.
- **unknown**: antigen absent; censored `<1:20` against an exact-value consumer.
- **conversion**: none within dilution titres; the absence is itself the point.

## Questions for the reviewer

1. Should dilution titres and standardised concentrations be one profile with a declared quantity,
   or two?
2. How should the antigen strain be declared, and by which vocabulary?
3. Is `1` acceptable for a reciprocal dilution, or should the contract carry the dilution series?
4. Should neutralisation titres stay in their own profile, given the same structure applies?
5. What makes two ELISA results comparable in practice — the same kit, the same standard, both?

## Sources to pin

`who-is-antibody-2021` (international standards and BAU); `ucum-2.2` (`[IU]`; `[BAU]` is an
allergen unit); `stevens-1946` (ordinal and log-spaced values); `reed-muench-1938` for endpoint
estimation where relevant. Each needs a SHA-256 at sign-off.

## Tests

BMCS-SCI-011; Phase 2 cases for titre-versus-standardised-unit and for censored values.
