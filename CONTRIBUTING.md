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

A profile change needs:

1. A stable id and version.
2. Requirements and comparison rules written as data.
3. Its generated fixtures: `positive`, `negative-required-missing` and
   `comparison-unknown`.
4. Authoritative scientific sources.
5. A named domain reviewer and a review date.
6. A description that sticks to whether interfaces fit together, not whether a
   model is scientifically valid.

## Adding a comparison operator

Implement it in both `python/` and `typescript/`, add tests in both, and check
that both give the same results on the shared fixtures in
`spec/v0.1/fixtures/golden/`.

## Before you open a pull request

Run the Python and TypeScript test suites. The README explains how.
