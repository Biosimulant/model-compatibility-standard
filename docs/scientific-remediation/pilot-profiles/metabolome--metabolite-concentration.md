# Metabolite Concentration — `metabolome/metabolite-concentration@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D4, D7, D8.

## Proposed scientific meaning

The concentration of one identified metabolite in a declared biological compartment, as an
amount-of-substance concentration (`umol/L`) or a mass concentration (`mg/L`). A ratio-scale
quantity with a true zero, bounded below by the assay's limit of quantification.

The identity of the metabolite, the compartment it was measured in, and whether the value is molar
or mass-based are all part of the quantity. Plasma, serum, whole blood, urine, CSF and intracellular
concentrations of the same metabolite are different measurements, related by biology rather than by
arithmetic.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity of the quantity (D3). |
| `representation.kind` | Scalar, or a vector over samples. |
| `identifiers.namespace`, `identifiers.namespace_version` | Which metabolite: a ChEBI, HMDB or PubChem identifier with its release. A concentration without the analyte's identity is not comparable to anything. |
| `measurement.quantity` | Binds molar vs mass concentration, which have different dimensions (D1). |
| `measurement.unit` | UCUM: `umol/L`, `nmol/L`, `mg/L`, `ng/mL`. Note `uM` is **not** a UCUM code. |
| `measurement.scale` | `ratio`. The current `probability` is wrong. |
| `biological_context.compartment` | Plasma vs serum vs intracellular changes the value by orders of magnitude and is not convertible. |

**Conditional**

| Field | Condition |
|---|---|
| `biological_context.species` | Required when reference values or physiology are species-specific, which is the usual case for biofluids. |
| `measurement.detection_limits` | Required whenever values can fall below the limit of quantification; a value below LLOQ is not a measurement of zero. |
| `biological_context.assay` | Required when the method changes the value: targeted LC-MS/MS with internal standards vs untargeted semi-quantitation. |
| `biological_context.tissue` | Required for tissue concentrations, together with the normalisation basis (per g wet weight, per mg protein). |
| `measurement.normalization` | Required whenever the value is normalised (per protein, per cell count, per creatinine for urine). |
| `uncertainty.interval`, `uncertainty.confidence_level` | Required when a dispersion travels with the value. |
| `lifecycle.observation_period`, `biological_context.intervention` | Required for time-course or perturbation data (fasting state, dose, sampling time). |

**Recommended.** `measurement.calibration_ref` (internal standard, calibration curve);
`origin.instrument_model`; `origin.protocol_ref`; `identifiers.structure_hash` (InChIKey) as a
cross-check on analyte identity.

**Deliberately not gating.** `measurement.reference_range` — interpretation, not interface.
`artifact.*` for scalar exchange. `origin.operator`.

**Proposed new items.** A declared molar-mass parameter on the mass-to-molar transformation (D1), so
`mg/L` to `umol/L` becomes an explicit, parameterised, auditable conversion rather than either a
silent pass or a hard contradiction.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `identifiers.namespace` + version | equal, or pinned mapping (D7) | unknown | Different analyte namespaces need a mapping; ChEBI to HMDB is not identity |
| `measurement.unit` | dimensional conversion (D1) | unknown | `nmol/L` to `umol/L` lossless; `mg/L` to `umol/L` only with a declared molar mass |
| `measurement.scale` | equal | unknown | — |
| `biological_context.compartment` | equal | unknown | Plasma vs intracellular INCOMPATIBLE |
| `measurement.detection_limits` | compare when both declare (D2) | ignore | Different LLOQs are a quality matter, not a contradiction; surface as a warning |

## What v0.1 gets wrong here

- The positive fixture declares a micromolar concentration on a `probability` scale
  (BMCS-SCI-013) — the substring bug, since "concentration" contains "ratio".
- `identifiers.namespace` is the placeholder `example-namespace`, so the normative example teaches
  that any string identifies an analyte.
- No compartment is required, so a plasma concentration and an intracellular concentration of the
  same metabolite compare as directly compatible.
- No detection limits, so censored values pass as ordinary numbers.
- `mg/L` vs `uM` currently returns INCOMPATIBLE. That is the right *refusal* but for the wrong
  reason, and it is pinned as guard BMCS-SCI-105 so a naive dimensional-analysis fix cannot turn it
  into a silent conversion.

## Fixtures to regenerate

- **positive**: `unit: umol/L`, `scale: ratio`, analyte `CHEBI:17234` with a ChEBI release,
  compartment plasma, species `NCBITaxon:9606`, LLOQ declared.
- **conversion**: `nmol/L` to `umol/L` lossless (factor 1000).
- **parameterised conversion**: `mg/L` to `umol/L` with a declared molar mass — approval required.
- **contradiction**: plasma vs intracellular; analyte A vs analyte B.
- **unknown**: compartment absent; identifier release absent.

## Questions for the reviewer

1. Which analyte namespace is primary: ChEBI, HMDB, PubChem, or a declared choice with mappings?
2. Should free and protein-bound fractions be separable here, or is that a pharmacology concern?
3. Is compartment the right granularity, or is a specimen type (UBERON or OBI) needed as well?
4. Should below-LLOQ values be representable in the contract (a censoring flag), or excluded?
5. For urine, is creatinine normalisation a different quantity or a declared normalisation?

## Sources to pin

`ucum-2.2` (`umol/L`, `mg/L`; no `M`); `si-brochure-9`; `stevens-1946`; `fda-bmv-2018`
(LLOQ and calibration); ChEBI (Hastings et al. 2016, `10.1093/nar/gkv1031`); HMDB for biofluid
reference concentrations if adopted. Each needs a SHA-256 at sign-off.

## Tests

BMCS-SCI-013 (scale), BMCS-SCI-011 (conversion fixture); guard BMCS-SCI-105 (mass vs molar).
