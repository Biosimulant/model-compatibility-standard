# Protein Abundance — `proteome/protein-abundance@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D2, D7, D8, D10.

## Proposed scientific meaning

The abundance of protein groups in a sample, estimated by a declared mass-spectrometry
quantification strategy. Most values are in arbitrary units and are comparable only within one
strategy, one normalisation and, for isobaric labelling, one plex.

"Protein abundance" names a family of quantities, not one: label-free intensity, iBAQ, spectral
counts, isobaric reporter intensities or ratios, and absolute amounts are not interchangeable.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity (D3). |
| `representation.kind` | Vector or matrix over protein groups. |
| `measurement.quantity` | Which quantification: LFQ intensity, iBAQ, spectral count, reporter-ion intensity, reporter ratio, or absolute amount. This is the field that stops the family collapsing into one number. |
| `measurement.unit` | `1` for arbitrary intensity, declared explicitly so "arbitrary" is a statement rather than an omission; a real UCUM unit (`fmol/ug`) for absolute quantification. |
| `measurement.scale` | `ratio` for linear intensity, `interval` for log intensity, `count` for spectral counts (D8). |
| `measurement.normalization` | Required always: unnormalised and median- or quantile-normalised intensities are different values. |
| `identifiers.namespace`, `identifiers.namespace_version` | UniProt with its release. Accessions are merged and demerged between releases. |
| `identifiers.ambiguity_handling` | How shared peptides and protein groups are resolved. It defines what one row *is*, and two pipelines disagree about it. |
| `biological_context.species` | Search databases are species-specific. |

**Conditional**

| Field | Condition |
|---|---|
| `measurement.control`, `measurement.baseline` | Required for ratio quantities: a reporter ratio without its reference channel is uninterpretable. |
| `measurement.batch_correction` | Required for multi-plex experiments; TMT plexes are not directly comparable without bridging. |
| `uncertainty.missingness` | Required: missing values in proteomics are largely not-missing-at-random, and treating them as zero biases every downstream test. |
| `uncertainty.imputation` | Required when values are imputed; imputed and observed values must not be exchanged silently. |
| `dimensions.feature_labels_ref`, `feature_labels_sha256` | Required for matrices: the protein-group universe, pinned. |
| `biological_context.tissue`, `biological_context.cell_line` | Required when the port is selected by sample origin. |
| `origin.software`, `origin.software_version` | Required when the quantity is pipeline-defined (MaxQuant LFQ, DIA-NN, Spectronaut); the algorithm is part of the quantity. |
| `biological_context.assay` | Required when DDA, DIA and targeted assays are all in scope. |

**Recommended.** `origin.instrument_model`; `origin.protocol_ref`; `uncertainty.quality_flags`
(q-value, number of peptides).

**Deliberately not gating.** `artifact.*` unless exchanged as a file. `measurement.reference_range`.
`origin.operator`.

**Proposed new items.** An explicit "arbitrary unit" marker, or a quantity kind that carries it
(D1), so a dimensionless arbitrary intensity cannot be compared against a dimensionless ratio as if
both were plain numbers.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `measurement.quantity` | equal | unknown | LFQ intensity vs iBAQ INCOMPATIBLE; neither derives from the other without peptide-level data |
| `measurement.normalization` | compare when both declare (D2) | ignore | Different normalisations are not interchangeable |
| `measurement.scale` | equal, or a declared transform | unknown | log2 to linear is exact given the base and any offset |
| `identifiers.namespace` + version | equal, or pinned mapping (D7) | unknown | UniProt release differences need a mapping |
| `uncertainty.missingness` | compare when both declare | ignore | Zero-filled vs NA-preserved matrices are different data |

## What v0.1 gets wrong here

- `unit: 1`, `scale: ratio` with no quantification strategy and no normalisation required: the
  profile cannot distinguish a spectral count from a TMT ratio.
- `identifiers.namespace` is required but its example is `example-namespace`.
- The conversion fixture asserts `nM -> uM` for an arbitrary intensity (BMCS-SCI-011).
- Missingness is a candidate item, so an imputed matrix and an observed one are exchangeable.

## Fixtures to regenerate

- **positive**: quantity LFQ intensity, `unit: 1` arbitrary, `scale: ratio`, normalisation declared,
  UniProt release declared, ambiguity handling declared, species `NCBITaxon:9606`, missingness
  declared.
- **conversion**: log2 intensity to linear intensity, lossless given base and offset.
- **contradiction**: LFQ intensity vs reporter ratio; different UniProt releases with no mapping
  (UNKNOWN rather than a match).
- **lossy**: intensities aggregated from peptides to protein groups under a different rule.
- **unknown**: normalisation absent; ambiguity handling absent.

## Questions for the reviewer

1. Should absolute quantification be a separate profile, given it has real units and a calibration?
2. Is protein-group identity declarable well enough to compare across pipelines, or must ports
   agree on a pipeline?
3. Should reporter ratios be their own profile, since they require a reference channel?
4. Is peptide-level abundance in scope here or only in the peptide profile?
5. What is the minimum provenance that makes two intensity matrices comparable at all?

## Sources to pin

MaxLFQ (Cox et al. 2014, `10.1074/mcp.M113.031591`); mzTab (Griss et al. 2014,
`10.1074/mcp.O113.036681`); `mzml-2011`; UniProt's current release paper; `robinson-2010-tmm` for
normalisation reasoning; `stevens-1946`. Each needs a SHA-256 at sign-off.

## Tests

BMCS-SCI-011; Phase 2 cases for quantity-strategy mismatch and imputed-vs-observed values.
