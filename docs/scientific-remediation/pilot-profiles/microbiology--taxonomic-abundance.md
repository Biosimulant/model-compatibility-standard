# Taxonomic Abundance — `microbiology/taxonomic-abundance@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D5, D7, D8, D10.

## Proposed scientific meaning

The abundance of each taxon in a microbial community sample, over a feature universe defined by a
declared taxonomy and release, at a declared rank, as either counts or relative abundances.

This is the pilot's test of species cardinality. A community profile describes many organisms at
once, so the single `biological_context.species` field that the generator requires is the wrong
shape — and its generated value, `NCBITaxon:9606`, is the host rather than anything measured.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity (D3). |
| `representation.kind` | Vector or matrix over taxa. |
| `dimensions.axes`, `axes[].name`, `axes[].meaning` | Which axis is taxa and which is samples. |
| `dimensions.feature_labels_ref`, `feature_labels_sha256` | The taxon universe, pinned. |
| `identifiers.taxonomy_namespace`, `identifiers.taxonomy_version` | NCBI Taxonomy, GTDB or SILVA, with its release. Taxa are renamed and re-parented between releases, so the release is part of the label's meaning. |
| taxonomic rank | Genus-level and species-level abundances are different feature universes. No catalogue item carries rank — see proposed items. |
| `measurement.quantity` | Read counts, relative abundance, or estimated absolute abundance (cells per gram). |
| `measurement.unit` | `1` for counts and proportions; a real unit for absolute abundance. |
| `measurement.scale` | `count` for counts, `proportion` for relative abundance (D8). |
| `measurement.normalization` | Rarefaction, total-sum scaling, or centred log-ratio. These produce different numbers with different statistical properties. |
| `biological_context.assay` | 16S amplicon and shotgun metagenomics do not produce comparable feature spaces, and amplicon results depend on the variable region. |

**Conditional**

| Field | Condition |
|---|---|
| `biological_context.species` | Required as the **host** species only for host-associated communities, and it must be declared as the host rather than as the measured organism (D5). |
| `biological_context.tissue`, `biological_context.compartment` | Required for host-associated samples: gut, skin and oral communities are not comparable. |
| `uncertainty.missingness` | Required to distinguish a taxon that was absent from one that was below detection or filtered out. |
| `measurement.detection_limits` | Required when a minimum-count or prevalence filter has been applied. |
| `identifiers.mapping_refs`, `unmapped_handling` | Required when taxa are mapped between taxonomies; GTDB and NCBI names diverge substantially. |
| `origin.processing_pipeline_ref`, `origin.software_version` | Required when the classifier defines the feature values (DADA2, Kraken2, MetaPhlAn). |
| `constraints[]` | Required for relative abundance: the sum-to-one constraint is part of the data's meaning and drives the compositional caveat below. |

**Recommended.** `biological_context.geography`, `biological_context.cohort` for population studies;
`origin.protocol_ref` for extraction method, which strongly affects observed composition.

**Deliberately not gating.** `artifact.*` unless exchanged as a file.
`measurement.reference_range`. `security.*` for non-human-derived samples; for human microbiome
data, consent applies at the policy layer (D12).

**Proposed new items.** A taxonomic rank declaration, and a taxon-role declaration so host and
community members are distinguishable (D5). Both are missing from the catalogue.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `identifiers.taxonomy_namespace` + version | equal, or pinned mapping (D7) | unknown | GTDB to NCBI is a partial mapping, so it is lossy |
| rank | equal | unknown | Genus vs species INCOMPATIBLE |
| `measurement.quantity` | equal | unknown | Counts vs relative abundance: counts to proportions is lossy (library size is discarded) and the reverse is not possible |
| `measurement.normalization` | compare when both declare (D2) | ignore | Rarefied and CLR-transformed data are not interchangeable |
| `biological_context.assay` | equal | unknown | 16S vs shotgun INCOMPATIBLE |

## What v0.1 gets wrong here

- `biological_context.species: NCBITaxon:9606` in the positive fixture: a human taxon on a microbial
  community vector, and a single value where the data describe many organisms.
- `identifiers.namespace` is `example-namespace`, and no taxonomy release is required.
- No rank, no normalisation, no assay: a genus-level 16S proportion vector and a species-level
  shotgun count matrix satisfy the same contract.
- The conversion fixture asserts `nM -> uM` (BMCS-SCI-011).

## Fixtures to regenerate

- **positive**: taxa axis with a pinned label set, taxonomy GTDB with its release, rank species,
  quantity relative abundance, `scale: proportion`, normalisation total-sum scaling, assay shotgun,
  host species declared as host.
- **lossy**: counts to relative abundance — library size is lost, approval required.
- **contradiction**: genus vs species rank; 16S vs shotgun; different taxonomy release with no
  mapping.
- **unknown**: taxonomy release absent; normalisation absent.

## Questions for the reviewer

1. Should relative and absolute abundance be separate profiles?
2. Which taxonomy is primary, and must ports declare mappings to the others?
3. Should the compositional nature of relative abundance be enforced by a constraint, and should a
   CLR-transformed vector be a different quantity?
4. How should host and community taxa be distinguished in the contract?
5. Are amplicon sequence variants and OTUs in scope as feature universes alongside named taxa?

## Sources to pin

Gloor et al. 2017 on compositional microbiome data (`10.3389/fmicb.2017.02224`);
`ncbitaxon-schoch-2020`; GTDB's current release paper; `bioregistry-2022`; `stevens-1946`. Each
needs a SHA-256 at sign-off.

## Tests

BMCS-SCI-011; Phase 2 cases for rank mismatch and for counts-to-proportions loss.
