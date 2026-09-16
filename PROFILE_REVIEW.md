# Scientific review of a profile

Tests show that the comparison rules run as written. They do not show that the
rules are scientifically right. That judgement belongs to the reviewers.

## What the scientist receives

Each profile has a generated packet at:

```text
spec/v0.1/review-packets/<domain>/<profile-name>.json
```

The packet contains the profile’s exact digest, intended mapping, every field
listed in the source profile, comparison rules, worked scientific examples,
generated test cases and questions for review.

This is the complete mapping for that profile. The scientist does not need to
review unrelated fields from `source/fields.yaml`.

## What the scientist decides

The scientist checks:

- whether the profile describes one clear scientific concept;
- whether its intended use and limitations are honest and precise;
- which representations are scientifically interchangeable;
- the disposition of every proposed field: required, conditional, recommended
  or excluded;
- which missing facts should return `UNKNOWN`;
- which known contradictions should return `INCOMPATIBLE`;
- whether any conversion or inference is explicit and correctly classified;
- whether the examples have the right expected outcomes; and
- whether authoritative, versioned sources support the decisions.

Fields marked `under-review` in a draft must receive a final disposition before
approval.

## What approval means

Approval means that this one profile is a defensible and sufficiently precise
compatibility contract for its stated use. It does not approve a model,
dataset, result, clinical application, regulatory claim, consent basis or
future use.

## Required roles and evidence

A profile can move to `reviewed` only when it has:

- a named scientific reviewer who did not author the profile;
- a different named schema reviewer who did not author the profile;
- a named domain owner;
- a field-level decision for every field in the packet;
- a decision for every applicable contract area;
- pinned authoritative sources;
- confirmed examples and generated fixtures;
- a clear intended use and at least one limitation; and
- a review date.

The scientific reviewer judges the science. The schema reviewer checks that
those decisions are represented consistently. The domain owner accepts ongoing
stewardship and future retirement decisions.

## Recording the result

Copy:

```text
source/reviews/profile-review.template.yaml
```

to:

```text
source/reviews/<domain>/<profile-name>.yaml
```

Fill in the names, sources, section decisions, field decisions and reviewed
fixture names. The build checks the record against
`source/profile-review.schema.json` and verifies that the reviewers are
independent and that the packet is covered.

Until a complete record exists, the profile remains `release_eligible: false`.
All three current v0 profiles are in that state.
