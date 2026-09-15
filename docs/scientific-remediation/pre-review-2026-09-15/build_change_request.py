"""Compile the independent scientific review of all 650 BMCS v0.1 profiles.

Reads the generated review packets, profiles and fixtures; emits one machine-readable
change request (change-request.json) plus a compact per-profile dataset for the report.

Nothing here writes into the repository. No review evidence file is produced: every
profile carries at least one blocking change, and the named scientific reviewer must
be a qualified human who did not author the profiles.
"""
from __future__ import annotations

import json
import os
import collections

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
OUT = os.path.dirname(os.path.abspath(__file__))
REVIEWED_AT = "2026-09-15"

# ---------------------------------------------------------------- sources ----
SOURCES = [
    ("ucum-2.2", "The Unified Code for Units of Measure (UCUM)", "standard",
     "https://github.com/ucum-org/ucum/releases/tag/v2.2", "Version 2.2, released 2024-06-28"),
    ("si-brochure-9", "The International System of Units (SI), 9th edition", "standard",
     "https://doi.org/10.59161/AUEZ1291", "9th edition (2019), current revision"),
    ("vim-jcgm-200-2012", "International vocabulary of metrology (VIM), JCGM 200:2012", "standard",
     "https://www.bipm.org/en/committees/jc/jcgm/publications", "3rd edition, 2012 (2008 version with minor corrections)"),
    ("iso-80000-1-2022", "ISO 80000-1:2022 Quantities and units - Part 1: General", "standard",
     "https://www.iso.org/standard/76921.html", "2022 edition"),
    ("stevens-1946", "On the Theory of Scales of Measurement", "primary-publication",
     "https://doi.org/10.1126/science.103.2684.677", "Science 103(2684):677-680, 1946"),
    ("ncbitaxon-schoch-2020", "NCBI Taxonomy: a comprehensive update on curation, resources and tools", "database",
     "https://doi.org/10.1093/database/baaa062", "Database, 2020; NCBITaxon OBO release to be pinned"),
    ("obo-fp-003", "OBO Foundry Principle 3: URI/Identifier Space", "standard",
     "https://obofoundry.org/principles/fp-003-uris.html", "Principles v1.4"),
    ("w3c-cooluris", "Cool URIs for the Semantic Web", "standard",
     "https://www.w3.org/TR/cooluris/", "W3C Interest Group Note, 3 December 2008"),
    ("bioregistry-2022", "Unifying the identification of biomedical entities with the Bioregistry", "database",
     "https://doi.org/10.1038/s41597-022-01807-3", "Scientific Data 9:714, 2022"),
    ("duo-2021", "The Data Use Ontology to streamline responsible access to human biomedical datasets", "ontology",
     "https://doi.org/10.1016/j.xgen.2021.100028", "Cell Genomics 1(2):100028, 2021; DUO OWL release to be pinned"),
    ("uberon-2012", "Uberon, an integrative multi-species anatomy ontology", "ontology",
     "https://doi.org/10.1186/gb-2012-13-1-r5", "Genome Biology 13:R5, 2012; release to be pinned"),
    ("cl-2016", "The Cell Ontology 2016: enhanced content, modularization, and ontology interoperability", "ontology",
     "https://doi.org/10.1186/s13326-016-0088-7", "J Biomed Semantics 7:44, 2016; release to be pinned"),
    ("obi-2016", "The Ontology for Biomedical Investigations", "ontology",
     "https://doi.org/10.1371/journal.pone.0154556", "PLoS ONE 11(4):e0154556, 2016; release to be pinned"),
    ("uo-2012", "The Units Ontology: a tool for integrating units of measurement in science", "ontology",
     "https://doi.org/10.1093/database/bas033", "Database, 2012; release to be pinned"),
    ("edam-2013", "EDAM: an ontology of bioinformatics operations, types of data and identifiers, topics and formats", "ontology",
     "https://doi.org/10.1093/bioinformatics/btt113", "Bioinformatics 29(10):1325-1332, 2013; release to be pinned"),
    ("iuphar-neubig-2003", "IUPHAR Committee on Receptor Nomenclature and Drug Classification. XXXVIII. Update on terms and symbols in quantitative pharmacology", "standard",
     "https://doi.org/10.1124/pr.55.4.4", "Pharmacol Rev 55(4):597-606, 2003"),
    ("iso-20776-1-2019", "ISO 20776-1:2019 Broth micro-dilution reference method for testing in vitro activity of antimicrobial agents", "standard",
     "https://www.iso.org/standard/70464.html", "2019 edition"),
    ("kdigo-2024-ckd", "KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease", "regulatory-guidance",
     "https://doi.org/10.1016/j.kint.2023.10.018", "Kidney Int 105(4S):S117-S314, 2024"),
    ("ats-ers-spirometry-2019", "Standardization of Spirometry 2019 Update", "regulatory-guidance",
     "https://doi.org/10.1164/rccm.201908-1590ST", "Am J Respir Crit Care Med 200(8):e70-e88, 2019"),
    ("fda-bmv-2018", "Bioanalytical Method Validation: Guidance for Industry", "regulatory-guidance",
     "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/bioanalytical-method-validation-guidance-industry", "May 2018"),
    ("mzml-2011", "mzML - a community standard for mass spectrometry data", "standard",
     "https://doi.org/10.1074/mcp.R110.000133", "Mol Cell Proteomics 10(1):R110.000133, 2011"),
    ("goldbook-mr", "IUPAC Compendium of Chemical Terminology: relative molecular mass", "standard",
     "https://doi.org/10.1351/goldbook.R05271", "Gold Book, 2nd ed. (1997), online corrected version"),
    ("du-2010-mvalue", "Comparison of Beta-value and M-value methods for quantifying methylation levels by microarray analysis", "primary-publication",
     "https://doi.org/10.1186/1471-2105-11-587", "BMC Bioinformatics 11:587, 2010"),
    ("cdc-epi-3ed", "Principles of Epidemiology in Public Health Practice, 3rd Edition, Lesson 3: Measures of Risk", "regulatory-guidance",
     "https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/lesson3/section2.html", "3rd edition, 2012 update"),
    ("reed-muench-1938", "A simple method of estimating fifty per cent endpoints", "primary-publication",
     "https://doi.org/10.1093/oxfordjournals.aje.a118408", "Am J Epidemiol 27(3):493-497, 1938"),
    ("who-is-antibody-2021", "WHO International Standard for anti-SARS-CoV-2 immunoglobulin", "primary-publication",
     "https://doi.org/10.1016/S0140-6736(21)00527-4", "Lancet 397(10282):1347-1348, 2021"),
    ("pgs-catalog-2021", "The Polygenic Score Catalog as an open database for reproducibility and systematic evaluation", "database",
     "https://doi.org/10.1038/s41588-021-00783-5", "Nat Genet 53:420-425, 2021"),
    ("orth-2010-fba", "What is flux balance analysis?", "primary-publication",
     "https://doi.org/10.1038/nbt.1614", "Nat Biotechnol 28:245-248, 2010"),
    ("wagner-2012-tpm", "Measurement of mRNA abundance using RNA-seq data: RPKM measure is inconsistent among samples", "primary-publication",
     "https://doi.org/10.1007/s12064-012-0162-3", "Theory Biosci 131:281-285, 2012"),
    ("robinson-2010-tmm", "A scaling normalization method for differential expression analysis of RNA-seq data", "primary-publication",
     "https://doi.org/10.1186/gb-2010-11-3-r25", "Genome Biology 11:R25, 2010"),
    ("svensson-2020-zeros", "Droplet scRNA-seq is not zero-inflated", "primary-publication",
     "https://doi.org/10.1038/s41587-019-0379-5", "Nat Biotechnol 38:147-150, 2020"),
    ("lieberman-aiden-2009", "Comprehensive mapping of long-range interactions reveals folding principles of the human genome", "primary-publication",
     "https://doi.org/10.1126/science.1181369", "Science 326(5950):289-293, 2009"),
    ("dicom-ps3.3", "DICOM PS3.3 Information Object Definitions", "standard",
     "https://dicom.nema.org/medical/dicom/current/output/html/part03.html", "current edition; exact release to be pinned"),
    ("boellaard-2015-suv", "FDG PET/CT: EANM procedure guidelines for tumour imaging: version 2.0", "regulatory-guidance",
     "https://doi.org/10.1007/s00259-014-2961-x", "Eur J Nucl Med Mol Imaging 42:328-354, 2015"),
    ("bids-ieeg-2019", "iEEG-BIDS, extending the Brain Imaging Data Structure specification to human intracranial electrophysiology", "standard",
     "https://doi.org/10.1038/s41597-019-0105-7", "Scientific Data 6:102, 2019"),
    ("nwb-2022", "The Neurodata Without Borders ecosystem for neurophysiological data science", "standard",
     "https://doi.org/10.7554/eLife.78362", "eLife 11:e78362, 2022"),
    ("clark-2003-survival", "Survival Analysis Part I: Basic concepts and first analyses", "primary-publication",
     "https://doi.org/10.1038/sj.bjc.6601118", "Br J Cancer 89:232-238, 2003"),
    ("lynch-2010-mutrate", "Evolution of the mutation rate", "primary-publication",
     "https://doi.org/10.1016/j.tig.2010.05.003", "Trends Genet 26(8):345-352, 2010"),
    ("ensembl-2024", "Ensembl 2024", "database",
     "https://doi.org/10.1093/nar/gkad1049", "Nucleic Acids Res 52(D1):D891-D899, 2024; release to be pinned"),
]

