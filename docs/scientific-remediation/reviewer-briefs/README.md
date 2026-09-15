# Reviewer briefs

What a scientific reviewer is being asked to do, per group of domains. Use these to recruit.

Every profile needs two named people who did not author it: a **domain-qualified scientific
reviewer**, who judges whether the profile describes the science correctly, and a **schema and
compatibility reviewer**, who judges whether the rules are expressible and consistent. They must be
different people. Git history names one author for all current profile source, and the pilot
dossiers were drafted with AI assistance, so neither the author nor the assistant can review.

| Brief | Domains | Profiles | Pilot profiles |
|---|---|---|---|
| [Wave A](wave-a-physiology-and-clinical.md) | physiology, cardiopulmonary-renal, clinical, epidemiology, phenotype, pharmacology | 150 | 6 |
| [Wave B](wave-b-omics.md) | genome, transcriptome, epigenome, proteome, metabolome, lipidome-glycome, multiomics | 175 | 5 |
| [Wave C](wave-c-cells-organisms-populations.md) | cell, immunology, microbiology, virology, developmental, ecology, evolution | 175 | 3 |
| [Wave D](wave-d-structure-space-computation.md) | chemical, imaging, spatial, neuroscience, simulation, core | 150 | 6 |

## What every reviewer should know before agreeing

**The work comes in two stages.** The pilot (Phase 2) is a handful of profiles reviewed in depth,
which also tests whether the review format works. The domain wave (Phase 4) is the rest of the
domain, reviewed against rules the pilot has already settled, so it is faster per profile.

**Approving a profile is a narrow claim.** It says the profile gives a defensible and precise
compatibility contract for its stated use. It does **not** say a model using it is scientifically
valid, clinically safe, or fit for regulatory use. That sentence is in the standard and should be in
the reviewer's mind, because it is the difference between a reasonable ask and an unreasonable one.

**What the reviewer receives.** A dossier per pilot profile with the proposed meaning, the fields a
port must declare and why each one matters, the comparison outcomes, the fixtures, open questions,
and the sources to pin. For wave profiles, the same in condensed form, plus what changed in
regeneration.

**What the reviewer produces.** A completed evidence file under `source/reviews/<domain>/`, naming
them, recording a decision for each contract area, the sources behind those decisions pinned by
SHA-256, and a confirmation that the fixtures were checked. `PROFILE_REVIEW.md` is the definition of
complete.

**What the reviewer does not decide.** Cross-cutting design questions — the unit model, identifier
mapping, ontology choices — are decided once, in
[the decision records](../decisions/), rather than per profile. A reviewer who disagrees with one
should say so; that reopens the decision rather than creating a per-profile exception.

**Effort, roughly.** A pilot profile takes half a day for a first pass, because the reviewer is also
judging the format and the open questions. A wave profile takes one to two hours once the class
rules are settled. These are estimates from the dossier contents, not measurements; the pilot exists
partly to replace them with real numbers.

**Conflict of interest.** Reviewers should declare involvement with the models or datasets a profile
is likely to describe. Being a user of the standard is fine; having authored the profile is not.
