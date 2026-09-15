# D4. Subject and biological-context vocabulary

**Status:** Open. **Owner:** unassigned. **Decided:** — . **Approved by:** —

## Question

Should `semantic.subject`, tissue, cell type, compartment and assay be controlled terms, and which
of them may decide compatibility?

## Why it matters

`semantic.subject` is required in all 650 profiles as free text up to 4096 characters, compared with
string equality, and the generated examples are one placeholder per domain (`biological_sample`,
`nervous_system`, `data_value`). This fails in both directions: `blood_plasma` and
`UBERON:0001969` compare unequal though they are the same specimen, while the placeholder
`biological_sample` matches itself across plasma, CSF and tumour biopsy, which are not
interchangeable for any concentration measurement.

## Options

| Option | For | Against |
|---|---|---|
| (a) Keep free text | No dependency | Both error directions stay; the required field means nothing |
| (b) CURIEs from registered prefixes, compared by subsumption against pinned snapshots | Correct semantics; reuses maintained vocabularies | Snapshot infrastructure; licensing for some vocabularies |
| (c) A short Biosimulant-controlled list per domain | Implementable immediately | Reinvents UBERON and CL badly, and will not compose |

## Recommendation

Option (b), with two constraints. First, the field gates compatibility only where the sampled entity
changes the meaning of the value — decided per profile, not per domain. Second, until snapshots
exist, demote `semantic.subject` from required-and-compared to declared-and-not-gating, rather than
leaving a required field whose comparison is wrong.

## What adopting it changes

- A CURIE pattern with prefixes resolved against a pinned Bioregistry snapshot.
- Subsumption comparison against pinned UBERON, CL, OBI and MONDO snapshots.
- Positive fixtures across 650 profiles replace placeholder subjects with real terms.
- Core, chemical and simulation profiles may drop the subject requirement entirely.

## Sub-questions

1. Which vocabularies are in scope, and who maintains the snapshot pinning?
2. Does the target's term have to subsume the source's, or is any overlap enough?
3. How are composite specimens (whole blood vs plasma vs buffy coat) handled?
4. What happens when a needed term does not exist in any ontology?

## Tests

No case today; the correct behaviour depends on this decision. Add on adoption: a narrower specimen
term must satisfy a broader requirement; a missing snapshot must return UNKNOWN.

## Sources to pin

`uberon-2012`, `cl-2016`, `obi-2016`, `bioregistry-2022`.

## Decision

_To be recorded._