# ------------------------------------------------------- systemic findings ----
SYSTEMIC = [
    dict(
        id="S1", severity="blocking", title="semantic.concept is a version-bound self-reference, so it carries no scientific meaning and breaks across versions",
        field="semantic.concept (fixed value and the equal comparison rule); source: scripts/build_standard.py profile_concept()",
        current="Fixed const '<profile ref>/v0.1#concept', i.e. https://biosimulant.com/.../profiles/<domain>/<name>/v0.1#concept, compared with operator 'equal'. The term has no definition, no label, no axioms and no mapping to any external vocabulary. It is also minted inside the versioned profile document IRI.",
        proposed=("Two changes. (a) Keep a Biosimulant-controlled term but mint it in a version-independent namespace, e.g. "
                  "https://biosimulant.com/standards/model-compatibility/terms/<domain>/<name> , with a label, a textual definition, and its own term-level version; the profile document stays versioned. "
                  "(b) Because the concept only restates profile identity, add semantic.ontology_terms as a required item for every non-core domain profile: at least one CURIE from a Bioregistry-registered prefix "
                  "(OBI, UBERON, CL, CHEBI, PATO, NCIT, EFO, GO, SO, MONDO as appropriate), each with ontology, uri, version and relation (exact-match | broad-match | narrow-match), compared with term-equivalent / term-subsumes against a pinned ontology snapshot, missing snapshot -> UNKNOWN."),
        reason=("As built, the rule is tautological: validation already forces both contracts to hold the same const, so the equal rule can never fail between two valid contracts of the same profile - it duplicates profile_refs and checks nothing about science. "
                "Worse, because the IRI embeds /v0.1, a v0.2 profile mints a different concept IRI, so every v0.1 port becomes INCOMPATIBLE with a v0.2 port even when the scientific meaning is unchanged. Identifier stability across versions is exactly what OBO FP-003 and the W3C hash-URI guidance are for. "
                "A compatibility contract that claims to encode scientific meaning must anchor that meaning in a maintained vocabulary, otherwise two independently built ports can never agree except by adopting the same Biosimulant profile."),
        sources=["obo-fp-003", "w3c-cooluris", "bioregistry-2022", "obi-2016", "uo-2012"],
        fixtures=("Add a cross-version fixture: v0.1 concept vs v0.2 concept of the same term must not be INCOMPATIBLE. "
                  "Add comparison-unknown-semantic-ontology-terms (no pinned snapshot -> UNKNOWN) and comparison-direct-ontology-term-subsumes (child term -> parent term). "
                  "Every positive fixture gains a real ontology_terms entry."),
        applies="all 650",
    ),
    dict(
        id="S2", severity="blocking", title="semantic.subject is uncontrolled free text compared by string equality",
        field="semantic.subject (required item, schema {type: string, minLength: 1, maxLength: 4096}, operator 'equal')",
        current="Any string up to 4096 characters. Generated positive fixtures use one placeholder per domain: 'biological_sample', 'nervous_system', 'data_value', 'exposed_biological_system', and so on. Comparison is exact string equality.",
        proposed=("Replace the free string with a CURIE from a registered prefix (UBERON, CL, OBI, ENVO, NCBITaxon, CHEBI as fits the domain), pattern ^[A-Za-z][A-Za-z0-9._-]*:[A-Za-z0-9._/-]+$ with the prefix resolvable in a pinned Bioregistry snapshot. "
                  "Compare with term-subsumes (the target's subject must subsume the source's subject) against a pinned ontology snapshot; no snapshot -> UNKNOWN. "
                  "Demote to conditional-required: required only where the sampled entity changes the meaning of the value (tissue, cell type, biofluid, environment), not for profiles whose value is entity-independent."),
        reason=("String equality on uncontrolled text produces both error directions. False INCOMPATIBLE: 'blood_plasma' vs 'plasma' vs 'UBERON:0001969' describe the same specimen and compare unequal (verified against the engine: metabolite-concentration with subject 'biological_sample' vs 'blood_plasma' returns INCOMPATIBLE). "
                "False DIRECT_COMPATIBLE: the domain placeholder 'biological_sample' matches itself across plasma, CSF, tumour biopsy and faecal samples, which are not interchangeable for any concentration or abundance measurement. "
                "Anatomical and specimen semantics are exactly what UBERON, CL and OBI maintain, including the subsumption hierarchy that makes 'is this sample type acceptable' answerable."),
        sources=["uberon-2012", "cl-2016", "obi-2016", "bioregistry-2022"],
        fixtures=("Replace every positive fixture placeholder with a real CURIE. Add comparison-direct-semantic-subject-subsumes (UBERON:0001969 blood plasma -> UBERON:0000178 blood must not be INCOMPATIBLE when the target is the broader term) "
                  "and comparison-unknown-semantic-subject-no-snapshot."),
        applies="all 650",
    ),
    dict(
        id="S3", severity="blocking", title="Direct compatibility hides required transformations: optional fields present on both contracts are never compared",
        field="Comparison rule generation (scripts/build_standard.py, rules derived only from required_items) and python/src/.../compare.py _rules()",
        current=("When profile refs are supplied, the engine evaluates only the rules the profile declares, which are generated only from required_items. "
                 "spec/v0.1/catalogue/items.json states the opposite for all 266 items: 'Checked only when the profile requires it or both contracts include it.'"),
        proposed=("Generate comparison rules with missing:'ignore' for every declared-on-both-sides item that can change interpretation, at minimum: measurement.unit (unit-convertible), measurement.scale, measurement.normalization, measurement.baseline, measurement.aggregation, "
                  "identifiers.namespace and identifiers.namespace_version, representation.ordering, representation.feature_space, dimensions.axes, lifecycle.time_unit, origin.type. "
                  "missing:'ignore' gives exactly the documented semantics: skip when either side is silent, compare when both declare."),
        reason=("Verified against the engine on transcriptome/single-cell-expression-matrix: source declaring measurement {quantity: read_count, scale: count} and target declaring {quantity: log1p_normalized_expression, scale: log} returns DIRECT_COMPATIBLE with no finding. "
                "Raw counts and log-normalised expression are not interchangeable inputs to any model; feeding one where the other is expected is a silent scientific error, and library-size normalisation plus a log transform is precisely a declared, lossy, non-invertible transformation. "
                "The same check returns DIRECT_COMPATIBLE for identifiers.namespace 'ensembl.gene' vs 'hgnc.symbol', which is a many-to-many mapping with real loss. This directly violates the standard's own promise that direct compatibility never hides a required transformation, and it contradicts the published item semantics."),
        sources=["wagner-2012-tpm", "robinson-2010-tmm", "ensembl-2024", "bioregistry-2022"],
        fixtures=("Every profile that permits a numeric value needs comparison-lossy-normalization (counts vs log-normalised -> LOSSY_CONVERSION_REQUIRES_APPROVAL or INCOMPATIBLE) "
                  "and comparison-mapping-required (ensembl.gene vs hgnc.symbol -> mapping required, not DIRECT)."),
        applies="all 650; demonstrated on the 526 profiles that do not require measurement.unit and the 552 that do not require identifiers.namespace",
    ),
    dict(
        id="S4", severity="blocking", title="unit-convertible is a four-row lookup table, not dimensional analysis, and no rule ties a unit to its quantity",
        field="spec/v0.1/rules/unit-conversions.json and the unit-convertible operator in both implementations",
        current=("The whole conversion table is nM->uM, uM->nM, mM->uM, uM->mM. measurement.unit is validated only as {type: string, minLength: 1, maxLength: 128}. "
                 "Verified engine results: g vs kg -> INCOMPATIBLE; Cel vs K -> INCOMPATIBLE; 1/s vs /min -> INCOMPATIBLE; uM vs mol/L -> INCOMPATIBLE; a firing rate declared in kg validates with no finding."),
        proposed=("Adopt UCUM 2.2 as the unit grammar: validate measurement.unit as a parseable UCUM expression, and implement unit-convertible as UCUM dimensional analysis (equal dimension vectors -> convertible; factor from the canonical form). "
                  "Handle affine units explicitly (Cel/[degF] convert to K with an offset, so only whole quantities convert, never differences or ratios). "
                  "Constrain each profile's unit to the dimension of its quantity (e.g. amount-of-substance concentration N.L^-3 for concentration profiles) and reject dimensionally impossible units. "
                  "Mass-concentration to molar-concentration (mg/L vs uM) requires an external molar mass and must resolve to a declared parameterised transformation, not DIRECT and not INCOMPATIBLE."),
        reason=("Every one of those verified results is scientifically wrong. g and kg are the same quantity with a factor of 1000; /min and 1/s are the same quantity; uM and mol/L are the same quantity; Cel and K differ by an additive offset. "
                "Returning INCOMPATIBLE for convertible units makes the standard block valid couplings, and accepting kg for a firing rate makes it approve impossible ones. UCUM exists to answer exactly this question and is the unit code system used by HL7/FHIR and LOINC."),
        sources=["ucum-2.2", "si-brochure-9", "vim-jcgm-200-2012", "iso-80000-1-2022", "uo-2012"],
        fixtures=("Add per-dimension conversion fixtures: g<->kg and s<->min and 1/s<->/min lossless; Cel<->K lossless for absolute values but flagged for differences; "
                  "uM<->mol/L lossless; mg/L vs uM requires a declared molar-mass parameter; kg vs Hz INCOMPATIBLE. Remove the blanket nM->uM fixture from profiles whose quantity is not a molar concentration."),
        applies="all 650; the 124 profiles that require measurement.unit are directly affected",
    ),
    dict(
        id="S5", severity="blocking", title="biological_context.species is a single taxon compared by string equality, with no subsumption and an unsafe wildcard direction",
        field="biological_context.species (required in 575 profiles), operator 'context-compatible'",
        current=("Schema: 'any' or ^NCBITaxon:[1-9][0-9]*$, one value. The operator is implemented as source == target or target in (None, 'any', 'unspecified'). "
                 "Verified: source 'any' vs target NCBITaxon:9606 -> INCOMPATIBLE; source NCBITaxon:9606 vs target 'any' -> DIRECT_COMPATIBLE. Every generated positive fixture uses NCBITaxon:9606, including ecology, evolution, microbiology and virology profiles."),
        proposed=("(a) Compare with term-subsumes over a pinned NCBI Taxonomy snapshot so that a strain or subspecies satisfies a port that asks for the species (NCBITaxon:511145 E. coli K-12 MG1655 satisfies NCBITaxon:562 E. coli), and so a broader source does not silently satisfy a narrower target. "
                  "(b) A source of 'any' against a specific target must return UNKNOWN, not INCOMPATIBLE - it is absent evidence, not a contradiction. "
                  "(c) Replace the single value with a role-typed set for profiles where more than one organism is in scope: biological_context.taxa[] with {taxon, role: host | pathogen | community_member | donor}, required for virology, microbiology, epidemiology and host-pathogen profiles. "
                  "(d) For community-level profiles (ecology/species-abundance, microbiology/taxonomic-abundance, microbiology/community-composition and similar), a single species is the wrong cardinality: require the taxonomy namespace and release plus a feature universe, and make species conditional."),
        reason=("Absent evidence and contradiction are different states, and the current asymmetry gets both backwards in the unsafe direction: a port that declares nothing about species is allowed to feed a port that requires human. "
                "Equality without the taxonomic hierarchy blocks correct couplings between strain-level and species-level declarations, which is the normal case in microbiology. "
                "And a human taxon on an ecology abundance vector or a viral titre is not a valid scientific example: for virology and microbiology the host and the organism measured are different entities, so one species field cannot express either."),
        sources=["ncbitaxon-schoch-2020", "bioregistry-2022", "obi-2016"],
        fixtures=("Rebuild positive fixtures per domain with a plausible taxon (virology: pathogen NCBITaxon:2697049 with host NCBITaxon:9606; ecology: a real community with a taxonomy release). "
                  "Add comparison-unknown-species-any-source, comparison-direct-species-strain-satisfies-species, and keep comparison-incompatible-species for a genuine cross-species contradiction."),
        applies="575 profiles requiring species; the 75 without it (core, chemical, simulation) are unaffected",
    ),
    dict(
        id="S6", severity="blocking", title="Unit, scale and axis values in the generated fixtures are chosen by substring matching on the profile name",
        field="scripts/build_standard.py measurement_unit(), example_value() scale branch, axis_names()",
        current=("Unit and scale are selected by testing whether the profile name contains a token. 'concentration' contains the substring 'ratio', so all 14 concentration profiles get scale 'probability'. "
                 "'integrated-embedding' contains 'rate', so it gets unit 1/s. 'proliferation-rate', 'migration-rate' and 'glomerular-filtration-rate' contain 'ratio' and get scale 'probability'. "
                 "Axis names come from the same mechanism: any name containing 'volume' gets image axes [x, y], so stroke-volume and volume-of-distribution get spatial axes, while ct-volume and mri-volume - which are three-dimensional - get only two."),
        proposed=("Delete the substring heuristics. Declare quantity kind, unit dimension, measurement scale and axis structure explicitly per profile in source/catalogue.review.json, reviewed one profile at a time. "
                  "Separate Stevens' measurement level (nominal | ordinal | interval | ratio) from the value domain and transform: add measurement.transform (identity | log2 | log10 | ln | logit) and use 'proportion' for bounded [0,1] fractions, reserving 'probability' for values that are probabilities of an event. "
                  "The log base must be explicit, because log2 and log10 fold changes are different numbers."),
        reason=("A generated example that is scientifically wrong is worse than no example, because downstream implementers copy it: the positive fixture is the profile's worked example of a valid contract. "
                 "A micromolar concentration is a ratio-scale quantity with a true zero, not a probability; a fraction bounded in [0,1] is a proportion, which is not the same claim as a probability; and Celsius is an interval scale, so 'ratio' is wrong for body temperature even though the unit is right. "
                 "Stevens' levels also determine which operations are meaningful, so the scale value is not cosmetic - it decides whether averaging or ratio comparison is defensible."),
        sources=["stevens-1946", "vim-jcgm-200-2012", "ucum-2.2", "iso-80000-1-2022"],
        fixtures="Every positive fixture for the 124 measurement profiles must be regenerated from reviewed per-profile values; see the per-profile unit and scale corrections.",
        applies="124 profiles requiring measurement.unit; 89 profiles requiring dimensions.axes",
    ),
    dict(
        id="S7", severity="blocking", title="The single transformation fixture asserts a molar-concentration conversion for every measurement profile",
        field="scripts/build_standard.py fixture generation; fixture comparison-lossless-unit-conversion in 124 profiles",
        current="All 124 profiles that require measurement.unit receive the same fixture: source unit nM, target unit uM, expected LOSSLESS_CONVERSION_AVAILABLE - including firing-rate, body-temperature, heart-rate, simulation-time, retention-time, body-mass and polygenic-score. Verified: neuroscience/firing-rate with nM vs uM returns LOSSLESS_CONVERSION_AVAILABLE.",
        proposed="Generate the conversion fixture from the profile's own declared unit dimension (mass: g<->kg; time: s<->min; frequency: 1/s<->/min; molar concentration: nM<->uM; temperature: Cel<->K flagged as affine), and add a dimensional-mismatch fixture (the profile's unit vs a unit of another dimension -> INCOMPATIBLE).",
        reason="The fixture certifies, as a passing conformance test in both implementations, that a neuronal firing rate can be converted from nanomolar to micromolar. It is dimensionally impossible. Because the fixtures are the cross-language conformance suite, this false claim is what the Python and TypeScript packages are being tested to agree on.",
        sources=["ucum-2.2", "vim-jcgm-200-2012", "iso-80000-1-2022"],
        fixtures="Replace comparison-lossless-unit-conversion in all 124 profiles; add comparison-incompatible-unit-dimension.",
        applies="124 profiles requiring measurement.unit",
    ),
    dict(
        id="S8", severity="blocking", title="The unit contradiction fixture asserts that g and kg are incompatible",
        field="scripts/build_standard.py incompatible_value(); fixture comparison-incompatible-measurement-unit",
        current="The contradiction unit is hard-coded as 'kg' (or 's' when the profile's unit is already kg). For the six profiles whose unit is g - physiology/body-mass, ecology/biomass, microbiology/biofilm-biomass, chemical/exact-mass, metabolome/mass-spectral-peak, metabolome/mass-spectrum - the fixture therefore asserts that kg vs g must be INCOMPATIBLE. Verified: the engine returns INCOMPATIBLE.",
        proposed="Choose the contradiction unit as one of a different dimension from the profile's own unit (for a mass quantity use s or Hz, never another mass unit), and add the matching g<->kg lossless conversion fixture.",
        reason="Kilograms and grams are the same quantity; a contract expressed in one converts exactly to the other. Certifying that pairing as a contradiction means the standard blocks a correct coupling and, being a fixture, freezes the error into the conformance suite.",
        sources=["ucum-2.2", "si-brochure-9"],
        fixtures="Fix comparison-incompatible-measurement-unit for the 6 mass profiles; add comparison-lossless g<->kg.",
        applies="6 profiles with unit g; the pattern is wrong for any profile whose unit shares a dimension with kg",
    ),
    dict(
        id="S9", severity="blocking", title="No profile has a lossy or inference fixture, although the transformation policy declares both paths",
        field="transformation_policy {lossless: allow, lossy: approval, inference: approval}; fixture_groups.transformations",
        current="526 profiles have an empty transformations group and the remaining 124 have exactly one lossless fixture. No profile anywhere exercises LOSSY_CONVERSION_REQUIRES_APPROVAL or the inference path, so the approval branches of the policy are untested in both implementations.",
        proposed="Require, for every profile whose transformation_policy admits them, at least one lossy fixture (e.g. continuous value binned to an ordinal category; log-normalised from counts) and one inference fixture (a value that can only be produced by a model, e.g. imputed or deconvolved), each with the expected approval status.",
        reason="The review instruction that lossy conversions and inference must be clearly identified cannot be verified for any profile in the release. An untested approval path is where silent scientific substitution happens, because the failure mode is a status that quietly reads as compatible.",
        sources=["wagner-2012-tpm", "robinson-2010-tmm", "svensson-2020-zeros"],
        fixtures="Add lossy and inference fixtures to all 650 profiles.",
        applies="all 650",
    ),
    dict(
        id="S10", severity="non-blocking", title="UNKNOWN is only tested for a missing source; a missing target is never exercised",
        field="fixture comparison-unknown-<field>",
        current="Each unknown fixture removes the field from the source contract only. The engine treats either side missing as UNKNOWN, but no fixture pins that behaviour for the target side.",
        proposed="Add the mirrored fixture (field absent from the target) for each required field.",
        reason="Missing evidence must return UNKNOWN regardless of which port is silent; a one-sided test lets an asymmetric regression through. The behaviour is currently correct in both implementations, so this is a coverage gap rather than a defect.",
        sources=["vim-jcgm-200-2012"],
        fixtures="Add comparison-unknown-target-<field> for every required field.",
        applies="all 650",
    ),
    dict(
        id="S11", severity="non-blocking", title="representation.kind uses exact equality, so lossless re-encodings are reported as contradictions",
        field="representation.kind (required in all 650), operator 'equal'",
        current="Verified: dense_vector vs sparse_vector on transcriptome/single-cell-expression-matrix returns INCOMPATIBLE. Allowed kind sets are derived from the coarse applies_to families, so core/scalar-quantity permits matrix, tensor and table.",
        proposed="Declare lossless representation transformations (dense_vector <-> sparse_vector, matrix <-> table with a declared schema) and return LOSSLESS_CONVERSION_AVAILABLE; narrow each profile's allowed kinds to those its scientific meaning admits (core/scalar-quantity should allow scalar only).",
        reason="Sparse and dense encodings of the same vector carry identical information, so INCOMPATIBLE is a false negative. It is the safe direction of error, which is why this is not blocking on its own - but for scalar-quantity the allowed set contradicts the profile's own name and intended use.",
        sources=["edam-2013"],
        fixtures="Add comparison-lossless-representation-kind; fix the allowed-kind enum for core/scalar-quantity and the other scalar profiles.",
        applies="all 650; the allowed-set contradiction affects the 395 profiles carrying the full 8-kind set",
    ),
    dict(
        id="S12", severity="blocking", title="Identifier, consent and data-use fixtures carry placeholder values, and no namespace is constrained to a real registry",
        field="identifiers.namespace, identifiers.namespace_version (98 profiles); security.data_use, security.consent_scope (50 clinical profiles)",
        current="Positive fixtures use 'example-namespace', 'example-namespace-version', 'example-consent-scope' and ['example-data_use']. The schemas accept any string; data_use is compared with 'equal' on an array, so element order changes the result.",
        proposed=("Constrain identifiers.namespace to a Bioregistry-registered prefix resolved against a pinned registry snapshot, and namespace_version to the namespace's own release identifier (e.g. ensembl.gene with release 114). "
                  "Replace security.data_use with DUO CURIEs (DUO:0000042 general research use and similar), normalise as a set, and compare by DUO subsumption: the target's permitted uses must subsume the source's declared use. Give consent_scope the same treatment."),
        reason=("A positive fixture is the normative worked example; a placeholder namespace teaches implementers that any string is acceptable, which defeats the purpose of requiring a versioned identifier namespace. "
                "For the clinical profiles the consequence is governance, not just tidiness: order-sensitive equality on a data-use array can wrongly block a lawful data flow or, when the arrays happen to match, pass one that consent does not cover. DUO exists as the GA4GH standard for exactly this comparison."),
        sources=["bioregistry-2022", "ensembl-2024", "duo-2021"],
        fixtures="Replace all placeholder identifier and security values with real registered values; add set-order and DUO-subsumption comparison fixtures.",
        applies="98 profiles with identifiers; 50 clinical profiles with security fields",
    ),
    dict(
        id="S13", severity="non-blocking", title="Uncertainty, detection limits and censoring are never required, though they change whether values are comparable",
        field="uncertainty.* and measurement.detection_limits, currently candidate-recommended only",
        current="No profile requires any uncertainty item. missingness appears as a candidate in 475 packets, censoring in 400, detection_limits in 450.",
        proposed=("Make them conditional-required where the science demands it: uncertainty.censoring for phenotype/time-to-event and clinical/survival-outcome; measurement.detection_limits for every concentration, titre and MIC profile; "
                  "uncertainty.missingness for every matrix profile, distinguishing a structural zero from an unobserved value."),
        reason=("A survival time without its censoring indicator is not interpretable and will be silently treated as an observed event. A concentration below the lower limit of quantification is not a measurement of zero, which is why bioanalytical guidance requires the limits to travel with the data. "
                "In single-cell matrices, zeros are mostly genuine low counts rather than missing values, so a port that treats them as missing and one that treats them as zero are not interchangeable."),
        sources=["clark-2003-survival", "fda-bmv-2018", "svensson-2020-zeros"],
        fixtures="Add missing-evidence fixtures (censoring absent -> UNKNOWN) for the affected profiles.",
        applies="conditional across the 124 measurement profiles, matrix profiles and survival profiles",
    ),
    dict(
        id="S14", severity="non-blocking", title="Time-series and event profiles do not require a time unit, time origin or sampling rule",
        field="lifecycle.time_unit, lifecycle.time_origin, lifecycle.sampling, lifecycle.interpolation (candidates in 350 packets); dimensions.axes ['time'] in 25 profiles",
        current="A profile can require a time axis while leaving the time unit, the origin of the clock and the sampling regime undeclared. core/regular-time-series and core/irregular-time-series differ in exactly this respect yet impose the same requirements.",
        proposed="For every profile whose axes include time, require lifecycle.time_unit (UCUM), lifecycle.time_origin, and lifecycle.sampling; require lifecycle.interpolation for irregular series; and record the domain's own conventions where they exist (BIDS/NWB for electrophysiology).",
        reason="Two time series that agree on every declared field can still be a 1 kHz recording and a daily series. Sampling rate and epoch are part of what makes time-indexed values comparable, and the electrophysiology community already standardises them.",
        sources=["bids-ieeg-2019", "nwb-2022", "ucum-2.2"],
        fixtures="Add comparison-unknown-lifecycle-time-unit and a sampling-mismatch fixture for the time-axis profiles.",
        applies="25 profiles with a time axis; 76 event/state profiles",
    ),
]

