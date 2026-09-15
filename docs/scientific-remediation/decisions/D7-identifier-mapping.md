# D7. Identifier mapping and loss

**Status:** Decided in part: option (c). Mapping loss implemented. **Owner:** unassigned. **Decided:** — . **Approved by:** —

## Question

When does translating identifiers between namespaces preserve the data, and when does it lose
something that needs approval?

## Why it matters

Ensembl gene IDs and HGNC symbols declared on both ports return DIRECT_COMPATIBLE today: the
mapping is invisible. But the pre-review's opposite claim — that identifier mapping is always lossy
— is also wrong. A pinned mapping that is total over the declared feature universe and bijective on
it loses nothing. The standard needs to tell those cases apart, and it already has the operators
(`mapping-total`, `mapping-bijective`) to do it.

## Options

| Option | For | Against |
|---|---|---|
| (a) Treat namespace differences as INCOMPATIBLE | Safe | Blocks routine, correct couplings |
| (b) Treat mapping as always lossy, requiring approval | Visible | Wrong for complete bijective maps; approval fatigue |
| (c) Decide from the mapping's declared properties | Correct | Requires mappings to be pinned and characterised |

## Recommendation

Option (c). Lossless when a mapping snapshot is pinned by digest, total over the source's declared
feature universe, and bijective on it. Lossy, requiring approval, when it is partial or
many-to-one, with `unmapped_handling` declared. UNKNOWN when no snapshot is supplied. A namespace
version change within one namespace (Ensembl 110 to 114) is itself a mapping, because identifiers
are retired and merged.

## What adopting it changes

- Mapping snapshots pinned, distributed and versioned, sharing infrastructure with D3, D4 and D5.
- `identifiers.mapping_refs[]` with `release`, `sha256`, `cardinality` and `coverage` becomes
  required whenever a mapping is applied.
- Feature-universe digests (`dimensions.feature_labels_sha256`) become the cheap equality check that
  avoids mapping altogether.

## Sub-questions

1. Who publishes and pins the mappings — the bundle, or the workspace?
2. Is bijectivity required over the whole namespace, or only over the declared feature universe?
3. How is a mapping's own provenance and licence recorded?

## Tests

Settles BMCS-SCI-002 and contributes to 014. Add on adoption: a pinned total bijective mapping must
be lossless; a partial mapping must require approval.

## Sources to pin

`bioregistry-2022`, `ensembl-2024`.

## Decision

**Adopted: option (c), decide from the mapping's declared properties.** The core is implemented.

The operators already told total from bijective correctly; what they threw away was the answer.
Both engines returned a bare boolean, so a pinned mapping surfaced as `DIRECT_COMPATIBLE` and a
merging mapping was indistinguishable from a reversible one — the "the mapping is invisible" problem
this decision was written about. They now report loss, and all four outcomes are pinned in both
languages:

| Mapping | Status | Policy |
|---|---|---|
| Pinned, total, bijective | `LOSSLESS_CONVERSION_AVAILABLE` | ALLOW |
| Pinned, total, merges identifiers | `LOSSY_CONVERSION_REQUIRES_APPROVAL` | APPROVAL_REQUIRED |
| Pinned, not total over the declared universe | `INCOMPATIBLE` | BLOCK |
| No snapshot supplied | `UNKNOWN` | BLOCK |

A bijective translation is lossless but it is still a *conversion*, not a direct match, which is why
it reports `LOSSLESS_CONVERSION_AVAILABLE` rather than `DIRECT_COMPATIBLE`. This settles
BMCS-SCI-002. The coverage lives in the operator tests of both languages rather than in a profile
fixture, because a `compare` case in the scientific-checks file cannot carry a pinned snapshot.

**Implemented: a namespace version change is a mapping.** Ensembl 110 against 114 was a flat
contradiction, which asserts knowledge nobody has — identifiers are retired and merged between
releases, so the question is what the transition did. `mapping-total` could not answer it: it
requires list-valued feature universes and returns false for anything else, while
`identifiers.namespace_version` is a scalar. A `namespace-version-compatible` operator now decides
it against a pinned release-transition snapshot, whose format the standard publishes as
`namespace-transition-snapshot.schema.json`:

| Situation | Status |
|---|---|
| Same release | direct match |
| Transition pinned, nothing retired or merged | `LOSSLESS_CONVERSION_AVAILABLE` |
| Transition pinned, identifiers retired or merged | `LOSSY_CONVERSION_REQUIRES_APPROVAL` |
| No snapshot, or a snapshot silent on this pair | `UNKNOWN` |

The change reaches all 650 profiles, because `identifiers.namespace_version` carries a rule
everywhere through `COMPARED_WHEN_BOTH_DECLARE`, not only in the ~100 that require it. Generated
`comparison-unknown-no-snapshot-*` fixtures rose from 10 to 123 accordingly, since a differing
release with no pinned transition is now absent evidence rather than a contradiction.

**Still open, and per-profile.** `identifiers.mapping_refs[]` becoming required wherever a mapping is
applied stays review work: `mapping_refs`, `unmapped_handling` and `ambiguity_handling` are each
required by exactly 2 of the 650 profiles today, and deciding which profiles apply a mapping is a
judgement about each profile's data, not a rule a generator can derive. Publishing and pinning the
mappings themselves is the same snapshot-ownership question D3, D4 and D5 all wait on.
