# Firing Rate — `neuroscience/firing-rate@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D2, D5, D8, D9.

## Proposed scientific meaning

The rate at which a defined neural unit emits action potentials, estimated over a declared counting
window. The quantity is a frequency (dimension 1/time). It is not a spike train, not a spike count,
and not a normalised or z-scored rate.

Two firing rates are comparable only when they describe the same kind of unit (single neuron,
multi-unit cluster, or population average) and were estimated over compatible windows. A 10 ms
window and a whole-trial average are different quantities, not different units.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity of the quantity; must be a version-independent term (D3), not today's self-reference. |
| `representation.kind` | Scalar, per-unit vector and time-binned matrix are different shapes of the same quantity. |
| `measurement.quantity` | Must resolve to a frequency quantity kind, which is what binds the unit's dimension (D1). |
| `measurement.unit` | `Hz` or `/min`; any unit of dimension 1/time. This is the field that makes the number meaningful. |
| `measurement.scale` | `ratio`: a firing rate has a true zero, so ratios of rates are meaningful. |
| `lifecycle.window` | The counting window is part of the quantity. Without it, an instantaneous rate and a trial mean are exchanged silently. |
| `semantic.entity` | What the rate belongs to: single unit, multi-unit, or population. The item exists in the catalogue but is required by no profile today. |

**Conditional**

| Field | Condition |
|---|---|
| `biological_context.species` | Required whenever the rate is compared across preparations; species-specific baselines make cross-species exchange a scientific claim, not a conversion. |
| `biological_context.brain_region` (via `biological_context.tissue`) | Required when the consumer selects by region; a CURIE from UBERON or an atlas, compared by subsumption (D4). |
| `dimensions.axes` + `representation.ordering` | Required when the value is not scalar: which axis is unit and which is time bin. |
| `lifecycle.time_unit`, `lifecycle.time_origin` | Required for time-binned rates. |
| `origin.method`, `origin.method_version` | Required when the rate is produced by spike sorting or deconvolution, because unit identity depends on the sorter. |
| `uncertainty.kind`, `uncertainty.variance` | Required when a dispersion value travels with the rate. |

**Recommended.** `biological_context.cell_type` (CL term); `origin.instrument`; `origin.software_version`;
`biological_context.assay` (extracellular, patch, calcium imaging — calcium-derived rates are inferred, not measured).

**Deliberately not gating.** `artifact.*` — a scalar rate is exchanged inline, so file format cannot
change the science. `uncertainty.quality_flags` — useful for filtering, not for deciding a coupling.
`origin.operator` — personal data with no bearing on compatibility.

**Proposed new items.** A quantity-kind registry entry binding this profile to frequency (D1); a
`measurement.window_basis` distinguishing a fixed window, an adaptive kernel and a whole-trial mean,
unless `lifecycle.window` can carry that (D1, reviewer question 3).

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `measurement.unit` | dimensional conversion (D1) | unknown | Hz vs /min lossless (factor 60); Hz vs any non-frequency unit INCOMPATIBLE |
| `measurement.scale` | equal | unknown | A z-scored rate is not this profile |
| `lifecycle.window` | equal, then declared tolerance | unknown | Different windows are not a conversion |
| `semantic.entity` | equal | unknown | Single-unit vs population is a contradiction |
| `biological_context.species` | subsumption (D5) | unknown | Cross-species is a contradiction for a species-specific port |

## What v0.1 gets wrong here

- The conversion fixture asserts `nM -> uM` is lossless **for a firing rate** (BMCS-SCI-004), and a
  contract declaring the rate in `kg` validates cleanly (BMCS-SCI-005).
- The unit `1/s` is right, but nothing binds it to the quantity, so any unit passes.
- No counting window is required anywhere, so two incomparable estimates compare as direct.
- `semantic.subject` is the placeholder `nervous_system`, which cannot distinguish a cortical single
  unit from a whole-brain average.

## Fixtures to regenerate

- **positive**: `unit: Hz`, `scale: ratio`, window 1 s, entity single-unit, species `NCBITaxon:10090`,
  region a real UBERON term.
- **conversion**: `Hz` to `/min`, lossless, factor 60 — replacing the nM to uM fixture.
- **contradiction**: `Hz` vs `mV` (different dimension) INCOMPATIBLE; single-unit vs population
  INCOMPATIBLE; 10 ms window vs trial mean INCOMPATIBLE.
- **unknown**: window absent on either side; species absent on either side.
- **lossy**: calcium-imaging-inferred rate offered to a port requiring electrophysiological rate
  (inference path, D11).

## Questions for the reviewer

1. Is the counting window enough, or must the smoothing kernel and its bandwidth also be declared?
2. Should calcium-imaging-derived rates be in scope at all, or excluded into their own profile? They
   are model-inferred, and the inference is not invertible.
3. Is `lifecycle.window` the right home for the estimation window, or does this need its own item?
4. Should instantaneous rate (a limit) and binned rate be one profile or two?
5. For multi-unit activity, what must a port declare so a consumer knows it is not single-unit?

## Sources to pin

`nwb-2022` (Neurodata Without Borders, for what a unit and its provenance must carry);
`bids-ieeg-2019`; `ucum-2.2` (`Hz`, `/min`); `vim-jcgm-200-2012` (quantity and unit); `stevens-1946`
(ratio scale). Each needs a SHA-256 of the exact reviewed document at sign-off.

## Tests

BMCS-SCI-004, BMCS-SCI-005, BMCS-SCI-010; guards BMCS-SCI-101, BMCS-SCI-106.
