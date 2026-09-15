# Methylation M Value — `epigenome/methylation-m-value@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D7, D8, D10.

## Proposed scientific meaning

The log2 ratio of methylated to unmethylated signal at a declared CpG site or array probe:
`M = log2((Meth + a) / (Unmeth + a))`, where `a` is a declared stabilising offset. Unbounded, can be
negative, and approximately homoscedastic — which is why it is used for statistics while the beta
value is used for interpretation.

This profile is in the pilot because it is the clearest case of a transform-defined quantity: the
same biology, expressed on two scales, with a conversion that is exact only under stated conditions.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity (D3). |
| `representation.kind` | Scalar per site, or a matrix over sites and samples. |
| `measurement.quantity` | M-value, distinct from beta value and from raw intensities. |
| `measurement.unit` | `1`: dimensionless. |
| `measurement.scale` | `interval`, not `ratio`. M is unbounded and signed, so ratios of M values are meaningless. |
| `identifiers.namespace`, `identifiers.namespace_version` | Which probes: an array manifest with its version (450K, EPIC v1, EPIC v2), or genomic coordinates. Probe identifiers are not stable across manifest versions. |
| `measurement.normalization` | The preprocessing pipeline (noob, funnorm, BMIQ) with its version. M values from different normalisations are not interchangeable. |
| `biological_context.species` | Probe sets and CpG coordinates are species-specific. |
| `biological_context.tissue` | Methylation is strongly tissue-specific; a blood M value and a tumour M value at the same CpG are different measurements. |

**Conditional**

| Field | Condition |
|---|---|
| `representation.reference_assembly` | Required when sites are given as coordinates rather than probe IDs. |
| `uncertainty.missingness` | Required for matrices: probes failing detection p-value thresholds are missing, not zero. |
| `measurement.batch_correction` | Required when values are batch-corrected or cell-composition adjusted; the adjustment changes what the number means. |
| `biological_context.cell_type` | Required when the port is deconvolved to a cell type rather than bulk tissue. |
| `biological_context.assay` | Required when both array and bisulfite-sequencing data are in scope, since coverage-dependent noise differs. |
| `dimensions.feature_labels_ref`, `feature_labels_sha256` | Required for matrices, pinning the probe universe. |

**Recommended.** `origin.software_version` for the preprocessing toolchain;
`uncertainty.quality_flags` for per-probe detection.

**Deliberately not gating.** `artifact.*` unless exchanged as a file. `measurement.reference_range`.
`biological_context.age` and `sex`, although both are strong covariates — they inform analysis
rather than decide interface compatibility.

**Proposed new items.** A transform declaration with its base and offset (D8). Without it the
contract cannot state `a`, and the beta-to-M conversion cannot be checked.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `measurement.quantity` | equal, or a declared transform | unknown | M vs beta is a defined conversion, not a direct match |
| transform offset `a` | equal | unknown | Different offsets give different numbers from the same intensities |
| `identifiers.namespace` + version | equal, or pinned mapping (D7) | unknown | EPIC v1 to v2 probe mapping is partial: some probes were removed, so the mapping is lossy |
| `measurement.normalization` | compare when both declare (D2) | ignore | Different pipelines are not interchangeable |
| `biological_context.tissue` | subsumption (D4) | unknown | Blood vs tumour INCOMPATIBLE |

## What v0.1 gets wrong here

- `scale: ratio` for a signed, unbounded log ratio.
- No probe namespace, manifest version or normalisation is required, so two M-value ports can
  agree on every declared field and refer to different probe sets processed differently.
- The conversion fixture asserts `nM -> uM` for a dimensionless log ratio (BMCS-SCI-011).

## Fixtures to regenerate

- **positive**: `unit: 1`, `scale: interval`, transform log2 with offset declared, probe namespace
  EPIC v2 with manifest version, normalisation declared, tissue and species declared.
- **lossless**: beta to M with `a = 0` and beta strictly inside (0,1).
- **lossy or inference**: beta to M with a non-zero offset, which needs the underlying intensities.
- **contradiction**: M vs beta declared as the same quantity; blood vs tumour tissue.
- **unknown**: manifest version absent; normalisation absent.

## Questions for the reviewer

1. One profile with a declared transform, or two profiles for beta and M?
2. What offset convention should the standard default to, and should it be allowed to vary?
3. Beta values of exactly 0 or 1 make M infinite. Should the contract require clipping, and declare it?
4. Is bisulfite sequencing in scope here, where coverage replaces probe identity?
5. Should cell-composition adjustment be a normalisation or a separate derived profile?

## Sources to pin

`du-2010-mvalue` (the beta/M comparison and the offset); `stevens-1946` (interval vs ratio);
`ucum-2.2` (dimensionless `1`); the Illumina manifest version adopted, as a vendor document. Each
needs a SHA-256 at sign-off.

## Tests

BMCS-SCI-011; a Phase 2 case: beta and M declared as the same quantity must not be a direct match.
