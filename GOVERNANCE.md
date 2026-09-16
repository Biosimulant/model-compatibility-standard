# Governance

Biosimulant maintains this standard in the open on GitHub.

## Acceptance

The pull request is the review record. It should contain the reason for the
change, evidence, discussion, requested corrections and final approval. Merging
a profile into `main` accepts that profile for its stated use.

Review effort should match the change. A new biological interpretation may
need a domain scientist; a schema or comparison change may need an
implementation specialist. These people participate through the pull request.
The standard does not duplicate their names or signatures in profile data.

Automated tests confirm that the declared rules are well formed and behave
consistently. They do not prove that a scientific decision is correct, so the
pull request must make the scientific reasoning and sources inspectable.

## Profile status

Profiles have two lifecycle states:

| Status | Meaning |
|---|---|
| `active` | Accepted on `main` and available for new work. |
| `deprecated` | Kept for existing references, but not recommended for new work. |

If a profile has a serious error, publish a corrected version and deprecate the
affected one. Do not silently rewrite a published profile.

## Versions

Releases use semantic versioning. Once a version is released, its schemas,
profiles, rules and fixtures do not change. Fixes go into a new version.
`spec/v0.1/bundle.manifest.json` lists every generated file and SHA-256 digest
so consumers can verify the exact bundle.

Accepting a compatibility profile does not approve any model, dataset,
scientific result, clinical use or regulatory claim.
