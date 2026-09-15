# D2. Comparing fields both ports declare

**Status:** Decided: option (b). Implemented. **Owner:** unassigned. **Decided:** — . **Approved by:** —

## Question

When a profile does not require a field, but both contracts declare it, should the comparison
evaluate it?

## Why it matters

Today it does not, and that is the single largest source of false passes. Verified: raw counts
against log-normalised expression, Ensembl IDs against HGNC symbols, a value in mg against a value
in s, GRCh37 coordinates against GRCh38, and a simulated value against a port requiring measured
data all return DIRECT_COMPATIBLE.

`spec/v0.1/catalogue/items.json` already promises the opposite for all 266 items: "Checked only
when the profile requires it or both contracts include it." So either the behaviour or the
published wording is wrong.

## Options

| Option | For | Against |
|---|---|---|
| (a) Keep profile-required fields only | Predictable; small rule sets | Contradicts the published item semantics; the false passes above remain |
| (b) Compare a defined list of interpretation-changing items when both declare them | Matches the documented promise; targets the real failures | The list must be justified per item family |
| (c) Compare every field both ports declare | Simple rule | Turns incidental metadata differences into blocking results |

## Recommendation

Option (b), implemented with the existing `missing: "ignore"` behaviour, which already means "skip
when either side is silent, compare when both declare". The starting list: `measurement.unit`,
`scale`, `normalization`, `baseline`, `aggregation`; `identifiers.namespace` and
`namespace_version`; `representation.ordering` and `feature_space`; `dimensions.axes`;
`lifecycle.time_unit`; `origin.type`; and `representation.reference_assembly`.

## What adopting it changes

- Rule generation in `scripts/build_standard.py` emits comparison rules for declared-optional items,
  not just required ones.
- Items documentation either matches the behaviour or is corrected.
- The UNKNOWN and INCOMPATIBLE rate on real manifests will rise. Measure it before and after: an
  over-broad list is its own failure mode.

## Sub-questions

1. Is the list per item family, per profile class, or a single global list?
2. Should a declared-optional mismatch be INCOMPATIBLE, or a weaker "conditional" status?
3. Does comparing `origin.type` belong here or in the policy layer (D12)?

## Tests

Settles BMCS-SCI-001, 002, 003, 014 and 015.

## Sources to pin

`wagner-2012-tpm`, `robinson-2010-tmm`, `ensembl-2024`, `bioregistry-2022`.

## Decision

**Adopted: option (b), compare a defined list when both ports declare it.** Implemented as
`COMPARED_WHEN_BOTH_DECLARE` in `scripts/build_standard.py`: every profile now emits rules with
`missing: "ignore"` for unit, scale, transform, quantity, normalization, baseline, aggregation,
identifier namespace and version, ordering, feature space, reference assembly, coordinate system,
axes, time unit, temporal meaning, origin type and compartment.

The published item semantics and the behaviour now agree. Settles BMCS-SCI-001, 002, 003, 014
and 015.