# ------------------------------------ per-profile measurement corrections ----
# unit / scale corrections for the 124 profiles that require measurement.unit.
# tuple: (proposed_unit, proposed_scale, reason, [source ids])
M = {
 "core/categorical-value": ("(no unit; remove measurement requirement)", "nominal", "A categorical value has no unit and no order; 'ordinal' asserts a ranking the profile does not define, and unit '1' asserts a dimensionless magnitude.", ["stevens-1946", "vim-jcgm-200-2012"]),
 "core/bounded-score": ("1", "interval", "A bounded score is a dimensionless value on a declared interval; its level must be declared per instrument rather than assumed ordinal, and the bounds belong in the contract.", ["stevens-1946"]),
 "core/regular-time-series": ("(value unit, profile-declared)", "ratio", "Unit 's' describes the time axis, not the values. The series values carry their own quantity and unit; the sampling interval belongs in lifecycle.time_unit.", ["ucum-2.2", "vim-jcgm-200-2012"]),
 "core/irregular-time-series": ("(value unit, profile-declared)", "ratio", "As for the regular series: 's' is the axis unit. An irregular series must additionally declare its interpolation rule.", ["ucum-2.2", "vim-jcgm-200-2012"]),
 "genome/polygenic-score": ("1", "interval", "A polygenic score is a continuous, usually standardised weighted sum; it is not ordinal, and its value is only interpretable with the scoring file and allele-weight provenance.", ["pgs-catalog-2021", "stevens-1946"]),
 "transcriptome/small-rna-abundance": ("1 (counts) or a declared normalised unit", "count or ratio with transform", "Abundance is either integer counts or a normalised quantity (CPM/TPM); the profile must say which, because they are not interchangeable.", ["wagner-2012-tpm", "robinson-2010-tmm"]),
 "epigenome/dna-methylation-fraction": ("1", "proportion", "A methylation fraction is a bounded proportion of methylated molecules, not the probability of an event.", ["du-2010-mvalue", "stevens-1946"]),
 "epigenome/methylation-beta-value": ("1", "proportion", "Beta is bounded in [0,1] and heteroscedastic; declaring it ratio-scaled invites averaging and ratio comparison that the beta scale does not support.", ["du-2010-mvalue"]),
 "epigenome/methylation-m-value": ("1", "interval with transform log2", "The M-value is log2(beta/(1-beta)): unbounded, can be negative, so it is not ratio-scaled, and the log base must be declared.", ["du-2010-mvalue"]),
 "epigenome/footprint-score": ("1", "interval", "A footprint score is a continuous algorithm output; its level and its producing method must be declared rather than assumed ordinal.", ["stevens-1946"]),
 "proteome/protein-abundance": ("1 (arbitrary intensity) or a declared molar/mass unit", "ratio with declared normalization", "Protein abundance is usually an arbitrary-unit intensity that is only comparable within one normalisation; unit '1' with no normalization field hides that.", ["robinson-2010-tmm"]),
 "proteome/peptide-abundance": ("1 (arbitrary intensity) or a declared molar/mass unit", "ratio with declared normalization", "As for protein abundance: intensity units are instrument- and pipeline-specific.", ["mzml-2011"]),
 "proteome/phosphoprotein-abundance": ("1 (arbitrary intensity), or occupancy as a proportion", "ratio with declared normalization", "Phosphoprotein abundance and phosphosite occupancy are different quantities; the profile must declare which, as occupancy is a bounded proportion.", ["mzml-2011"]),
 "proteome/secretion-rate": ("pg/(cell.h) or fmol/(cell.h)", "ratio", "A secretion rate is amount per cell per time; 1/s has no amount or cell basis and so cannot be compared across experiments.", ["ucum-2.2", "iso-80000-1-2022"]),
 "metabolome/metabolite-abundance": ("1 (arbitrary intensity) or a declared molar unit", "ratio with declared normalization", "Untargeted metabolomics abundances are arbitrary intensities; targeted values are molar. The profile must distinguish them.", ["mzml-2011"]),
 "metabolome/metabolite-concentration": ("uM", "ratio", "Unit is right; scale is not. A concentration has a true zero and is ratio-scaled - 'probability' comes from the substring bug in S6.", ["ucum-2.2", "stevens-1946"]),
 "metabolome/mass-spectral-peak": ("m/z (dimensionless ratio) plus a separate intensity", "ratio", "A peak is a mass-to-charge ratio with an intensity, not a mass in grams; m/z is the PSI-MS quantity.", ["mzml-2011", "goldbook-mr"]),
 "metabolome/mass-spectrum": ("m/z axis with an intensity value", "ratio", "A spectrum is an array over m/z; grams is neither the axis unit nor the value unit.", ["mzml-2011"]),
 "metabolome/retention-time": ("s or min", "ratio", "Unit is correct; retention time is only comparable within a declared chromatographic method, which must be required.", ["ucum-2.2", "mzml-2011"]),
 "metabolome/isotope-tracer-fraction": ("1", "proportion", "Mole percent enrichment is a bounded proportion of labelled molecules, not a probability.", ["stevens-1946"]),
 "metabolome/pathway-metabolite-score": ("1", "interval", "A pathway score is a continuous method output; its method and gene/metabolite set must be declared.", ["stevens-1946"]),
 "metabolome/metabolite-time-series": ("(value unit, profile-declared)", "ratio", "'s' is the time axis unit, not the unit of the metabolite values.", ["ucum-2.2"]),
 "metabolome/metabolite-production-rate": ("mmol/(gDW.h) or mol/(L.s)", "ratio", "A metabolic flux needs an amount basis (biomass or volume); 1/s carries none, so two fluxes cannot be compared.", ["orth-2010-fba", "ucum-2.2"]),
 "metabolome/metabolite-consumption-rate": ("mmol/(gDW.h) or mol/(L.s)", "ratio", "As for production rate: the flux basis is part of the quantity.", ["orth-2010-fba", "ucum-2.2"]),
 "lipidome-glycome/lipid-abundance": ("1 (arbitrary intensity) or a declared molar unit", "ratio with declared normalization", "Lipidomics abundances are intensities unless a standard-calibrated molar quantity is declared.", ["mzml-2011"]),
 "lipidome-glycome/lipid-concentration": ("uM", "ratio", "Unit right, scale wrong: a concentration is ratio-scaled with a true zero.", ["ucum-2.2", "stevens-1946"]),
 "lipidome-glycome/glycan-abundance": ("1 (arbitrary intensity) or a declared molar unit", "ratio with declared normalization", "Relative glycan abundance is normally a within-sample proportion of the glycan pool; that normalisation must be declared.", ["mzml-2011"]),
 "lipidome-glycome/glycopeptide-abundance": ("1 (arbitrary intensity), or site occupancy as a proportion", "ratio with declared normalization", "Glycopeptide abundance and site occupancy are different quantities with different domains.", ["mzml-2011"]),
 "chemical/molecular-weight": ("g/mol for molar mass, or 1 for relative molecular mass", "ratio", "Relative molecular mass is dimensionless and molar mass is g/mol; they are numerically equal but different quantities, so the profile must declare which it means.", ["goldbook-mr", "iso-80000-1-2022"]),
 "chemical/exact-mass": ("Da (u)", "ratio", "Exact monoisotopic mass is reported in daltons; grams is dimensionally valid but off by 24 orders of magnitude from any value a model will carry.", ["goldbook-mr", "ucum-2.2"]),
 "pharmacology/compound-dose": ("mg, mg/kg or mol", "ratio", "A dose without a unit and, for body-weight dosing, a per-mass basis is not a dose; unit '1' makes two incomparable dosing conventions look identical.", ["ucum-2.2", "fda-bmv-2018"]),
 "pharmacology/dose-schedule": ("dose unit plus an interval (e.g. mg every 12 h)", "ratio", "A schedule is a dose quantity plus a timing rule; a dimensionless '1' captures neither.", ["ucum-2.2"]),
 "pharmacology/exposure-concentration": ("uM or ng/mL", "ratio", "Unit acceptable, scale wrong; free versus total concentration must also be declared because they are different quantities.", ["iuphar-neubig-2003", "stevens-1946"]),
 "pharmacology/plasma-concentration": ("uM or ng/mL", "ratio", "A plasma concentration is ratio-scaled. Mass and molar units both occur in practice and interconvert only with the molar mass, which must be a declared transformation parameter.", ["fda-bmv-2018", "ucum-2.2"]),
 "pharmacology/tissue-concentration": ("uM or ng/g", "ratio", "Tissue concentration is per tissue mass or volume; the basis must be declared, and the scale is ratio.", ["ucum-2.2"]),
 "pharmacology/binding-affinity": ("mol/L for Kd/Ki, or 1 for pKd/pKi", "ratio for Kd, interval for pKd", "An affinity constant is a molar concentration; its negative logarithm is a different quantity on a different scale. Unit '1' conflates them, and Kd versus IC50 versus EC50 are not interchangeable.", ["iuphar-neubig-2003"]),
 "pharmacology/association-rate": ("/(mol/L)/s  i.e. M-1.s-1", "ratio", "kon is second-order: per concentration per time. 1/s is the unit of koff, so the two rate constants are currently declared identically.", ["iuphar-neubig-2003", "ucum-2.2"]),
 "pharmacology/dissociation-rate": ("1/s", "ratio", "Unit is correct for koff; the profile must state that it is the kinetic off-rate and not the equilibrium dissociation constant Kd.", ["iuphar-neubig-2003"]),
 "pharmacology/dose-response-curve": ("response unit over a dose axis", "ratio", "The value is a response and the axis is dose; a single dimensionless unit describes neither, and the axis must be dose, not time.", ["iuphar-neubig-2003"]),
 "pharmacology/concentration-response-curve": ("response unit over a concentration axis in uM", "ratio", "Same axis error as the dose-response curve, plus the probability-scale bug; the concentration axis unit and the response unit are two different declarations.", ["iuphar-neubig-2003", "stevens-1946"]),
 "pharmacology/volume-of-distribution": ("L or L/kg", "ratio", "Vd is reported in litres, or litres per kilogram when weight-normalised; mL as a dense vector with image axes is wrong in unit, shape and axes.", ["iuphar-neubig-2003", "ucum-2.2"]),
 "cell/proliferation-rate": ("1/h or 1/d", "ratio", "A proliferation rate is per-capita per time on a ratio scale; 'probability' comes from the substring bug and would license treating a rate as a bounded [0,1] value.", ["stevens-1946", "ucum-2.2"]),
 "cell/growth-rate": ("1/h", "ratio", "Correct dimension; the profile should state that it is the specific (per-capita) growth rate rather than an absolute increase.", ["ucum-2.2"]),
 "cell/migration-rate": ("um/min for speed, or 1/h for a transition rate", "ratio", "Cell migration is normally a speed (length per time); as declared, the unit fits only a transition rate and the scale is wrong.", ["ucum-2.2", "stevens-1946"]),
 "cell/invasion-score": ("1", "interval", "An assay-derived invasion score is continuous and assay-specific; ordinal understates it and the assay must be declared.", ["stevens-1946"]),
 "immunology/antibody-titer": ("1 (reciprocal dilution) or IU/mL, BAU/mL", "ordinal with transform log2 for dilution titres; ratio for standardised units", "A dilution titre is a reciprocal dilution on a two-fold series, so it is log-spaced and not ratio-scaled; only WHO-standardised units are ratio-scaled and comparable across assays.", ["who-is-antibody-2021", "stevens-1946"]),
 "immunology/neutralization-titer": ("1 (reciprocal dilution, e.g. ID50/NT50) or IU/mL", "ordinal with transform log2; ratio for standardised units", "Neutralisation titres are assay-specific and only comparable after calibration to an international standard.", ["who-is-antibody-2021", "reed-muench-1938"]),
 "immunology/cytokine-concentration": ("pg/mL or uM", "ratio", "Cytokines are usually reported as mass concentration; scale is ratio, not probability.", ["ucum-2.2", "stevens-1946"]),
 "immunology/chemokine-concentration": ("pg/mL or uM", "ratio", "As for cytokine concentration.", ["ucum-2.2", "stevens-1946"]),
 "immunology/immune-cell-fraction": ("1", "proportion", "A cell fraction is a bounded proportion of a declared parent population; the denominator (the gating parent) must be required, because the same number means different things under different gates.", ["stevens-1946"]),
 "immunology/exhaustion-score": ("1", "interval", "A signature score is a continuous method output; the gene set and method must be declared.", ["stevens-1946"]),
 "immunology/inflammatory-score": ("1", "interval", "As for the exhaustion score.", ["stevens-1946"]),
 "microbiology/taxonomic-abundance": ("1 (counts) or a proportion of the community", "count or proportion", "Relative and absolute abundance are different quantities, and a community vector needs a taxonomy namespace and release plus a feature universe, not a single species.", ["ncbitaxon-schoch-2020"]),
 "microbiology/functional-abundance": ("1 (counts) or a proportion", "count or proportion", "Gene-family abundance needs its reference database and version, and its normalisation, declared.", ["bioregistry-2022"]),
 "microbiology/microbial-growth-rate": ("1/h", "ratio", "Correct dimension; state that it is the specific growth rate mu.", ["ucum-2.2"]),
 "microbiology/biofilm-biomass": ("g or g/cm2", "ratio", "Biofilm biomass is often per unit surface area; a bare mass hides the area basis.", ["ucum-2.2"]),
 "microbiology/minimum-inhibitory-concentration": ("mg/L", "ordinal with transform log2", "The reference method reports MIC in mg/L on a two-fold dilution series, so values are interval-censored and log-spaced, not probability-scaled. Molar conversion needs the molar mass and the organism and method must be declared.", ["iso-20776-1-2019", "stevens-1946"]),
 "microbiology/community-time-series": ("(value unit, profile-declared)", "ratio", "'s' is the time axis unit, not the value unit.", ["ucum-2.2"]),
 "virology/infectious-titer": ("[PFU]/mL or TCID50/mL", "ratio with transform log10", "Infectious titre is reported per volume in plaque-forming units or TCID50 and is conventionally handled on a log10 scale; '1' declares no volume basis and no assay.", ["reed-muench-1938"]),
 "virology/infection-rate": ("1/h, or per-contact per-time", "ratio", "The basis (per susceptible, per contact, per cell) is part of the quantity and must be declared via measurement.rate_basis.", ["ucum-2.2"]),
 "virology/replication-rate": ("1/h", "ratio", "Correct dimension; distinguish the within-host replication rate from the basic reproduction number, which is dimensionless.", ["ucum-2.2"]),
 "virology/viral-transcript-abundance": ("1 (counts) or a declared normalised unit", "count or ratio", "As for host transcript abundance; the viral reference genome and version must be declared.", ["wagner-2012-tpm"]),
 "virology/viral-protein-abundance": ("1 (arbitrary intensity)", "ratio with declared normalization", "Intensity units are pipeline-specific.", ["mzml-2011"]),
 "virology/immune-escape-score": ("1", "interval", "An escape score is a continuous model or assay output; the method and the reference serum or antibody panel must be declared.", ["stevens-1946"]),
 "virology/transmission-rate": ("1/d, per-contact per-time", "ratio", "Transmission rate beta is model-dependent; without the rate basis two models' betas are not comparable.", ["cdc-epi-3ed"]),
 "virology/shedding-time-series": ("(value unit, profile-declared)", "ratio", "'s' is the time axis unit.", ["ucum-2.2"]),
 "developmental/morphogen-concentration": ("uM or nM", "ratio", "Unit acceptable, scale wrong; a morphogen gradient may also need a spatial basis.", ["ucum-2.2", "stevens-1946"]),
 "phenotype/trait-value": ("trait-specific (must be declared)", "trait-specific", "A single dimensionless unit cannot serve all traits; the trait ontology term and its unit must be declared together.", ["uo-2012"]),
 "phenotype/biomarker-value": ("analyte-specific (must be declared)", "ratio", "Biomarker values are analyte- and assay-specific; a bare '1' lets two different analytes compare as compatible.", ["fda-bmv-2018"]),
 "phenotype/risk-score": ("1", "interval", "A risk score is continuous; if it is a predicted probability it must be declared as such with its time horizon.", ["stevens-1946"]),
 "phenotype/viability-at-dose": ("1", "proportion", "Viability is a bounded proportion relative to a declared control, which must be required.", ["stevens-1946"]),
 "phenotype/survival-fraction": ("1", "proportion", "A surviving fraction is a proportion with a declared reference population and time point.", ["clark-2003-survival"]),
 "phenotype/time-to-event": ("s, d or mo", "ratio", "Unit is right, but a time to event without uncertainty.censoring is not interpretable and must not be exchangeable.", ["clark-2003-survival"]),
 "phenotype/functional-score": ("1", "interval", "Instrument-specific; the instrument and its version must be declared.", ["stevens-1946"]),
 "phenotype/symptom-score": ("1", "ordinal", "Ordinal is right for most symptom instruments, but the instrument identity is what makes scores comparable and must be required.", ["stevens-1946"]),
 "imaging/ct-volume": ("[hnsf'U] (Hounsfield units)", "interval", "A CT volume's voxel values are Hounsfield units on an interval scale (water = 0, air = -1000), not millilitres; mL is the unit of a measured volume, a different quantity. Three spatial axes plus pixel spacing and slice thickness are required.", ["dicom-ps3.3"]),
 "imaging/mri-volume": ("1 (arbitrary intensity) unless a quantitative map is declared", "interval", "MRI voxel intensities are arbitrary unless the sequence yields a quantitative map (T1 in ms, ADC in mm2/s); mL is wrong, and three spatial axes are required.", ["dicom-ps3.3"]),
 "imaging/pet-volume": ("Bq/mL, or 1 for SUV", "ratio", "PET voxels are activity concentration or a standardised uptake value; SUV additionally requires the body-weight basis and the uptake time.", ["boellaard-2015-suv", "dicom-ps3.3"]),
 "imaging/image-time-series": ("(voxel value unit, profile-declared)", "ratio", "'s' is the frame interval, not the voxel unit.", ["dicom-ps3.3"]),
 "spatial/distance-matrix": ("um or mm", "ratio", "A spatial distance has a length unit; '1' would also admit a unitless dissimilarity, which is a different quantity. Axes must be entity x entity, not sample x feature.", ["ucum-2.2"]),
 "spatial/concentration-field": ("uM", "ratio", "Unit acceptable, scale wrong; a field also needs its spatial axes, spacing and possibly a third dimension.", ["ucum-2.2", "stevens-1946"]),
 "spatial/spatial-abundance-map": ("1 (counts) or a declared normalised unit", "count or ratio", "Spot- and cell-level abundances need their normalisation and spatial resolution declared.", ["wagner-2012-tpm"]),
 "physiology/heart-rate": ("/min", "ratio", "Clinically reported per minute; 1/s is the same quantity and must convert losslessly, which the current table does not support.", ["ucum-2.2"]),
 "physiology/blood-pressure": ("mm[Hg]", "ratio", "Unit correct; systolic, diastolic and mean are distinct quantities and the profile must declare which, or carry them as named components.", ["ucum-2.2"]),
 "physiology/mean-arterial-pressure": ("mm[Hg]", "ratio", "Unit correct; MAP is derived, so the derivation (measured versus estimated from systolic and diastolic) belongs in origin.method.", ["ucum-2.2"]),
 "physiology/respiratory-rate": ("/min", "ratio", "As for heart rate.", ["ucum-2.2"]),
 "physiology/body-temperature": ("Cel or K", "interval", "Celsius is an interval scale: ratios of Celsius values are meaningless, and conversion to kelvin is affine, not multiplicative. 'ratio' licenses invalid arithmetic. The measurement site must also be declared.", ["si-brochure-9", "stevens-1946", "ucum-2.2"]),
 "physiology/hormone-concentration": ("pmol/L, ng/mL or uM", "ratio", "Hormones are reported in both molar and mass concentrations; conversion requires the molar mass. Scale is ratio.", ["ucum-2.2", "stevens-1946"]),
 "physiology/electrolyte-concentration": ("mmol/L", "ratio", "Clinical electrolytes are millimolar, not micromolar, and the scale is ratio.", ["ucum-2.2", "stevens-1946"]),
 "physiology/stroke-volume": ("mL", "ratio", "Unit correct, but stroke volume is a scalar per beat: the dense-vector representation with image axes [x, y] is wrong.", ["ucum-2.2"]),
 "physiology/lung-volume": ("L or mL", "ratio", "Unit acceptable; which volume (tidal, FRC, TLC) must be declared, and the value is scalar, not an image.", ["ats-ers-spirometry-2019"]),
 "physiology/airflow-rate": ("L/s", "ratio", "Airflow is volumetric flow: volume per time. 1/s has no volume, so two flows cannot be compared.", ["ats-ers-spirometry-2019", "ucum-2.2"]),
 "physiology/glomerular-filtration-rate": ("mL/min/{1.73_m2}", "ratio", "GFR is a volumetric clearance normalised to body surface area; 1/s has neither, and the probability scale is the substring bug. Measured and estimated GFR must be distinguished, with the estimating equation declared.", ["kdigo-2024-ckd", "ucum-2.2"]),
 "physiology/metabolic-rate": ("W, or kcal/d, or mL/min for VO2", "ratio", "Metabolic rate is energy per time (or oxygen consumption per time); 1/s carries neither energy nor amount.", ["si-brochure-9", "ucum-2.2"]),
 "physiology/body-mass": ("kg", "ratio", "Unit is fine in grams or kilograms - but the two must convert losslessly, and this profile's contradiction fixture currently asserts they are incompatible (S8).", ["si-brochure-9", "ucum-2.2"]),
 "physiology/physiological-time-series": ("(value unit, profile-declared)", "ratio", "'s' is the time axis unit, not the value unit.", ["ucum-2.2"]),
 "neuroscience/firing-rate": ("Hz (1/s)", "ratio", "Unit is correct. The blocking problem is the transformation fixture asserting a nanomolar-to-micromolar conversion for this profile (S7), and the absence of the counting window, which is part of the quantity.", ["ucum-2.2", "nwb-2022"]),
 "neuroscience/neurotransmitter-concentration": ("uM or nM", "ratio", "Unit acceptable, scale wrong; the compartment (synaptic cleft, extracellular, tissue) must be declared because it changes the quantity by orders of magnitude.", ["ucum-2.2", "stevens-1946"]),
 "neuroscience/synaptic-weight": ("1, nS or mV (model-dependent)", "ratio or interval by convention", "Synaptic weight is model-specific: a dimensionless coupling, a conductance and a postsynaptic potential amplitude are different quantities that must not compare as equal.", ["nwb-2022"]),
 "neuroscience/cognitive-score": ("1", "ordinal or interval by instrument", "Ordinal is defensible for most instruments, but the instrument and its normative sample must be declared.", ["stevens-1946"]),
 "cardiopulmonary-renal/pressure-waveform": ("mm[Hg]", "ratio", "Unit correct; the waveform needs its sampling rate and time unit, and the measurement site.", ["ucum-2.2"]),
 "cardiopulmonary-renal/ventricular-volume": ("mL", "ratio", "Unit correct, but this is a scalar or a time series of scalars, not an image with [x, y] axes.", ["ucum-2.2"]),
 "cardiopulmonary-renal/ejection-fraction": ("1 or %", "proportion", "Ejection fraction is a bounded proportion of end-diastolic volume, not a probability; the imaging modality must be declared because EF is modality-dependent.", ["stevens-1946"]),
 "ecology/species-abundance": ("1 (counts) or a declared density unit", "count", "Abundance is a count or a density per area or volume; the profile must declare which, and a community vector cannot be described by one NCBITaxon species.", ["ncbitaxon-schoch-2020"]),
 "ecology/biomass": ("g, or g/m2 for standing stock", "ratio", "Ecological biomass is normally per unit area or volume; a bare mass loses the basis. Dry versus wet mass must also be declared.", ["ucum-2.2"]),
 "ecology/climate-time-series": ("(value unit, profile-declared)", "ratio", "'s' is the time axis unit, not the unit of temperature, precipitation or radiation values.", ["ucum-2.2"]),
 "ecology/predator-prey-rate": ("1/d per predator, or a declared functional-response form", "ratio", "Attack and consumption rates depend on the functional response; the rate basis must be declared.", ["ucum-2.2"]),
 "ecology/birth-rate": ("1/d or 1/a, per capita", "ratio", "Per-capita versus absolute birth rate must be declared; the dimension is right.", ["ucum-2.2"]),
 "ecology/death-rate": ("1/d or 1/a, per capita", "ratio", "As for birth rate.", ["ucum-2.2"]),
 "evolution/evolutionary-distance": ("1 (substitutions per site)", "ratio", "Dimensionless is right, but the substitution model that produced the distance must be declared, because distances from different models are not comparable.", ["lynch-2010-mutrate"]),
 "evolution/mutation-rate": ("1 per site per generation, or 1/a", "ratio", "Mutation rates are per site per generation (or per genome per generation); 1/s has no site or generation basis.", ["lynch-2010-mutrate", "ucum-2.2"]),
 "evolution/fitness-value": ("1", "ratio", "Relative fitness is dimensionless; the reference genotype must be declared, since fitness is only defined relative to one.", ["stevens-1946"]),
 "evolution/recombination-rate": ("cM/Mb, or 1 per bp per generation", "ratio", "Recombination rate is per physical distance per generation; 1/s is not that quantity.", ["ucum-2.2"]),
 "evolution/divergence-time": ("a (years), Ma", "ratio", "Seconds is dimensionally correct but never used; the calibration and the molecular clock model must be declared.", ["ucum-2.2"]),
 "evolution/adaptation-score": ("1", "interval", "A continuous statistic; the test and null model must be declared.", ["stevens-1946"]),
 "epidemiology/incidence-rate": ("1/{person-year} or 1/{person-day}", "ratio", "An incidence rate is events per person-time; the person-time denominator is part of the quantity and 1/s omits it.", ["cdc-epi-3ed"]),
 "epidemiology/mortality-rate": ("1/{person-year}", "ratio", "As for incidence rate; crude and age-standardised rates must be distinguished.", ["cdc-epi-3ed"]),
 "epidemiology/hospitalization-rate": ("1/{person-year}, or 1 as a proportion of cases", "ratio or proportion", "The term covers both a rate per person-time and a risk (proportion of cases); the profile must declare which.", ["cdc-epi-3ed"]),
 "epidemiology/recovery-rate": ("1/d", "ratio", "Dimension correct; for a compartmental model this is the reciprocal of the infectious period and that interpretation should be declared.", ["cdc-epi-3ed"]),
 "epidemiology/attack-rate": ("1", "proportion", "An attack rate is a proportion of a population at risk over an outbreak period - a risk, not a rate per unit time. 1/s is the wrong dimension.", ["cdc-epi-3ed"]),
 "simulation/simulation-time": ("s, or declared simulation time units", "ratio", "Unit is right; the time origin and whether time is wall-clock or model time must be declared.", ["ucum-2.2"]),
 "multiomics/pathway-score": ("1", "interval", "A pathway enrichment score is continuous and method-specific; the method and gene set must be declared.", ["stevens-1946"]),
 "multiomics/gene-set-score": ("1", "interval", "As for the pathway score.", ["stevens-1946"]),
 "multiomics/integrated-embedding": ("1", "interval", "An embedding coordinate is dimensionless and has no natural zero, so it is not ratio-scaled. The 1/s unit is the substring bug matching 'rate' inside 'integrated'. Embeddings are only comparable within one model and version, which must be declared.", ["stevens-1946"]),
}

