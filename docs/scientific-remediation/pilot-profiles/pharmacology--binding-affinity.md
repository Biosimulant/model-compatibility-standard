# Binding Affinity — `pharmacology/binding-affinity@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D2, D8, D11.

## Proposed scientific meaning

A measure of the interaction between a declared ligand and a declared molecular target, of a
declared type: an equilibrium dissociation constant `Kd`, an inhibition constant `Ki`, or a
half-maximal concentration `IC50` or `EC50`, expressed either as a molar concentration or as its
negative base-10 logarithm.

These are not the same quantity. `IC50` depends on assay conditions; `Ki` does not. Converting one
to the other requires the Cheng-Prusoff relation, the substrate or radioligand concentration, its
`Km` or `Kd`, and an assumption of competitive binding — an inference, not a unit conversion.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity (D3). |
| `representation.kind` | Scalar, or a vector over ligand-target pairs. |
| `semantic.endpoint` | Which constant: Kd, Ki, IC50, EC50. Without it, the number is uninterpretable and today nothing carries it. |
| `measurement.quantity` | Molar concentration, or negative log10 molar. |
| `measurement.unit` | `nmol/L`, `umol/L` for concentrations; `1` for p-scale values. Note `uM` and `nM` are not UCUM codes. |
| `measurement.scale` | `ratio` for concentrations; `interval` for p-scale values, which are logarithmic (D8). |
| `semantic.entity` | The ligand, by identifier. |
| target identity | The protein target, by UniProt accession. Today no item carries a second entity — see proposed items. |
| `biological_context.species` | The target's species: a human and a rat orthologue give different affinities. |

**Conditional**

| Field | Condition |
|---|---|
| `biological_context.assay` | Required whenever IC50 or EC50 is reported, since those depend on the assay format; recommended for Kd. |
| assay conditions (substrate concentration, `Km`, temperature, pH) | Required when the port is intended to support conversion to `Ki`; without them the Cheng-Prusoff path is unavailable. |
| `uncertainty.censoring` | Required when qualified values are in scope (`> 10 umol/L` from a screen that did not reach saturation). A censored value must not be compared as an exact one. |
| `measurement.aggregation` | Required when the value is a summary over replicates or literature reports; a geometric mean of heterogeneous assays is a different quantity. |
| `uncertainty.interval`, `uncertainty.confidence_level` | Required when a confidence interval travels with the estimate. |
| `biological_context.cell_line`, `biological_context.medium` | Required for cell-based functional assays. |

**Recommended.** `origin.protocol_ref`; `origin.fit_method` (how the curve was fitted);
`identifiers.structure_hash` for the ligand.

**Deliberately not gating.** `artifact.*`. `measurement.reference_range`.
`biological_context.tissue` for biochemical assays.

**Proposed new items.** A second typed entity, so ligand and target can both be declared and
compared. `semantic.entity` is a single field, and `identifiers.entity_type` describes one
namespace, so a ligand-target pair currently cannot be expressed in the contract at all. This is
the largest gap in the profile.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `semantic.endpoint` | equal | unknown | Kd vs IC50 is not a direct match |
| `measurement.unit` | dimensional conversion (D1) | unknown | `nmol/L` to `umol/L` lossless |
| quantity vs p-scale | declared transform (D8) | unknown | `Kd` to `pKd` is exact for positive values |
| IC50 to Ki | inference (D11) | — | Requires Cheng-Prusoff inputs; approval required, never automatic |
| target and ligand identity | equal, or pinned mapping | unknown | Different target INCOMPATIBLE |
| `biological_context.species` | subsumption (D5) | unknown | Human vs rat orthologue INCOMPATIBLE unless declared equivalent |

## What v0.1 gets wrong here

- `unit: 1`, `scale: ratio`, no endpoint: a `Kd` in molar, a `pKd` and an `IC50` all satisfy the
  same contract and compare as directly compatible.
- Neither the ligand nor the target is identified, so two unrelated affinities match.
- `biological_context.species` is required, but for the wrong reason: it is the *target's* species
  that matters, not the subject's.
- The conversion fixture asserts `nM -> uM`, which here is at least dimensionally plausible, but the
  positive fixture's `unit: 1` means the profile is not measuring a concentration at all.

## Fixtures to regenerate

- **positive**: endpoint Kd, `unit: nmol/L`, `scale: ratio`, ligand and target identified, target
  species `NCBITaxon:9606`, assay declared.
- **lossless**: `nmol/L` to `umol/L`; `Kd` to `pKd`.
- **inference**: IC50 offered to a port requiring Ki — approval required, with the Cheng-Prusoff
  inputs declared.
- **contradiction**: Kd vs EC50; different target; human vs rat target.
- **unknown**: endpoint absent; target absent; censored value against an exact-value consumer.

## Questions for the reviewer

1. How should the ligand-target pair be modelled: two typed entities, a pair identifier, or a
   composite profile?
2. Should `pKd` be a separate profile or a declared transform of the same quantity?
3. Are functional potencies (EC50 from cell assays) in scope with binding constants, or separate?
4. What minimum assay metadata makes two `Kd` values comparable — buffer, temperature, method?
5. Should aggregated literature values (as in ChEMBL) be allowed, and if so how is heterogeneity
   declared?

## Sources to pin

`iuphar-neubig-2003` (terms and symbols; Kd, Ki, IC50, and p-scale definitions); Cheng and Prusoff
1973 (`10.1016/0006-2952(73)90196-2`); ChEMBL's current release paper for the standard-type and
relation conventions; `ucum-2.2`; `stevens-1946`. Each needs a SHA-256 at sign-off.

## Tests

BMCS-SCI-011; Phase 2 cases for endpoint mismatch and the IC50-to-Ki inference path.
