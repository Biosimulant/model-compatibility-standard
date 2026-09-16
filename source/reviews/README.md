# Scientific review records

This directory holds one review record per profile:

```text
source/reviews/<domain>/<profile-name>.json
```

Start from `profile-review.template.json`. The record is checked against
`../profile-review.schema.json` when the standard is built.

A completed review names the scientific reviewer, a separate schema reviewer
and the domain owner. It records the sources, intended use, limitations,
field-by-field decisions and the examples that were checked. Neither reviewer
may be a profile author.

The generated review packet under `spec/v0.1/review-packets/` is the mapping the
scientist reviews. Every required and candidate field in that packet needs a
decision: required, conditional, recommended or excluded. The reviewer may also
identify a field that is missing from the proposal.

The build checks that sources are versioned and pinned, reviewers are
independent, every contract section has a decision, and the required fixtures
were reviewed. A name or signature by itself is not enough.

When the record is complete, the build can mark that profile
`release_eligible: true`. Automated tests and generated text do not count as
scientific approval. See [PROFILE_REVIEW.md](../../PROFILE_REVIEW.md) for the
full gate and [PROPOSING_A_PROFILE.md](../../PROPOSING_A_PROFILE.md) for the
submission process.