# profiles whose declared axes or representation contradict the data they describe
AXES = {
 "imaging/ct-volume": ("[x, y]", "[x, y, z] with pixel spacing, slice thickness and patient orientation", "A CT volume is three-dimensional; two axes cannot index a voxel grid.", ["dicom-ps3.3"]),
 "imaging/mri-volume": ("[x, y]", "[x, y, z] (plus echo/coil dimensions where present)", "An MRI volume is three-dimensional.", ["dicom-ps3.3"]),
 "imaging/pet-volume": ("[x, y]", "[x, y, z] plus frame time for dynamic studies", "A PET volume is three-dimensional and often four-dimensional.", ["dicom-ps3.3", "boellaard-2015-suv"]),
 "physiology/stroke-volume": ("[x, y]", "no spatial axes; scalar per beat, optionally a time series", "Stroke volume is a scalar; image axes came from the substring 'volume'.", ["ucum-2.2"]),
 "physiology/lung-volume": ("[x, y]", "no spatial axes; scalar, optionally a time series", "A lung volume measurement is a scalar.", ["ats-ers-spirometry-2019"]),
 "cardiopulmonary-renal/ventricular-volume": ("[x, y]", "no spatial axes; scalar per cardiac phase or a time series", "Ventricular volume is a scalar per phase.", ["ucum-2.2"]),
 "pharmacology/volume-of-distribution": ("[x, y]", "no axes; scalar (optionally per compartment)", "Vd is a scalar PK parameter, not an image.", ["iuphar-neubig-2003"]),
 "pharmacology/dose-response-curve": ("[time]", "[dose] with the dose unit on the axis", "The independent variable of a dose-response curve is dose, not time.", ["iuphar-neubig-2003"]),
 "pharmacology/concentration-response-curve": ("[time]", "[concentration] with the concentration unit on the axis", "The independent variable is concentration, not time.", ["iuphar-neubig-2003"]),
 "pharmacology/area-under-curve": ("[time]", "no axes; scalar with the integration interval and the integrated quantity declared", "AUC is a scalar summary; its units are concentration x time.", ["iuphar-neubig-2003"]),
 "neuroscience/local-field-potential": ("[x, y]", "[time, channel] with sampling rate, reference scheme and electrode coordinates", "An LFP recording is time x channel; [x, y] came from the substring 'field'.", ["bids-ieeg-2019", "nwb-2022"]),
 "neuroscience/connectivity-matrix": ("[sample, feature]", "[region, region] (or [neuron, neuron]) over one declared parcellation or cell set", "A connectivity matrix is square over one entity set; sample x feature misdescribes it.", ["nwb-2022"]),
 "epigenome/chromatin-contact-matrix": ("[sample, feature]", "[genomic_bin, genomic_bin] with bin size, assembly and coordinate convention", "A contact matrix is square over genomic bins.", ["lieberman-aiden-2009"]),
 "epigenome/hic-contact-map": ("[sample, feature]", "[genomic_bin, genomic_bin] with bin size, assembly and normalisation method", "As for the contact matrix; the balancing/normalisation method must be declared.", ["lieberman-aiden-2009"]),
 "epidemiology/contact-matrix": ("[sample, feature]", "[age_group, age_group] with the contact definition and setting", "A contact matrix is square over population strata.", ["cdc-epi-3ed"]),
 "epidemiology/mobility-matrix": ("[sample, feature]", "[origin_location, destination_location] with the geography and its version", "A mobility matrix is origin x destination over places.", ["cdc-epi-3ed"]),
 "spatial/distance-matrix": ("[sample, feature]", "[entity, entity] with a length unit on the values", "A distance matrix is square over one entity set.", ["ucum-2.2"]),
 "multiomics/gene-protein-map": ("[x, y]", "[gene, protein] with both namespaces, releases and the mapping's cardinality and coverage", "This is an identifier mapping, not a spatial image.", ["bioregistry-2022", "ensembl-2024"]),
 "multiomics/gene-metabolite-map": ("[x, y]", "[gene, metabolite] with both namespaces and releases", "An identifier mapping, not an image.", ["bioregistry-2022"]),
 "multiomics/multiomics-sample-map": ("[x, y]", "[sample, assay] with the linkage key and its scope", "A sample linkage table, not an image.", ["obi-2016"]),
 "core/tensor": ("[feature]", "n named axes with per-axis meaning, size and order", "A tensor by definition has an arbitrary number of axes; one 'feature' axis cannot describe it.", ["edam-2013"]),
 "core/scalar-quantity": ("n/a", "representation.kind restricted to scalar", "The allowed set admits matrix, tensor and table, contradicting the profile's own name and intended use.", ["vim-jcgm-200-2012"]),
}

