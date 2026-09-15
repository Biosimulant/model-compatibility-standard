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
  missing information, and any conversions the profile allows. The generator
  currently makes only the first three (`positive`, `negative-required-missing`
  and `comparison-unknown`).
- A clear intended-use statement and at least one important limitation.
- A check that its rules only use operators listed in
  `spec/v0.1/rules/operators.json`.
- A review date, and a domain owner who decides when to deprecate it.

Until that evidence exists, the build keeps each profile's recorded review
status and sets `release_eligible` to `false`. Today that applies to all 650
profiles.

Review evidence is stored as one JSON file per profile under
`source/reviews/<domain>/<profile-name>.json`. Use
`source/reviews/profile-review.template.json`. The source schema and build check
the required names, dates, sources, decisions and fixture review. This keeps
domain work separate and avoids pretending that passing code tests is a
scientific sign-off.

The bundle calculates `ga_ready` from these files. It becomes `true` only when
all 650 profiles have complete review evidence.
