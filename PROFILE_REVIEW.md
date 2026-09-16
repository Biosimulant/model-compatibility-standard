# Profile review

Passing tests and passing scientific review are separate things. Tests show the
validators behave as written. They don't show that a profile is biologically
right.

A profile can move to `reviewed` only when it has all of the following:

- Decisions for each part of the contract that applies to it: meaning,
  representation, identifiers, measurement, biological context, timing, origin,
  uncertainty and file format.
- Primary or authoritative sources that back those decisions.
- A named scientific reviewer who didn't write the profile.
- A different named schema reviewer who didn't write the profile.
- Fixtures for a valid contract, a missing required field, a comparison with
  an invalid value, direct compatibility, a known incompatibility, missing
  information, and any conversions the profile allows.
- A clear intended-use statement and at least one important limitation.
- A check that its rules only use operators listed in
  `spec/v0.1/rules/operators.json`.
- A review date, and a domain owner who decides when to deprecate it.

Until that evidence exists, the build keeps each profile's recorded review
status and sets `release_eligible` to `false`. Today that applies to all active
incubator profiles.

## Internal pre-review

Every profile has a generated packet under
`spec/v0.1/review-packets/<domain>/<profile-name>.json`. The packet contains the
exact profile digest, proposed fixed and allowed values, required and
recommended fields, comparison rules, fixture names, reviewer questions and
the remaining approval roles.

`spec/v0.1/catalogue/internal-validation.json` records the machine-checkable
result for every active profile. `ready-for-external-review` means that the profile
is distinct, typed, schema-valid and fixture-backed in both implementations. It
does not mean that its scientific choices have been approved.

Review evidence is stored as one JSON file per profile under
`source/reviews/<domain>/<profile-name>.json`. Use
`source/reviews/profile-review.template.json`. The source schema and build check
the required names, dates, pinned sources, decisions and fixture review. A
reviewer must include or explicitly exclude every contract section. This keeps
domain work separate and avoids treating passing code tests as a scientific
sign-off.

The bundle calculates `ga_ready` from these files. It becomes `true` only when
every active profile has complete review evidence. Adding a future profile does
not invalidate previously completed profile reviews.
