# Infectious Titer — `virology/infectious-titer@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D5, D8, D11.

## Proposed scientific meaning

The concentration of infectious virus in a declared preparation, measured by a declared assay in a
declared host cell system: plaque-forming units per millilitre, 50% tissue-culture infectious dose
per millilitre, or focus-forming units per millilitre.

The unit is defined by the assay. A titre is a property of a virus-cell-protocol combination, not of
the virus alone, and the conventional log10 handling is part of how the values are used.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity (D3). |
| `representation.kind` | Scalar, or a vector over samples. |
| `measurement.quantity` | Which assay endpoint: PFU, TCID50, FFU. These are not the same quantity. |
| `measurement.unit` | `[PFU]/mL` or `[TCID_50]/mL` — both are real UCUM codes. Focus-forming units need an annotation, since UCUM has no `[FFU]`. |
| `measurement.scale` | `ratio`, with a declared log10 transform when values are reported as log10 titres (D8). |
| `biological_context.assay` | Plaque assay, endpoint dilution with a declared readout, or focus-forming assay. |
| `biological_context.cell_line` | The host cell (a Cellosaurus identifier). Titres of the same stock differ severalfold between Vero, Vero E6 and Calu-3. |
| pathogen taxon | Which virus, at strain or isolate level. Today `biological_context.species` is generated as `NCBITaxon:9606`, the host, and nothing identifies the virus. |

**Conditional**

| Field | Condition |
|---|---|
| `biological_context.strain` | Required when isolate-level identity matters, which for variant work it always does. |
| `biological_context.species` | Required as the **host** species when relevant, declared as the host role (D5). |
| `uncertainty.interval`, `uncertainty.confidence_level` | Required for TCID50, which is an estimate with a confidence interval, not a count. |
| `measurement.detection_limits` | Required when values can fall below the assay's limit of detection; a negative well is not a titre of zero. |
| `uncertainty.censoring` | Required when below-limit values are reported. |
| `biological_context.passage` | Required for stocks where passage history changes infectivity. |
| `origin.protocol_ref`, `origin.protocol_version` | Required when incubation time, overlay and staining differ between labs and change the count. |

**Recommended.** `biological_context.medium`; `origin.instrument_model` for automated counters;
`lifecycle.observation_period` for time-course sampling.

**Deliberately not gating.** `artifact.*`. `measurement.reference_range`.
`biological_context.age` and `sex`.

**Proposed new items.** A pathogen-taxon role, so the virus and the host cell's organism can both be
declared (D5). This profile cannot currently say which organism was measured.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `measurement.quantity` | equal | unknown | PFU vs TCID50 is not a direct match |
| PFU to TCID50 | inference (D11) | — | The conventional 0.7 factor is a Poisson approximation, assay-dependent; approval required, never automatic |
| `measurement.unit` | dimensional conversion (D1) | unknown | `[PFU]/mL` to `[PFU]/L` lossless; `[PFU]/mL` to `[TCID_50]/mL` is not a unit conversion |
| `biological_context.cell_line` | equal | unknown | Different host cell INCOMPATIBLE without a declared bridging study |
| pathogen taxon and strain | equal, or subsumption | unknown | Different virus INCOMPATIBLE |

## What v0.1 gets wrong here

- `unit: 1`, `scale: ratio`: no volume basis and no assay, so the number has no meaning.
- `biological_context.species: NCBITaxon:9606` identifies the host, while the measured organism is
  the virus, which appears nowhere.
- No cell line, assay or detection limit is required.
- The conversion fixture asserts `nM -> uM` for a titre (BMCS-SCI-011).

## Fixtures to regenerate

- **positive**: quantity PFU, `unit: [PFU]/mL`, `scale: ratio`, pathogen taxon with strain, host
  cell line declared, assay plaque assay, detection limit declared.
- **conversion**: `[PFU]/mL` to `[PFU]/L` lossless.
- **inference**: TCID50 offered to a port requiring PFU — approval required.
- **contradiction**: PFU vs TCID50 declared as the same quantity; different cell line.
- **unknown**: cell line absent; strain absent.

## Questions for the reviewer

1. Should genome copies per millilitre (qPCR) be in this profile or firmly excluded? They are not
   infectious units, and conflating them is a common error.
2. How should the virus be identified: NCBI Taxonomy plus a strain string, or a virus-specific
   nomenclature?
3. Should the host cell line be required, or only recommended for well-standardised assays?
4. Is log10 titre a separate quantity or a declared transform?
5. What bridging evidence would justify comparing titres across cell lines?

## Sources to pin

`reed-muench-1938` (endpoint estimation, and why TCID50 is an estimate); `ucum-2.2` (`[PFU]` and
`[TCID_50]` confirmed present); Cellosaurus (Bairoch 2018, `10.7171/jbt.18-2902-002`);
`ncbitaxon-schoch-2020`. Each needs a SHA-256 at sign-off.

## Tests

BMCS-SCI-011; Phase 2 cases for PFU against TCID50 and for the host-cell dependency.