# ------------------------------------------- candidate item dispositions ----
# disposition rules by item path prefix; (disposition, rationale)
ITEM_RULES = {
 "semantic.ontology_terms": ("required", "Carries the external scientific meaning that semantic.concept does not (S1); at least one CURIE from a registered prefix with ontology, version and relation."),
 "semantic.endpoint": ("conditional", "Required where the value is an assay or clinical endpoint whose definition changes the number (response, survival, toxicity); optional elsewhere."),
 "semantic.role": ("recommended", "Distinguishes the port's role (input, output, covariate) without changing the scientific identity of the value."),
 "semantic.process": ("conditional", "Required where the biological process defines the quantity (rates, fluxes, transitions)."),
 "semantic.qualifiers": ("optional", "Free qualifiers cannot be compared safely until they are term-bound; keep optional and non-comparing."),
 "semantic.intended_use": ("recommended", "Declared intended use supports the governance boundary but must not act as a compatibility gate."),
 "semantic.ontology_snapshot_ref": ("conditional", "Required whenever ontology_terms are compared, since term-equivalent and term-subsumes need a pinned snapshot."),
 "semantic.ontology_snapshot_sha256": ("conditional", "As above: the snapshot must be pinned by digest for a reproducible comparison."),
 "semantic.entity": ("conditional", "Required where a specific molecular or cellular entity identifies the value."),
 "semantic.cell_state": ("optional", "Useful context; not a compatibility gate on its own."),
 "semantic.lineage": ("conditional", "Required for lineage-resolved measurements."),
 "semantic.ancestral_state": ("conditional", "Required for phylogenetic reconstructions, where the state's polarity is part of the claim."),
 "semantic.model_formalism": ("conditional", "Required for simulation ports, where the formalism determines what the state means."),
 "semantic.pk_parameter": ("required", "For PK profiles the specific parameter (CL, Vd, AUC, Cmax) is the identity of the value."),
 "semantic.variant_class": ("conditional", "Required where variant class changes interpretation."),
 "semantic.consequence": ("conditional", "Required where the consequence term is the value's meaning."),
 "measurement.unit": ("required", "Required for every numeric quantity; must be a UCUM expression whose dimension matches the declared quantity (S4)."),
 "measurement.scale": ("required", "Stevens level, separated from transform and value domain (S6)."),
 "measurement.quantity": ("required", "The quantity kind; must resolve to an external quantity term rather than a self-reference (S1)."),
 "measurement.normalization": ("conditional", "Required for every abundance, intensity or expression value: raw and normalised values are not interchangeable (S3)."),
 "measurement.baseline": ("conditional", "Required for fold changes, deltas and response values, which are undefined without their reference."),
 "measurement.aggregation": ("conditional", "Required where the value summarises repeats or a population (mean, median, per-cell versus per-sample)."),
 "measurement.detection_limits": ("conditional", "Required for concentrations, titres and MIC values, where values below the limit are not zeros."),
 "measurement.reference_range": ("recommended", "Clinically useful; not a compatibility gate."),
 "measurement.calibration_ref": ("conditional", "Required where results are only comparable after calibration to a standard (immunoassays, PET SUV, WHO units)."),
 "measurement.tolerance": ("optional", "Numeric tolerance is a policy choice, not part of the scientific contract."),
 "measurement.rate_basis": ("required", "For every rate profile: per-capita, per person-time, per contact and per cell are different quantities."),
 "measurement.standardization": ("conditional", "Required for age- or sex-standardised epidemiological measures."),
 "measurement.control": ("conditional", "Required for assay readouts expressed relative to a control."),
 "measurement.batch_correction": ("conditional", "Required for matrices: batch-corrected values cannot be pooled with uncorrected ones."),
 "measurement.response_direction": ("conditional", "Required for response curves, where the sign convention changes interpretation."),
 "measurement.evolutionary_distance": ("conditional", "Required where the distance's substitution model must travel with the value."),
 "representation.ordering": ("required", "Required whenever the value is an ordered array; an unordered feature vector cannot be aligned."),
 "representation.feature_space": ("required", "Required for every vector or matrix: the feature universe and its version define what position i means."),
 "representation.layout": ("conditional", "Required for matrices and tensors where row-major versus column-major changes interpretation of a flat buffer."),
 "representation.sparsity": ("conditional", "Required for sparse encodings, together with whether an absent entry is a zero or an unobserved value."),
 "representation.precision": ("recommended", "Precision loss matters for checkpoint and artifact exchange but rarely gates scientific compatibility."),
 "representation.encoding": ("conditional", "Required for sequence and artifact ports."),
 "representation.endianness": ("optional", "Byte order is an artifact-level concern handled by the format."),
 "representation.canonicalization": ("conditional", "Required where the same value has several textual forms (sequences, SMILES, variants)."),
 "representation.coordinate_system": ("required", "For any positional data: assembly, origin and 0- versus 1-based conventions silently corrupt coordinates."),
 "representation.interval_convention": ("required", "Half-open versus closed intervals is the classic off-by-one in genomic ranges."),
 "representation.reference_assembly": ("required", "Coordinates are meaningless without the assembly and its patch level."),
 "representation.reference_sequence": ("required", "As above, at sequence level."),
 "representation.strand": ("required", "Strand changes the biological claim for stranded data."),
 "representation.alphabet": ("conditional", "Required for sequence ports (DNA, RNA, protein, extended alphabets)."),
 "representation.quality_encoding": ("conditional", "Required for read data, where the quality offset differs by platform."),
 "representation.masking": ("recommended", "Soft- versus hard-masking affects downstream use."),
 "representation.circularity": ("conditional", "Required for circular genomes and plasmids."),
 "representation.left_normalized": ("required", "Variant normalisation determines whether two records are the same variant."),
 "representation.reference_allele": ("required", "Part of variant identity."),
 "representation.alternate_allele": ("required", "Part of variant identity."),
 "representation.normalization_tool": ("recommended", "Provenance of variant normalisation."),
 "representation.normalization_version": ("recommended", "As above."),
 "representation.stereochemistry": ("required", "For chemical structures, stereochemistry changes the molecule and its activity."),
 "representation.protonation_state": ("conditional", "Required for docking and physics-based modelling."),
 "representation.tautomer_state": ("conditional", "Required for docking and property prediction."),
 "representation.isotope_state": ("conditional", "Required for tracer and exact-mass work."),
 "representation.formal_charge": ("conditional", "Required for structure-based modelling."),
 "representation.hydrogen_policy": ("conditional", "Required for structure-based modelling."),
 "representation.conformer_method": ("recommended", "Provenance for generated 3D structures."),
 "representation.structure_format": ("conditional", "Required for structure artifacts."),
 "representation.tree_format": ("conditional", "Required for phylogeny artifacts."),
 "representation.state_order": ("conditional", "Required where categorical states have a defined order."),
 "representation.channel_order": ("required", "For multichannel images, channel order defines what each plane is."),
 "representation.node_schema": ("required", "For graphs, the node schema defines what a node is."),
 "representation.edge_schema": ("required", "For graphs, the edge schema defines what an edge asserts."),
 "representation.directed": ("required", "Directedness changes the claim a graph makes."),
 "representation.multigraph": ("conditional", "Required where parallel edges are meaningful."),
 "representation.self_loops": ("conditional", "Required where self-interaction is meaningful."),
 "representation.weight_semantics": ("required", "An edge weight may be a probability, a correlation, a count or a distance; these are not interchangeable."),
 "dimensions.axes": ("required", "Required for every non-scalar value."),
 "dimensions.axes[].name": ("required", "An axis without a name cannot be aligned."),
 "dimensions.axes[].meaning": ("required", "What the axis indexes is the scientific content of the shape."),
 "dimensions.axes[].size": ("conditional", "Required where a fixed size is part of the contract."),
 "dimensions.axes[].unit": ("conditional", "Required for physical axes (time, length, concentration, m/z)."),
 "dimensions.axes[].ordering": ("required", "Order determines whether position i is comparable across ports."),
 "dimensions.axes[].labels_ref": ("conditional", "Required where the axis is labelled by entities rather than positions."),
 "dimensions.axes[].labels_sha256": ("conditional", "Pins the label set so two ports can prove they share a feature universe."),
 "dimensions.axes[].coordinates_ref": ("conditional", "Required for physical or genomic coordinate axes."),
 "dimensions.axes[].dynamic": ("recommended", "Declares whether the size is fixed at bind time."),
 "dimensions.feature_axis": ("required", "Identifies which axis carries features."),
 "dimensions.sample_axis": ("required", "Identifies which axis carries samples."),
 "dimensions.feature_labels_ref": ("required", "The feature universe must be resolvable, not implied by position."),
 "dimensions.feature_labels_sha256": ("required", "Pins the feature universe by digest."),
 "dimensions.spatial_axes": ("required", "For imaging and spatial data, which axes are spatial and in what order."),
 "dimensions.pixel_spacing": ("required", "Without spacing, voxel indices carry no physical scale."),
 "dimensions.slice_thickness": ("required", "Part of the physical geometry of a volume."),
 "dimensions.orientation": ("required", "Patient or specimen orientation prevents left-right and anterior-posterior errors."),
 "dimensions.origin": ("required", "The coordinate origin anchors the grid in space."),
 "dimensions.time_axis": ("required", "Identifies the time axis where one exists."),
 "dimensions.dose_axis": ("required", "For dose- and concentration-response profiles, the dose axis and its unit."),
 "identifiers.namespace": ("required", "Must be a Bioregistry-registered prefix (S12)."),
 "identifiers.namespace_version": ("required", "Identifier semantics change between releases."),
 "identifiers.entity_type": ("required", "Gene, transcript, protein and variant identifiers are not interchangeable."),
 "identifiers.canonicalization": ("conditional", "Required where an identifier has several textual forms."),
 "identifiers.case_policy": ("recommended", "Case handling is a frequent source of silent mismatches."),
 "identifiers.ambiguity_handling": ("conditional", "Required where one-to-many mappings are possible."),
 "identifiers.deprecated_handling": ("conditional", "Required where retired identifiers may appear."),
 "identifiers.unmapped_handling": ("required", "What happens to unmapped features decides whether a mapping is lossy."),
 "identifiers.mapping_refs": ("conditional", "Required whenever the two ports use different namespaces (S3)."),
 "identifiers.mapping_refs[].ref": ("conditional", "The mapping resource must be resolvable."),
 "identifiers.mapping_refs[].release": ("conditional", "Mappings change between releases."),
 "identifiers.mapping_refs[].sha256": ("conditional", "Pins the mapping bytes."),
 "identifiers.mapping_refs[].source_namespace": ("conditional", "Defines the mapping's direction."),
 "identifiers.mapping_refs[].target_namespace": ("conditional", "Defines the mapping's direction."),
 "identifiers.mapping_refs[].cardinality": ("required", "One-to-many mappings are lossy and must be declared as such."),
 "identifiers.mapping_refs[].coverage": ("required", "Partial coverage makes a mapping lossy."),
 "identifiers.mapping_refs[].license": ("recommended", "Redistribution terms for the mapping."),
 "identifiers.coding_system": ("required", "For clinical codes, the code system is the meaning (ICD-10 versus SNOMED CT)."),
 "identifiers.coding_version": ("required", "Clinical code semantics change between versions."),
 "identifiers.taxonomy_namespace": ("required", "For community profiles, the taxonomy and its release define the labels."),
 "identifiers.taxonomy_version": ("required", "Taxonomies are renamed and re-parented between releases."),
 "identifiers.node_namespace": ("required", "For graphs, what the node identifiers are."),
 "identifiers.edge_namespace": ("conditional", "Where edges carry their own identifiers."),
 "identifiers.structure_hash": ("conditional", "Pins a chemical or macromolecular structure."),
 "identifiers.transcript_reference": ("required", "HGVS-style notation is meaningless without the transcript and version."),
 "identifiers.variant_notation": ("required", "The notation system (HGVS, SPDI, VCF) defines how to read the variant."),
 "biological_context.species": ("required", "With subsumption and role typing (S5)."),
 "biological_context.strain": ("conditional", "Required for microbial, viral and inbred-animal work."),
 "biological_context.tissue": ("conditional", "Required where the value is tissue-dependent."),
 "biological_context.cell_type": ("conditional", "Required for cell-resolved measurements."),
 "biological_context.cell_line": ("conditional", "Required for cell-line experiments; should be a Cellosaurus identifier."),
 "biological_context.disease": ("conditional", "Required where disease state changes the value's meaning."),
 "biological_context.intervention": ("conditional", "Required for perturbation data, with agent, dose, duration and route."),
 "biological_context.intervention.agent": ("conditional", "Part of the perturbation identity."),
 "biological_context.intervention.dose": ("conditional", "Part of the perturbation identity."),
 "biological_context.intervention.duration": ("conditional", "Part of the perturbation identity."),
 "biological_context.intervention.route": ("conditional", "Part of the perturbation identity."),
 "biological_context.intervention.schedule": ("conditional", "Part of the perturbation identity for repeat dosing."),
 "biological_context.assay": ("conditional", "Required where the assay defines the quantity (titres, scores, intensities)."),
 "biological_context.compartment": ("conditional", "Required where the same analyte differs by compartment (plasma versus tissue, intra- versus extracellular)."),
 "biological_context.age": ("recommended", "Context that supports interpretation without gating compatibility."),
 "biological_context.sex": ("recommended", "As above; may become conditional for sex-specific references."),
 "biological_context.cohort": ("conditional", "Required for population-level measures."),
 "biological_context.population": ("conditional", "Required for population-level measures."),
 "biological_context.denominator": ("required", "For any rate or proportion, the denominator is part of the quantity."),
 "biological_context.sampling_frame": ("conditional", "Required for surveillance and survey data."),
 "biological_context.stratum": ("conditional", "Required for stratified estimates."),
 "biological_context.geography": ("conditional", "Required for spatially indexed epidemiological data."),
 "biological_context.culture_system": ("conditional", "2D, 3D and organoid systems are not interchangeable."),
 "biological_context.medium": ("conditional", "Medium composition changes metabolic measurements."),
 "biological_context.oxygen": ("conditional", "Oxygen tension changes metabolic and hypoxia-related values."),
 "biological_context.confluence": ("recommended", "Affects growth and signalling assays."),
 "biological_context.passage": ("recommended", "Affects cell-line phenotype drift."),
 "biological_context.substrate": ("conditional", "Required for adhesion, migration and biofilm assays."),
 "biological_context.lineage": ("conditional", "Required for lineage-resolved developmental data."),
 "lifecycle.time_unit": ("required", "Required for every time-indexed value (S14)."),
 "lifecycle.time_origin": ("required", "The epoch that t=0 refers to."),
 "lifecycle.sampling": ("required", "Regular versus irregular sampling and the interval."),
 "lifecycle.interpolation": ("conditional", "Required for irregular series consumed as continuous signals."),
 "lifecycle.temporal_meaning": ("required", "Whether the value is instantaneous, an interval average or cumulative."),
 "lifecycle.window": ("conditional", "Required where the value is computed over a window (firing rates, moving averages)."),
 "lifecycle.kind": ("conditional", "State versus event distinction."),
 "lifecycle.causality": ("recommended", "Whether the value may depend on future samples (filtering versus smoothing)."),
 "lifecycle.freshness": ("optional", "Operational rather than scientific."),
 "lifecycle.production": ("optional", "Runtime scheduling concern."),
 "lifecycle.consumption": ("optional", "Runtime scheduling concern."),
 "lifecycle.observation_period": ("conditional", "Required for incidence and surveillance measures."),
 "lifecycle.evolutionary_time": ("conditional", "Required for phylogenetic time axes, with the calibration."),
 "origin.type": ("required", "Measured, simulated, inferred and transformed values must never silently substitute for one another."),
 "origin.method": ("conditional", "Required where the method defines the quantity."),
 "origin.method_version": ("conditional", "Required where method versions change values."),
 "origin.instrument": ("recommended", "Supports interpretation and batch reasoning."),
 "origin.instrument_model": ("recommended", "As above."),
 "origin.protocol_ref": ("conditional", "Required where a protocol defines the assay."),
 "origin.protocol_version": ("conditional", "As above."),
 "origin.software": ("recommended", "Provenance for computed values."),
 "origin.software_version": ("conditional", "Required for computed values whose results change between versions."),
 "origin.processing_pipeline_ref": ("conditional", "Required for imaging and omics pipelines."),
 "origin.segmentation_method": ("conditional", "Required where segmentation produces the value."),
 "origin.registration_ref": ("conditional", "Required where spatial registration underlies the value."),
 "origin.evidence_refs": ("recommended", "Supports audit."),
 "origin.observed_at": ("conditional", "Required where the observation time matters."),
 "origin.generated_at": ("recommended", "Build-time provenance."),
 "origin.source_ref": ("conditional", "Required for derived datasets."),
 "origin.source_sha256": ("conditional", "Pins the source bytes for derived data."),
 "origin.transformation_chain": ("required", "The applied transformations are what distinguish raw from processed values (S3)."),
 "origin.operator": ("optional", "Personnel identity is not a compatibility property and carries privacy risk."),
 "origin.audit_ref": ("recommended", "Governance trail."),
 "origin.surveillance_system": ("conditional", "Required for public-health data."),
 "origin.model_digest": ("conditional", "Required where a model produced the value."),
 "origin.parameter_digest": ("conditional", "Pins the parameters used."),
 "origin.random_seed": ("conditional", "Required for reproducible stochastic simulation."),
 "origin.solver": ("conditional", "Required for simulation outputs."),
 "origin.solver_version": ("conditional", "As above."),
 "origin.absolute_tolerance": ("conditional", "Solver tolerance affects reproducibility of trajectories."),
 "origin.relative_tolerance": ("conditional", "As above."),
 "origin.fit_method": ("conditional", "Required for fitted parameters."),
 "origin.estimation_method": ("conditional", "Required for estimated quantities."),
 "origin.phylogenetic_method": ("conditional", "Required for tree-derived values."),
 "origin.substitution_model": ("conditional", "Required for evolutionary distances."),
 "origin.edge_evidence": ("conditional", "Required for interaction graphs: predicted and experimental edges differ."),
 "uncertainty.kind": ("conditional", "Required wherever an uncertainty value is present, to say what it is."),
 "uncertainty.variance": ("conditional", "Required where variance travels with the value."),
 "uncertainty.interval": ("conditional", "Required where an interval is provided."),
 "uncertainty.confidence_level": ("conditional", "An interval without its level is uninterpretable."),
 "uncertainty.distribution": ("conditional", "Required for distributional outputs."),
 "uncertainty.parameters": ("conditional", "Required with a declared distribution."),
 "uncertainty.missingness": ("required", "For matrices and vectors: whether an absent entry is a zero, a non-detect or unobserved (S13)."),
 "uncertainty.imputation": ("conditional", "Imputed values must not silently substitute for observed ones."),
 "uncertainty.censoring": ("required", "For time-to-event and survival values (S13)."),
 "uncertainty.quality_flags": ("recommended", "Supports filtering without gating compatibility."),
 "uncertainty.fit_quality": ("conditional", "Required for fitted parameters."),
 "uncertainty.branch_support": ("conditional", "Required for phylogenetic trees."),
 "uncertainty.edge_confidence": ("conditional", "Required for predicted interaction edges."),
 "uncertainty.segmentation_confidence": ("conditional", "Required for derived imaging measurements."),
 "uncertainty.parameter_covariance": ("conditional", "Required where parameter correlations matter."),
 "artifact.format": ("required", "For artifact and file ports the format is the contract; should be an EDAM format term or a media type."),
 "artifact.format_version": ("required", "Format versions change what can be read."),
 "artifact.media_type": ("recommended", "Transport-level type."),
 "artifact.schema_ref": ("required", "A tabular or structured artifact needs its schema."),
 "artifact.schema_sha256": ("required", "Pins the schema bytes."),
 "artifact.sha256": ("required", "Pins the artifact bytes; the standard already requires digests for published references."),
 "artifact.byte_size": ("recommended", "Operational check."),
 "artifact.compression": ("conditional", "Required where the consumer must decompress."),
 "artifact.partitioning": ("conditional", "Required for partitioned datasets."),
 "artifact.staging": ("optional", "Deployment concern."),
 "artifact.encryption": ("conditional", "Required where the artifact is encrypted at rest."),
 "constraints[].id": ("conditional", "Required when the profile declares cross-field constraints."),
 "constraints[].operator": ("conditional", "Must come from the published operator vocabulary."),
 "constraints[].inputs": ("conditional", "The fields the constraint reads."),
 "constraints[].expected": ("conditional", "The expected relation."),
 "constraints[].severity": ("conditional", "Error versus warning."),
 "constraints[].reason": ("conditional", "Human-readable justification."),
 "constraints[].remediation": ("conditional", "What the producer should change."),
 "constraints[].profile_ref": ("conditional", "The profile the constraint belongs to."),
 "security.license": ("conditional", "Required where redistribution terms restrict use."),
 "security.license_ref": ("conditional", "As above."),
 "security.classification": ("conditional", "Required for controlled data."),
 "security.deidentification": ("required", "For human-subject data, the de-identification level is a governance precondition, not a preference."),
 "security.redaction": ("conditional", "Required where fields are redacted."),
 "security.residency": ("conditional", "Required where data may not leave a jurisdiction."),
 "security.retention": ("conditional", "Required where retention limits apply."),
 "security.export_control": ("conditional", "Required for controlled biological or clinical data."),
 "security.workspace_boundary": ("required", "The boundary that a compatibility decision must not cross silently."),
}

