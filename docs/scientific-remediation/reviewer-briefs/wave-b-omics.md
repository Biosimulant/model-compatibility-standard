# Wave B — genome, transcriptome, epigenome, proteome, metabolome, lipidome-glycome, multiomics

175 profiles. 5 in the pilot. See the [shared brief](README.md) for what every reviewer is asked to
do and what approval means.

## Who is needed

- A **computational genomicist** for coordinates and variants: assemblies, 0- versus 1-based
  conventions, notation systems, liftover, and identifier lifecycles.
- A **single-cell or bulk transcriptomics analyst** for expression matrices: counts versus
  normalised values, feature universes, sparse encodings, and what a zero means.
- A **mass-spectrometry proteomics or metabolomics specialist** for intensity-based quantities:
  quantification strategies, normalisation, protein grouping, missing values, and calibration.
- An **epigenomics analyst** for methylation: beta and M values, array manifests, and normalisation
  pipelines.

Three or four reviewers, each taking the profiles they can speak to.

## Pilot profiles

| Profile | The question it tests |
|---|---|
| [genome/single-nucleotide-variant](../pilot-profiles/genome--single-nucleotide-variant.md) | Identity without any measured magnitude: assembly, coordinates, notation |
| [transcriptome/single-cell-expression-matrix](../pilot-profiles/transcriptome--single-cell-expression-matrix.md) | Normalisation, feature universe, zeros versus missing |
| [epigenome/methylation-m-value](../pilot-profiles/epigenome--methylation-m-value.md) | A transform-defined quantity, and when the transform is invertible |
| [proteome/protein-abundance](../pilot-profiles/proteome--protein-abundance.md) | A family of quantities sharing one name, in arbitrary units |
| [metabolome/metabolite-concentration](../pilot-profiles/metabolome--metabolite-concentration.md) | Real units, compartments, detection limits, mass versus molar |

## Questions this wave settles for everyone else

1. **What must travel with a normalised value?** Almost every omics profile carries values that are
   only comparable within one pipeline. If the answer is "the full pipeline", the standard has to
   say how much of it, and decision D2 depends on that.
2. **How are feature universes pinned?** A matrix is meaningless without knowing what column *i* is.
   Label digests are the cheap answer; identifier mappings are the expensive one (D7).
3. **When is an identifier mapping lossless?** Ensembl to HGNC is not; Ensembl 110 to 114 nearly is.
   The rule set here becomes the rule for the catalogue.
4. **Should raw and derived values share a profile?** Counts and log-normalised expression in one
   contract, distinguished by a declared quantity, or two profiles?

## Known defects in this wave's profiles

- Raw counts and log-normalised expression compare as DIRECT_COMPATIBLE when both are declared
  (BMCS-SCI-001), as do Ensembl identifiers against HGNC symbols (BMCS-SCI-002).
- Variants on GRCh37 and GRCh38 compare as DIRECT_COMPATIBLE (BMCS-SCI-014).
- Metabolite concentration declares a probability scale (BMCS-SCI-013); `uM` is not a UCUM code.
- The methylation M value declares a ratio scale for a signed, unbounded log ratio.
- Protein abundance is dimensionless with no quantification strategy, so a spectral count and a TMT
  ratio satisfy the same contract.
- Single-cell matrices declare `[sample, feature]` axes and a `dense_vector` representation.
- Identifier namespaces in positive fixtures are the placeholder `example-namespace`.
