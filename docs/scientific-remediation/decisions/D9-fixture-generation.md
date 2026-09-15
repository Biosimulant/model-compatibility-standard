# D9. Fixture generation

**Status:** Open. **Owner:** unassigned. **Decided:** — . **Approved by:** —

## Question

Where do the values in generated fixtures come from?

## Why it matters

They come from substring matches on profile names, in `scripts/build_standard.py`:

- `measurement_unit()` tests whether the name contains `concentration`, `mass`, `rate`, `time` and
  so on. "integ**rate**d-embedding" gets `1/s`.
- The scale branch tests for `ratio`, which is a substring of "concent**ratio**n", so all 14
  concentration profiles are declared on a `probability` scale, as are migration, proliferation and
  glomerular filtration rates.
- `axis_names()` gives anything containing `volume` the image axes `[x, y]`, so stroke volume and
  volume of distribution get spatial axes while CT and MRI volumes get two axes instead of three.
- `incompatible_value()` hard-codes `kg`, so every profile measured in `g` asserts that g and kg are
  incompatible.
- Every profile requiring a unit gets the same `nM` to `uM` conversion fixture.

Because fixtures are the cross-language conformance suite, these become the behaviour both
implementations are tested to agree on.

## Options

| Option | For | Against |
|---|---|---|
| (a) Fix the substring lists | Quick | The mechanism stays wrong; the next profile name breaks it again |
| (b) Take every value from explicit per-profile declarations | Correct and reviewable | 650 profiles need declarations, which is what the pilot and domain waves are for |
| (c) Declarations for reviewed profiles, heuristics for the rest | Incremental | Two classes of fixture; the unreviewed ones keep asserting false things |

## Recommendation

Option (b). Remove the heuristics entirely. Units, scales, axes and example values come from
`source/catalogue.review.json`, per profile. Conversion fixtures are derived from the profile's own
dimension; contradiction fixtures pick a unit of a *different* dimension; and the generator emits
target-side UNKNOWN fixtures as well as source-side ones.

## What adopting it changes

- Generator rewritten around declarations, which is the precondition for Phase 3 regeneration.
- Fixture invariants become enforceable in CI rather than only in the scientific suite.
- Lossy and inference fixtures become generatable (D11).

## Sub-questions

1. What does the generator do for a profile with no declarations yet — refuse, or emit a minimal
   fixture marked incomplete?
2. Do the fixture invariants move into the main test suite once they pass?

## Tests

Settles BMCS-SCI-011, 012 and 013, and makes guard 107 (target-side UNKNOWN) generated rather than
hand-written.

## Sources to pin

`vim-jcgm-200-2012`, `ucum-2.2`, `stevens-1946`.

## Decision

_To be recorded._
