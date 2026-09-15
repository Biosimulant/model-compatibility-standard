# Single Nucleotide Variant — `genome/single-nucleotide-variant@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D2, D4, D7, D10.

## Proposed scientific meaning

A single-base substitution at a position on a declared reference sequence, expressed in a declared
coordinate and notation system, with its reference and alternate alleles. It carries no measured
magnitude: this is an identity assertion, which makes it a useful pilot precisely because the
measurement machinery does not apply.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity (D3). |
| `representation.kind` | Scalar, record, or an array of variants. |
| `representation.reference_assembly` | A variant position means nothing without its assembly. GRCh37 and GRCh38 positions differ for the same variant. |
| `representation.coordinate_system` | 0-based interbase (SPDI, VRS) and 1-based (VCF, HGVS g.) disagree by one. This is the classic silent corruption. |
| `representation.interval_convention` | Half-open vs closed, for consistency with the coordinate system. |
| `identifiers.variant_notation` | VCF, HGVS, SPDI or VRS: the notation defines how to read the value. |
| `representation.reference_allele`, `representation.alternate_allele` | Part of variant identity; a position alone does not identify a substitution. |
| `biological_context.species` | Ties the assembly to an organism; the pair must be consistent. |

**Conditional**

| Field | Condition |
|---|---|
| `representation.reference_sequence` | Required when positions are on a sequence accession rather than a primary assembly chromosome; RefSeq or GenBank accession **with version**. |
| `identifiers.transcript_reference` | Required for transcript-relative notation (HGVS c. or p.); the transcript accession and version are part of the coordinate. |
| `representation.strand` | Required for transcript-relative or strand-sensitive notation. |
| `identifiers.namespace`, `identifiers.namespace_version` | Required when variants are referenced by database identifier (dbSNP rsID, ClinVar) rather than by coordinate; the build or release is then part of the identity. |
| `identifiers.mapping_refs`, `identifiers.unmapped_handling` | Required when a liftover or notation conversion is applied. |
| `representation.left_normalized`, `representation.normalization_tool` | Recommended for SNVs and required once the profile family includes indels, where normalisation decides identity. |
| `semantic.variant_class`, `semantic.consequence` | Required when the port asserts a class or predicted consequence, which depends on a transcript set and an annotation tool version. |

**Recommended.** `origin.method` and `origin.software_version` for the caller; `uncertainty.quality_flags`
for filter status.

**Deliberately not gating.** `measurement.*` — no magnitude is carried, so requiring a unit or scale
here would be meaningless. `biological_context.tissue` — somatic context matters for interpretation
but does not change what the variant *is*; a somatic-variant profile should carry it.
`artifact.*` unless exchanged as a VCF file.

**Proposed new items.** None. The catalogue already carries everything this profile needs, which is
itself a useful finding: the gap is in what is *required*, not in the vocabulary.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `representation.reference_assembly` | equal | unknown | GRCh37 vs GRCh38 is not a direct match; liftover is lossy and can fail per position |
| `representation.coordinate_system` | equal, or declared exact transform | unknown | 0-based to 1-based is a lossless, defined transformation |
| `identifiers.variant_notation` | equal, or declared transform | unknown | VCF to SPDI lossless on the same assembly; HGVS c. needs a transcript |
| `identifiers.namespace` + version | equal, or pinned mapping | unknown | rsIDs merge and split between builds, so the mapping is lossy |
| `biological_context.species` | subsumption (D5) | unknown | Contradiction across species |

## What v0.1 gets wrong here

- No assembly, coordinate system or notation is required. Two ports can agree on every declared
  field and disagree about which base is meant.
- `identifiers.namespace` is required but its positive fixture is `example-namespace`.
- Species is required and human-fixed in the fixture, while the assembly that actually determines
  the coordinate frame is absent.

## Fixtures to regenerate

- **positive**: assembly GRCh38 with its accession, 1-based VCF notation, ref and alt alleles,
  species `NCBITaxon:9606`.
- **lossless**: 1-based VCF to 0-based SPDI on the same assembly.
- **lossy**: GRCh37 to GRCh38 liftover — approval required, with unmapped handling declared.
- **contradiction**: same coordinates on different assemblies; different alternate allele.
- **unknown**: coordinate system absent; transcript absent for HGVS c. notation.

## Questions for the reviewer

1. Should VRS be the canonical internal form, with VCF and HGVS as declared conversions?
2. Are multi-allelic sites in scope, and if so as one port or split records?
3. Should assembly patch level be part of the required assembly declaration?
4. Is predicted consequence in scope at all, given it depends on transcript set and tool version?
5. Should this profile be merged into a general small-variant profile covering indels?

## Sources to pin

GA4GH VRS (Wagner et al. 2021, `10.1016/j.xgen.2021.100027`); SPDI (Holmes et al. 2020,
`10.1093/bioinformatics/btz856`); HGVS nomenclature (den Dunnen et al. 2016,
`10.1002/humu.22981`); the VCF specification (hts-specs, exact version to pin);
`ncbitaxon-schoch-2020`; `bioregistry-2022`. Each needs a SHA-256 at sign-off.

## Tests

No case yet: the defects here are missing requirements rather than wrong answers, so the tests
arrive with the corrected profile in Phase 2. Candidate cases: same coordinates on GRCh37 and
GRCh38 must not be a direct match; 0-based and 1-based declarations of the same variant must be a
lossless conversion.