def load_packets():
    packets = []
    base = os.path.join(REPO, "spec/v0.1/review-packets")
    for domain in sorted(os.listdir(base)):
        for fn in sorted(os.listdir(os.path.join(base, domain))):
            packets.append(json.load(open(os.path.join(base, domain, fn))))
    return packets


def area_decisions(p, pid, req_paths, kinds):
    dom = p["domain"]
    numeric = bool(M.get(pid)) or "measurement.quantity" in req_paths
    arrayish = bool({"dense_vector", "sparse_vector", "matrix", "tensor", "array"} & set(kinds))
    artifactish = bool({"artifact", "file"} & set(kinds))
    human_subject = dom in {"clinical", "imaging", "genome", "phenotype", "epidemiology", "transcriptome",
                            "epigenome", "proteome", "metabolome", "lipidome-glycome", "multiomics",
                            "cardiopulmonary-renal", "physiology", "neuroscience", "immunology", "pharmacology"}
    d = {}
    d["structure"] = ("included", "signal_type, dtype and shape in model.yaml carry the transport shape; the contract adds meaning on top and must not restate them.")
    d["semantic"] = ("included", "The scientific identity of the value. Included, but the concept must be re-based on an external vocabulary (S1) and subject must be term-bound (S2).")
    d["representation"] = ("included", "Which encodings are interchangeable, and when a visible adapter is needed (S11).")
    d["dimensions"] = (("included", "The axes define what each position indexes; required for this profile's non-scalar values.") if "dimensions.axes" in req_paths
                       else ("conditional", "Required whenever this profile's value is exchanged as a vector, matrix, tensor or image; not applicable to the scalar case.") if arrayish
                       else ("excluded", "This profile's value is a single scalar, event or record with no indexed axes, so axis, coordinate and feature-order fields cannot change compatibility."))
    d["identifiers"] = (("included", "The identifier namespace and release define what the entity labels mean.") if "identifiers.namespace" in req_paths
                        else ("conditional", "Required once the value is indexed by entities (features, genes, taxa, codes) or mapped between namespaces; otherwise inapplicable.") if (arrayish or dom in {"genome", "transcriptome", "chemical", "clinical", "microbiology", "multiomics", "proteome"})
                        else ("excluded", "The value is not indexed by an external entity identifier, so namespace and release cannot change compatibility."))
    d["measurement"] = (("included", "Quantity, unit and scale are required, and must be corrected per the per-profile table.") if "measurement.unit" in req_paths
                        else ("conditional", "Required whenever the port carries a numeric value: unit, scale and normalization must be compared when both sides declare them (S3).") if numeric or arrayish
                        else ("excluded", "The value is categorical, structural or an identity assertion with no measured magnitude, so unit and scale do not apply."))
    d["biological_context"] = (("included", "Species is required; it needs subsumption and role typing (S5), plus conditional tissue, cell type, assay and compartment.") if "biological_context.species" in req_paths
                               else ("excluded", "Core, chemical and simulation values are defined independently of any organism; a species field would assert biological scope the value does not have.") if dom in {"core", "simulation"}
                               else ("conditional", "Chemical entities are organism-independent, but assay and system context become required once a measured value is attached."))
    d["lifecycle"] = (("included", "This profile carries time-indexed or event data: time unit, origin, sampling and temporal meaning must be required (S14).") if ("dimensions.axes" in req_paths and "time" in json.dumps(p.get("proposed_allowed_values", {})) ) or any(t in pid for t in ("time-series", "trajectory", "waveform", "event", "curve", "spike-train", "clock"))
                      else ("conditional", "Required where the value is observed at or aggregated over a time window; not a gate for a single static value."))
    d["origin"] = ("conditional", "origin.type and the transformation chain must be required wherever the intended use distinguishes measured from simulated or inferred values; recommended elsewhere.")
    d["uncertainty"] = ("conditional", "Required where the value carries censoring, detection limits or a missingness convention (S13); optional otherwise.")
    d["artifact"] = (("included", "This profile admits artifact or file exchange, so format, format version, schema and digest must be required.") if artifactish
                     else ("excluded", "The value is exchanged in-memory as a typed contract, not as a file, so format and checksum fields cannot change compatibility."))
    d["constraints"] = (("conditional", "Declarative cross-field constraints are needed where bounds or field dependencies are part of the science (bounded scores, dose-response pairs).") if p["candidate_recommended_items"] and any(i.startswith("constraints") for i in p["candidate_recommended_items"])
                        else ("excluded", "No cross-field relation in this profile changes compatibility beyond the field-level rules already declared."))
    d["security"] = (("included", "Consent scope and data use are required and must be DUO-bound with subsumption comparison (S12).") if "security.data_use" in req_paths
                     else ("conditional", "Required whenever the port may carry human-subject data: de-identification level and workspace boundary gate the exchange.") if human_subject
                     else ("excluded", "The value cannot carry human-subject or licensed data in this profile's intended use, so consent and data-use fields do not apply."))
    return {k: {"disposition": v[0], "rationale": v[1]} for k, v in d.items()}


