# D7. Identifier mapping and loss

**Status:** Open. **Owner:** unassigned. **Decided:** — . **Approved by:** —

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

_To be recorded._
