# Profile review files

This directory holds the evidence that moves a profile from `candidate` or
`draft` to `reviewed`. One completed JSON file covers one profile. Put it at:

```text
source/reviews/<domain>/<profile-name>.json
```

Start with `profile-review.template.json` and validate it against
`../profile-review.schema.json`. The build also checks rules that JSON Schema
cannot express clearly:

- the profile must exist in the catalogue;
- the scientific and schema reviewers must be different people;
- neither reviewer can be one of the profile authors;
- every contract section must be included, conditional, or explicitly excluded,
  with a decision and source;
- every source used by a decision must exist in the same review file; and
- each source must name a version and pin the reviewed bytes with SHA-256; and
- positive, missing, invalid, direct, incompatible, `UNKNOWN`, and applicable
  transformation fixtures must have been checked.

Adding a name is not enough. The reviewer must check the actual profile rules,
fixtures, intended use and limits. Do not use generated text as scientific
approval.

The standard build sets `release_eligible: true` only after the review file is
complete. `ga_ready` becomes true only when all 650 profiles are eligible.