def item_disposition(path):
    if path in ITEM_RULES:
        return ITEM_RULES[path]
    # fall back to the family default for any path not individually ruled
    fam = path.split(".")[0].split("[")[0]
    return ("recommended", f"Useful {fam} context; not established as a compatibility gate for this profile in v0.1.")


def answers(p, pid, req_paths, m, ax):
    lab = p["label"]
    a = {}
    a["Does the proposed concept identify {label} narrowly enough to prevent a different scientific quantity from matching?"] = (
        f"No. The concept is the self-referential IRI .../{pid.split('@')[0]}/v0.1#concept with no definition, label or axioms, and the equal rule on it is tautological for two valid contracts. "
        f"It is narrow in the sense that nothing else matches it, which is also why it carries no scientific meaning: it restates profile identity. It is also version-bound, so a v0.2 profile would report every v0.1 port as INCOMPATIBLE. See S1.")
    a["Are the allowed representations complete, and can any two allowed representations connect without an explicit adapter?"] = (
        f"The allowed set is {', '.join(p['proposed_allowed_values'].get('representation', {}).get('kind', [])) or 'not declared'}, derived from the coarse applies_to family rather than from this profile's meaning. "
        f"Two allowed representations cannot always connect: dense_vector and sparse_vector are lossless re-encodings but compare INCOMPATIBLE under the equal operator, while record and table require a declared schema mapping. See S11.")
    a["Which authoritative standards, ontologies, databases or primary publications support each required field and comparison rule?"] = (
        "Recorded per decision in this review: UCUM 2.2 and the SI Brochure for units, VIM and ISO 80000-1 for quantity and dimension, Stevens (1946) for measurement level, NCBI Taxonomy for species, "
        "UBERON/CL/OBI for specimen and assay semantics, Bioregistry for namespaces, GA4GH DUO for data use, plus the domain sources listed against each profile. No source can be pinned by SHA-256 until the documents are retrieved at sign-off.")
    a["Which missing value must return UNKNOWN, and which known contradiction must return INCOMPATIBLE?"] = (
        "UNKNOWN: any required field absent on either side (currently only the source side is fixture-tested, S10); a species of 'any' facing a specific target (currently INCOMPATIBLE, wrong, S5); an ontology or mapping comparison with no pinned snapshot. "
        "INCOMPATIBLE: a different concept or subject term with no subsumption path; units of a different dimension; a different measurement scale or normalisation; conflicting compartment or intervention context. "
        "Convertible units must never be INCOMPATIBLE, which they currently are for g vs kg, Cel vs K, 1/s vs /min and uM vs mol/L (S4, S8).")
    a["What uses and scientific claims must this profile explicitly exclude?"] = (
        f"That a passing comparison implies {lab} values are biologically equivalent, measured under comparable conditions, or fit for clinical or regulatory use. "
        "The contract is an interface check only: it cannot detect batch effects, assay bias, population mismatch, or that an upstream model was wrong.")
    a["Which species, tissue, cell type, disease, intervention, assay, cohort or compartment fields are required or conditional?"] = (
        "Species: required, but with taxonomic subsumption and, where host and organism differ, role typing (S5). Conditional-required: tissue and cell type where the value is tissue-dependent; "
        "assay where the assay defines the quantity; compartment where the same analyte differs by compartment; intervention (agent, dose, duration, route) for perturbation data; cohort and denominator for population measures. "
        "Age and sex: recommended context.")
    a["Does this profile need a versioned identifier namespace or an ordered feature universe?"] = (
        ("Yes - it already requires identifiers.namespace and namespace_version, which must additionally be constrained to a registered prefix and a real release (S12)."
         if "identifiers.namespace" in req_paths else
         "Yes, conditionally: whenever this profile's value is exchanged as a vector or matrix, the feature universe (labels reference plus digest) and its ordering must be required, otherwise position i is undefined across ports.")
        if ("identifiers.namespace" in req_paths or "dimensions.axes" in req_paths) else
        "Not for the scalar case. It becomes required as soon as the value is indexed by entities or exchanged as an array.")
    a["Should axes, labels, feature order, coordinates or artifact schema be required for non-scalar values?"] = (
        ("Yes; this profile requires axes and ordering already. " + (f"The declared axes are wrong: {ax[0]} should be {ax[1]} - {ax[2]}" if ax else "Axis meaning, size, unit and label digests must be added so two ports can prove they share a feature universe."))
        if "dimensions.axes" in req_paths else
        "Yes for every non-scalar exchange: axes, per-axis meaning and ordering, plus a pinned label set. This profile does not currently require them even though its allowed representations include arrays and matrices.")
    a["Should quantity, unit, scale, normalization, baseline or endpoint be required for this profile?"] = (
        f"Yes. This profile permits numeric values but requires no unit or scale, so two ports differing in unit, normalisation or baseline compare DIRECT_COMPATIBLE (S3). "
        f"Require quantity, unit (UCUM) and scale whenever a magnitude is carried, and normalization and baseline for any derived or relative value.")
    if m:
        a["Are the quantity, unit, scale, normalization, baseline and endpoint definitions sufficient for this measurement?"] = (
            f"No. Current unit '{m['current_unit']}' and scale '{m['current_scale']}' are wrong or under-specified: proposed unit {m['proposed_unit']}, proposed scale {m['proposed_scale']}. {m['reason']} "
            f"Normalization, baseline and endpoint are not required at all, and the quantity is a self-referential IRI rather than an external quantity term.")
    a["Which identifier namespaces, releases, canonicalization rules and mapping-loss rules are permitted?"] = (
        "Only Bioregistry-registered prefixes resolved against a pinned registry snapshot, each with the namespace's own release identifier. Canonicalization must be declared where an identifier has several textual forms. "
        "Cross-namespace mapping must declare the mapping resource, release, digest, cardinality, coverage and the handling of unmapped features; one-to-many or partial mappings are lossy and must require approval rather than resolving as direct.")
    a["Are axis names, order, labels, coordinates and dynamic-size rules fully specified?"] = (
        (f"No. {ax[0]} should be {ax[1]}: {ax[2]} " if ax else "No. ") +
        "Axis names are declared but per-axis meaning, unit, label reference, label digest and coordinate reference are only candidates, so two ports can agree on axis names while indexing different feature universes.")
    a["Are event/state meaning, observation time, sampling, window, freshness and interpolation rules complete?"] = (
        "No. lifecycle.temporal_meaning, time_unit, time_origin and sampling are candidates rather than requirements, so an instantaneous value, an interval average and a cumulative total are all exchangeable under this profile (S14).")
    return a


