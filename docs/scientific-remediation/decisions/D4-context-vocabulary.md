# D4. Subject and biological-context vocabulary

**Status:** Decided in part: option (b). Demotion implemented. **Owner:** unassigned. **Decided:** — . **Approved by:** —

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

**Adopted: option (b), CURIEs compared by subsumption against pinned snapshots — with the second
constraint implemented now and the first waiting on snapshots.**

Implemented: `semantic.subject` is no longer a required, compared field. It was required in all 650
profiles as free text up to 4096 characters and compared with string equality, which failed in both
directions at once — `blood_plasma` and `UBERON:0001969` compared unequal though they name the same
specimen, while the generated placeholder `biological_sample` matched itself across plasma, CSF and
tumour biopsy. Leaving a required field whose comparison is wrong is worse than not gating on it, so
it is now declared-but-not-gating (`RETIRED_REQUIRED_ITEMS`) until it is term-bound.

The related half of this decision landed under D5: a source declaring `any` or `unspecified` against
a specific target is UNKNOWN rather than a contradiction, and each domain's generated example
organism is now plausible for that domain instead of uniformly human.

**Not implemented, and gated on the same snapshot question as D3, D5 and D7.** Subsumption against
pinned UBERON, CL, OBI and MONDO snapshots needs those snapshots to be pinned, distributed and
owned, and the licensing and ownership of that pinning is the sub-question this record opens with.
Until then a differing subject is absent evidence, not a contradiction, which is what the demotion
above delivers.

**Per-profile, and therefore review work.** Which profiles should gate on the sampled entity at all
is the first constraint in the recommendation — "only where the sampled entity changes the meaning
of the value, decided per profile, not per domain". Deriving that from a profile's name or domain is
the heuristic D9 abolished, so it belongs to the domain review waves. The same applies to replacing
the placeholder subjects across 650 positive fixtures with real terms, and to whether core, chemical
and simulation profiles drop the subject requirement entirely.
