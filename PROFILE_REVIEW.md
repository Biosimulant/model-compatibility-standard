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
- Fixtures for a valid contract, a missing required field, a comparison with
  missing information, and any conversions the profile allows. The generator
  currently makes only the first three (`positive`, `negative-required-missing`
  and `comparison-unknown`).
- A short statement of what the profile is for and what it doesn't cover. The
  profile format has no field for this yet.
- A check that its rules only use operators listed in
  `spec/v0.1/rules/operators.json`.
- A review date, and a domain owner who decides when to deprecate it.

Until that evidence exists, the build keeps each profile's recorded review
status and sets `release_eligible` to `false`. Today that applies to all 650
profiles.
