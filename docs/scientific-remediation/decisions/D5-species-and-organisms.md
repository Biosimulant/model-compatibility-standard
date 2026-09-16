# D5. Species and multi-organism context

**Status:** Decided in part. Implemented. **Owner:** unassigned. **Decided:** — . **Approved by:** —

## Question

What does `biological_context.species` mean, what does the value `any` mean, and how does a port
describe more than one organism?

## Why it matters

575 profiles require a single `NCBITaxon` value compared by `context-compatible`, which is
implemented as `source == target or target in (None, "any", "unspecified")`. Consequences, all
verified:

- Source `any` against a human-only target returns INCOMPATIBLE, though under every candidate
  meaning of `any` the answer should be compatible or UNKNOWN.
- Source human against target `any` returns DIRECT_COMPATIBLE, so the wildcard is asymmetric.
- A strain never satisfies a species-level requirement, because there is no subsumption.
- Community, host-pathogen and ecological profiles cannot express their organisms at all: the
  generated fixture for a microbial community declares `NCBITaxon:9606`.

## Options

| Option | For | Against |
|---|---|---|
| (a) Keep one value, define `any` precisely | Minimal change | Still cannot express host plus pathogen, or a community |
| (b) One value plus taxonomic subsumption over a pinned NCBI Taxonomy snapshot | Fixes strain-vs-species | Multi-organism ports still unrepresentable |
| (c) (b) plus a role-typed taxa list (`host`, `pathogen`, `community_member`, `donor`) | Expresses what the science needs | New item; more to validate |

## Recommendation

Option (c), and separate four states that are currently conflated: omitted (no evidence, UNKNOWN);
declared species; species-independent content, declared explicitly; and a target that accepts any
species. Retire the bare `any` on the source side unless it is given one of those meanings.

## What adopting it changes

- A `biological_context.taxa[]` item with roles, used by virology, microbiology, ecology and
  epidemiology profiles.
- Taxonomic subsumption against a pinned NCBI Taxonomy snapshot.
- Positive fixtures rebuilt per domain with plausible organisms, replacing the blanket human taxon.

## Sub-questions

1. Is `species-independent` a value of the species field or a separate declaration?
2. May a target declare an acceptance set (several taxa, or a subtree)?
3. For host-associated community data, is the host required, recommended or optional?

## Tests

Settles BMCS-SCI-010, and must keep guards 101 (omitted species returns UNKNOWN) and 106 (human vs
mouse stays incompatible) passing. Add on adoption: a strain must satisfy a species-level
requirement.

## Sources to pin

`ncbitaxon-schoch-2020`, `bioregistry-2022`, `obi-2016`.

## Decision

**Adopted in part.** Implemented now:

- A source declaring `any` or `unspecified` against a specific target returns UNKNOWN, not
  INCOMPATIBLE. Absent evidence is not a contradiction. Settles BMCS-SCI-010.
- `source/context-declarations.json` gives each domain a plausible example organism, so a microbial
  community, a viral titre and an ecological abundance are no longer all labelled human.

Also fixed here, because it belongs to the same operator: `context-compatible` is applied to every
`biological_context` item, and `intervention` is the one whose value is an array. TypeScript compared
the two sides with `===`, which for an array tests object identity, so two identical intervention
lists were reported as a contradiction while Python called them a match. Both engines now compare by
value, and `BMCS-SCI-109` guards it. The defect reached only the three pharmacology profiles that
declare an intervention; the other eight context fields are strings and were never affected.

**The role-typed taxa item now exists.** `biological_context.taxa[]` takes a `taxon` and a `role`
— `host`, `pathogen`, `community_member` or `donor` — with an optional label and strain. A single
`species` field could not describe a host and its pathogen, or the members of a community, so a
virology port had no way to say "human host, SARS-CoV-2 pathogen" and an ecology port had to pick
one organism and drop the rest. The item is set-like, because the order organisms are listed in
carries no meaning.

No profile requires it. Which ports need role-typed taxa, and which roles each one needs, is a
judgement about that profile's science and belongs to the domain review; what changed is that the
vocabulary to express it now exists.

**Still open:** taxonomic subsumption, so that a strain satisfies a species-level requirement. That
needs a pinned NCBI Taxonomy snapshot, and the ownership and licensing of the snapshots is the
question D3, D4 and D7 are all waiting on too. The snapshot *format* is now published as
`ontology-snapshot.schema.json`; what is missing is who produces and pins the content.