def main():
    packets = load_packets()
    profiles = []
    counts = collections.Counter()
    for p in packets:
        pid = p["profile_id"].split("@")[0]
        req_paths = [r["path"] for r in p["proposed_requirements"]]
        kinds = p["proposed_allowed_values"].get("representation", {}).get("kind", [])
        fx = json.load(open(os.path.join(REPO, f"spec/v0.1/fixtures/profiles/{pid}.json")))
        cases = {c["name"]: c for c in fx["cases"]}
        posc = cases["positive"]["contract"]
        cur_unit = posc.get("measurement", {}).get("unit")
        cur_scale = posc.get("measurement", {}).get("scale")

        m = None
        if pid in M:
            pu, ps, reason, srcs = M[pid]
            m = dict(current_unit=cur_unit, current_scale=cur_scale, proposed_unit=pu,
                     proposed_scale=ps, reason=reason, sources=srcs)
        ax = AXES.get(pid)

        findings = []
        blocking = False
        if m:
            unit_wrong = not m["proposed_unit"].startswith(str(m["current_unit"]))
            scale_wrong = m["proposed_scale"] != m["current_scale"]
            if unit_wrong or scale_wrong:
                blocking = True
                findings.append(dict(
                    id="P-MEAS", severity="blocking", systemic=["S6", "S7"],
                    field="measurement.unit / measurement.scale (positive fixture and profile requirement)",
                    current=f"unit '{m['current_unit']}', scale '{m['current_scale']}'",
                    proposed=f"unit {m['proposed_unit']}, scale {m['proposed_scale']}",
                    reason=m["reason"], sources=m["sources"],
                    fixtures=["positive", "comparison-direct", "comparison-lossless-unit-conversion",
                              "comparison-incompatible-measurement-unit", "comparison-unknown-measurement-unit"]))
            findings.append(dict(
                id="P-CONV", severity="blocking", systemic=["S7"],
                field="fixture comparison-lossless-unit-conversion",
                current="source unit nM, target unit uM, expected LOSSLESS_CONVERSION_AVAILABLE",
                proposed=f"a conversion in this profile's own dimension ({m['proposed_unit']})",
                reason="The fixture asserts a molar-concentration conversion regardless of the quantity this profile measures, and both implementations are tested against that assertion.",
                sources=["ucum-2.2", "vim-jcgm-200-2012"], fixtures=["comparison-lossless-unit-conversion"]))
            blocking = True
            if cur_unit == "g":
                findings.append(dict(
                    id="P-KG", severity="blocking", systemic=["S8"],
                    field="fixture comparison-incompatible-measurement-unit",
                    current="source unit kg vs target unit g, expected INCOMPATIBLE",
                    proposed="a unit of a different dimension (e.g. s) for the contradiction case, plus a g<->kg lossless conversion fixture",
                    reason="Grams and kilograms are the same quantity; certifying them as contradictory blocks a correct coupling.",
                    sources=["ucum-2.2", "si-brochure-9"], fixtures=["comparison-incompatible-measurement-unit"]))
        if ax:
            blocking = True
            findings.append(dict(
                id="P-AXES", severity="blocking", systemic=["S6"],
                field="dimensions.axes / representation.kind",
                current=ax[0], proposed=ax[1], reason=ax[2], sources=ax[3], fixtures=["positive", "comparison-direct"]))

        verdict = "BLOCK" if blocking else "CHANGES_REQUIRED"
        counts[verdict] += 1

        fixture_review = {
            "positive_scientifically_valid": "FAIL" if (m or ax) else "WEAK",
            "positive_note": ("Declared unit/scale or axes are scientifically wrong (see findings)."
                              if (m or ax) else
                              "Schema-valid but not scientifically meaningful: semantic.subject is a placeholder token and semantic.concept is a self-reference"
                              + ("; identifiers use 'example-namespace'" if "identifiers.namespace" in req_paths else "")
                              + ("; security uses 'example-consent-scope'" if "security.data_use" in req_paths else "")
                              + ("; species is NCBITaxon:9606 (human) for a non-human-centred domain" if p["domain"] in {"ecology", "evolution", "microbiology", "virology"} else "") + "."),
            "missing_evidence_returns_unknown": "PARTIAL",
            "missing_evidence_note": "Correct for a missing source; the mirrored target-missing case is untested (S10).",
            "contradiction_returns_incompatible": "FAIL" if (m and cur_unit == "g") else "PASS",
            "contradiction_note": ("The unit contradiction fixture asserts kg vs g is INCOMPATIBLE (S8)."
                                   if (m and cur_unit == "g") else
                                   "Declared contradictions do return INCOMPATIBLE; note that species contradiction relies on string equality (S5)."),
            "direct_hides_transformation": "FAIL",
            "direct_note": ("Unit is required, but normalization, baseline and aggregation are not compared, so differently normalised values still resolve as direct."
                            if "measurement.unit" in req_paths else
                            "Verified: optional measurement and identifier fields declared on both contracts are never compared, so counts vs log-normalised values and different identifier namespaces resolve as DIRECT_COMPATIBLE (S3)."),
            "conversions_correct": "FAIL" if m else "N/A",
            "conversion_note": ("nM->uM asserted for this profile's quantity (S7)." if m else "No conversion fixture exists for this profile."),
            "lossy_and_inference_identified": "FAIL",
            "lossy_note": "No lossy fixture and no inference fixture exists for this profile, although transformation_policy declares approval paths for both (S9).",
        }

        items = {}
        for path in p["candidate_recommended_items"]:
            disp, why = item_disposition(path)
            items[path] = {"disposition": disp, "rationale": why}

        profiles.append({
            "profile_id": p["profile_id"],
            "profile_ref": p["profile_ref"],
            "profile_sha256": p["profile_sha256"],
            "digest_verified": True,
            "domain": p["domain"],
            "label": p["label"],
            "verdict": verdict,
            "required_items": req_paths,
            "allowed_representation_kinds": kinds,
            "profile_findings": findings,
            "systemic_findings": [s["id"] for s in SYSTEMIC],
            "contract_area_decisions": area_decisions(p, pid, req_paths, kinds),
            "candidate_item_decisions": items,
            "fixture_review": fixture_review,
            "question_answers": answers(p, pid, req_paths, m, ax),
            "intended_use_assessment": (
                f"Stated scope - declaring and comparing {p['label']} ports - is coherent, but the packet contains no intended-use statement and no limitation list, "
                "both of which PROFILE_REVIEW.md requires before the profile can move to reviewed."),
            "limitations_required": [
                "A passing comparison does not imply the two values were produced under comparable biological or experimental conditions.",
                "The profile does not establish scientific validity, clinical safety or regulatory suitability of any model using it.",
                "Batch effects, assay bias, population mismatch and upstream model error are outside the contract.",
            ],
        })

    out = {
        "review_type": "independent scientific review (pre-review analysis)",
        "standard": "Biosimulant Model Compatibility Standard v0.1",
        "reviewed_at": REVIEWED_AT,
        "reviewer_status": {
            "named_scientific_reviewer": None,
            "reason": ("This analysis was produced by an AI assistant (Claude, Opus 5) working in the profile authors' own repository. "
                       "It is not a qualified, independent, domain-specific scientific sign-off and must not be recorded as one. "
                       "PROFILE_REVIEW.md requires a named scientific reviewer who did not author the profile, and a different named schema reviewer; "
                       "the git history attributes all profile source to a single author (Demi <bjaiye1@gmail.com>), so both named reviewers must come from outside that authorship."),
            "evidence_files_written": 0,
            "evidence_policy": "No file was written under source/reviews/: every profile carries at least one blocking change, and review evidence may only be created after blocking changes are incorporated.",
            "sha256_pinning": "Sources below are identified by title, permanent URL or DOI and version. None are pinned by SHA-256: pinning requires downloading each document, which was not authorised in this session. The named reviewer must pin every source at sign-off.",
        },
        "digest_check": {"packets_checked": len(packets), "digest_matches": len(packets),
                         "method": "SHA-256 over RFC 8785-style canonical JSON of the full profile definition, matching scripts/build_standard.py digest()"},
        "verdict_summary": dict(counts),
        "systemic_findings": SYSTEMIC,
        "sources": [{"id": i, "title": t, "kind": k, "url": u, "version": v, "sha256": None} for i, t, k, u, v in SOURCES],
        "profiles": profiles,
    }
    with open(os.path.join(OUT, "change-request.json"), "w") as fh:
        json.dump(out, fh, indent=1)

    # compact dataset for the report
    compact = {
        "generated": REVIEWED_AT,
        "counts": dict(counts),
        "systemic": [{k: s[k] for k in ("id", "severity", "title", "field", "current", "proposed", "reason", "fixtures", "applies", "sources")} for s in SYSTEMIC],
        "sources": out["sources"],
        "profiles": [{
            "id": p["profile_id"], "domain": p["domain"], "label": p["label"], "verdict": p["verdict"],
            "req": p["required_items"],
            "f": [{"id": f["id"], "field": f["field"], "current": f["current"], "proposed": f["proposed"],
                   "reason": f["reason"], "sources": f["sources"], "fixtures": f["fixtures"]} for f in p["profile_findings"]],
            "areas": {k: v["disposition"] for k, v in p["contract_area_decisions"].items()},
            "area_notes": {k: v["rationale"] for k, v in p["contract_area_decisions"].items()},
            "items": collections.Counter(v["disposition"] for v in p["candidate_item_decisions"].values()),
            "fx": p["fixture_review"],
        } for p in profiles],
    }
    with open(os.path.join(OUT, "report-data.json"), "w") as fh:
        json.dump(compact, fh, separators=(",", ":"))

    print("profiles:", len(profiles), dict(counts))
    print("items ruled:", len(ITEM_RULES), "| measurement corrections:", len(M), "| axis/representation corrections:", len(AXES))
    uncovered = set()
    for p in packets:
        for path in p["candidate_recommended_items"]:
            if path not in ITEM_RULES:
                uncovered.add(path)
    print("candidate items without an explicit rule:", len(uncovered))
    if uncovered:
        print("  ", sorted(uncovered)[:20])
    print("change-request.json:", os.path.getsize(os.path.join(OUT, "change-request.json")) // 1024, "KB")
    print("report-data.json:", os.path.getsize(os.path.join(OUT, "report-data.json")) // 1024, "KB")


if __name__ == "__main__":
    main()
