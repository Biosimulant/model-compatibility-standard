# Contributing

Released files never change. To fix a released profile, schema or rule, make the
change in a new version.

## How the spec is built

Everything in `spec/v0.1/` is generated, so don't edit it by hand.

1. Change `source/catalogue.review.json` (profiles, contract fields and packs) or
   `scripts/build_standard.py` (schemas, rules, reason codes and fixtures).
2. Run `python3 scripts/build_standard.py` to regenerate `spec/v0.1/`.
3. Commit the source change and the regenerated files together.

`npm test` and CI run `python3 scripts/build_standard.py --check`, which fails if
the two are out of sync.

## Adding or changing a profile

The v0 catalogue grows from observed model connections, not from a generated
list of possible biological concepts. Add one profile, or a small set that is
needed for the same workflow, in a change. Do not bulk-generate profiles.

A new profile starts with a concrete mapping: one model output, one model input,
and examples of the data each side actually emits or accepts. Record what must
match, what may be converted, what should be reported as unknown, and what must
block the connection. Then prepare the scientific review packet.

A profile change needs:

1. A stable id and version.
2. A stated use case, scope and important exclusions.
3. The complete output-to-input mapping that motivated it.
4. Requirements and comparison rules written as data.
5. Its generated fixtures: `positive`, `negative-required-missing` and
   `comparison-unknown`.
6. Authoritative scientific sources.
7. A named scientific reviewer, a separate schema reviewer and a review date.
8. A description that sticks to whether interfaces fit together, not whether a
   model is scientifically valid.

Keep the profile at `draft` and non-release-eligible until its review evidence
is complete. Adding a profile changes the generated catalogue counts; tests
derive those counts from the catalogue and must not hard-code a target size.

## Adding a comparison operator

Implement it in both `python/` and `typescript/`, add tests in both, and check
that both give the same results on the shared fixtures in
`spec/v0.1/fixtures/golden/`.

## Before you open a pull request

Run the Python and TypeScript test suites. The README explains how.
