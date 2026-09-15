# Single-cell Expression Matrix — `transcriptome/single-cell-expression-matrix@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D2, D6, D7, D8, D10.

## Proposed scientific meaning

A cells-by-features matrix of expression values from a single-cell or single-nucleus assay, where
the feature universe is pinned by identifier namespace and release, and the value type is declared:
raw counts, or a named normalisation with its transform.

Raw UMI counts, CPM, log1p-normalised values and z-scores are four different quantities in the same
shaped container. Most of this profile's work is keeping them apart.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity (D3). |
| `representation.kind` | A matrix kind. `dense_vector` is the current positive fixture, which does not describe a matrix. |
| `dimensions.axes`, `axes[].name`, `axes[].meaning` | Which axis is cells and which is features. The generated axes are `[sample, feature]`; for single-cell data the first axis is cells or barcodes, not samples. |
| `dimensions.feature_axis`, `dimensions.sample_axis` | Named explicitly so a transposed matrix cannot pass. |
| `dimensions.feature_labels_ref`, `dimensions.feature_labels_sha256` | The feature universe, pinned. Position *i* means nothing without it. |
| `representation.ordering` | Whether feature order is part of the contract. |
| `identifiers.namespace`, `identifiers.namespace_version` | Ensembl gene IDs with a release, or an equivalent. Symbols and IDs are different namespaces with a lossy mapping between them. |
| `measurement.quantity` | The value type: UMI counts, read counts, CPM, TPM, log-normalised, scaled. This is the field whose absence produces BMCS-SCI-001. |
| `measurement.scale` | `count` for counts, `ratio` or `interval` for normalised values (D8). |
| `measurement.normalization` | Required whenever the values are not raw counts: the method and its parameters. |
| `biological_context.species` | Feature universes are species-specific. |

**Conditional**

| Field | Condition |
|---|---|
| `measurement.unit` | Required when values carry one (`1` for counts); dimensionless normalised values still declare `1` explicitly. |
| `representation.sparsity` | Required when the matrix is sparse, together with what an absent entry means — an observed zero, not a missing value (D6). |
| `uncertainty.missingness` | Required when absent entries can mean "not measured", as in targeted panels or multi-batch merges. |
| `biological_context.assay` | Required because UMI-based 3' assays and full-length assays are not interchangeable for the same nominal quantity. |
| `biological_context.tissue`, `biological_context.cell_type` | Required when the port is selected by tissue or annotated cell type; CURIEs compared by subsumption (D4). |
| `measurement.batch_correction` | Required when values are batch-corrected: corrected and uncorrected values cannot be pooled. |
| `origin.processing_pipeline_ref`, `origin.software_version` | Required when the quantity is pipeline-defined (for example CellRanger's filtered matrix). |
| `identifiers.unmapped_handling`, `identifiers.mapping_refs` | Required when a namespace mapping is applied; without it, feature loss is invisible (D7). |

**Recommended.** `biological_context.disease`; `biological_context.intervention` for perturbation
screens; `uncertainty.quality_flags` for per-cell QC.

**Deliberately not gating.** `artifact.*` unless the matrix is exchanged as a file, in which case
format and schema become required. `origin.operator`. `measurement.reference_range`.

**Proposed new items.** A transform item with an explicit base and pseudocount (D8); log1p base e
and log2 with pseudocount 1 are different values from the same counts.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `measurement.quantity` | equal | unknown | Counts vs log-normalised INCOMPATIBLE, or a declared lossy transformation in the counts-to-normalised direction only |
| `measurement.normalization` | compare when both declare (D2) | ignore | Different methods are not interchangeable |
| `identifiers.namespace` + version | equal, or pinned mapping (D7) | unknown | Ensembl to HGNC needs a mapping; it is many-to-many and lossy |
| `dimensions.feature_labels_sha256` | equal | unknown | Same digest means the same feature universe, which is the cheapest correct check available |
| `representation.kind` | equal, or declared lossless re-encoding (D6) | unknown | dense to sparse lossless only with implicit-entry, ordering, shape and dtype declared equal |
| `biological_context.species` | subsumption (D5) | unknown | Human vs mouse INCOMPATIBLE |

## What v0.1 gets wrong here

- Counts and log1p-normalised values compare as DIRECT_COMPATIBLE when both are declared
  (BMCS-SCI-001), and so do Ensembl IDs against HGNC symbols (BMCS-SCI-002).
- No feature universe, no identifier namespace and no value type are required.
- The axes are `[sample, feature]` for a cells-by-features matrix.
- Dense vs sparse returns INCOMPATIBLE (guard BMCS-SCI-104): the right refusal today, but it must
  become a lossless conversion once the implicit-entry rules are declarable, not before.

## Fixtures to regenerate

- **positive**: matrix, axes `[cell, feature]`, features `ensembl.gene` release 114 with a pinned
  label digest, quantity UMI counts, `scale: count`, `unit: 1`, species `NCBITaxon:9606`, assay
  declared, sparsity with implicit zero.
- **lossy**: counts offered to a port requiring log-normalised values — approval required.
- **mapping**: Ensembl to HGNC with a pinned mapping — lossy, approval required; without a mapping
  — UNKNOWN.
- **lossless**: dense to sparse with implicit-entry, ordering, shape and dtype declared equal.
- **contradiction**: human vs mouse; counts vs z-scores.
- **unknown**: feature universe absent; value type absent.

## Questions for the reviewer

1. Should a port be allowed to carry only normalised values, or must raw counts be recoverable?
2. Is cell-level annotation (cell type) part of this contract or a separate companion port?
3. Should spliced and unspliced layers be separate ports, or layers within one?
4. For merged datasets, what must be declared so a consumer knows batch structure exists?
5. Is CELLxGENE's schema the right external anchor for the value-type vocabulary?

## Sources to pin

`wagner-2012-tpm`; `robinson-2010-tmm`; `svensson-2020-zeros` (zeros in droplet data are mostly real,
which is why implicit zero and missing must be distinguished); `ensembl-2024`; `bioregistry-2022`.
Add the AnnData and CELLxGENE schema versions if adopted. Each needs a SHA-256 at sign-off.

## Tests

BMCS-SCI-001, BMCS-SCI-002; guard BMCS-SCI-104.
