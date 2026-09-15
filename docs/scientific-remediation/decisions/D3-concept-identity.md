# D3. Concept identity and external meaning

**Status:** Decided in part: option (b). Terms minted and published. **Owner:** unassigned. **Decided:** — . **Approved by:** —

## Question

What identifies the scientific meaning of a port, and what happens to the provisional
`.../v0.1#concept` identifier?

## Why it matters

Every profile fixes `semantic.concept` to an IRI minted inside its own versioned document, and
compares it with `equal`. Validation already forces both contracts to hold that constant, so the
rule cannot fail between two valid contracts of the same profile: it restates profile identity and
carries no scientific meaning. Because the IRI embeds `/v0.1`, a v0.2 profile would report every
v0.1 port as INCOMPATIBLE even when the meaning is unchanged.

## Options

| Option | For | Against |
|---|---|---|
| (a) Keep as is | No work | Tautological, and breaks across versions |
| (b) Version-independent Biosimulant term, plus a mapping to external ontology terms where one exists | Stable identity; external meaning where it is available | Needs a term registry and snapshot infrastructure |
| (c) External ontology term only | Maximum interoperability | No ontology defines "a Biosimulant contract for X"; loses the contract boundary |

## Recommendation

Option (b). Mint terms outside the versioned profile document, for example
`https://biosimulant.com/standards/model-compatibility/terms/<domain>/<name>`, each with a label, a
definition and its own term-level version. Require `semantic.ontology_terms` — with `uri`,
`ontology`, `version` and `relation` — **where a maintained external term exists at the right
granularity**, decided per profile in the pilot rather than for all 650 at once (erratum E3).
Compare by `term-equivalent` or `term-subsumes` against a pinned snapshot; no snapshot means
UNKNOWN, which the engine already does.

## What adopting it changes

- Term minting and a published term registry with its own lifecycle.
- Ontology snapshot pinning and distribution, shared with D4, D5 and D7.
- A cross-version fixture: the same term under two profile versions must not be INCOMPATIBLE.

## Sub-questions

1. Who maintains the term registry, and what is its deprecation policy?
2. Do terms live in the bundle or at a resolvable URL, and what is the offline story?
3. Which relation values are permitted, and does a broad match satisfy a narrow requirement?

## Tests

No case today: the defect is structural rather than a wrong answer. Add on adoption: a v0.1 term and
its v0.2 successor must not be INCOMPATIBLE; a missing ontology snapshot must return UNKNOWN.

## Sources to pin

`obo-fp-003`, `w3c-cooluris`, `bioregistry-2022`, `obi-2016`, `uo-2012`.

## Decision

**Adopted: option (b), a version-independent Biosimulant term with external terms attached where one
exists.** The minting and the registry are implemented; deciding which profiles have a maintained
external term is not, and stays per-profile review.

Implemented:

- The concept IRI is minted outside the versioned profile document, as
  `.../terms/<domain>/<name>`. It no longer carries `/v0.1`, so a v0.2 profile does not report every
  v0.1 port as incompatible when the meaning has not changed.
- `spec/v0.1/catalogue/terms.json` publishes all 650 terms with a label, a definition, the domain,
  the profile that mints the term, the profile version it was minted in, and a `term_version` that
  moves independently of the profile version. Label and definition are the profile's own reviewed
  text rather than anything newly invented.
- The generator now rejects a `semantic.concept` that embeds a profile version. That check runs over
  every profile through `internal_quality_errors`, which the bundle tests assert is empty, so the
  version-independence this decision turns on cannot regress silently.

The tautology this record opens with is unchanged and deliberate: validation fixes both contracts to
the same constant, so the rule cannot fail between two valid contracts of the same profile. What the
change buys is that the constant now means something stable across versions, and that there is a
registry where a term's meaning can be stated, versioned and pointed at.

**Still open, and deliberately so.** `semantic.ontology_terms` is not required. The pre-review's
blanket "require it for all 650" was withdrawn as erratum E3, and the recommendation here is
explicit that it applies only "where a maintained external term exists at the right granularity,
decided per profile in the pilot". Every term therefore ships with an empty `external_terms`, which
is an honest absence rather than a placeholder. Comparison by `term-equivalent` or `term-subsumes`
already returns UNKNOWN without a pinned snapshot, so the engine behaves correctly in the meantime.

The registry's ownership and deprecation policy, and whether terms resolve at a URL as well as in
the bundle, are governance questions this record cannot answer on its own.
