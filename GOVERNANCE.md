# Governance

Biosimulant maintains this standard in the open, on GitHub.

## Versions

Releases use semantic versioning. Once a version is released, its schemas,
profiles, rules and fixtures never change; fixes go into a new version.
`spec/v0.1/bundle.manifest.json` lists every file with its sha256, so anyone can
check that they have exactly what was released.

## Two kinds of review

- **Technical review** checks that the schemas, rules and code behave as the
  specification says.
- **Domain review** checks that a profile correctly describes the kind of
  biological data it covers. It needs a named scientist. See
  [PROFILE_REVIEW.md](PROFILE_REVIEW.md).

Neither review says that a model is scientifically valid or safe for clinical use.

## Profile review status

Each profile records its status in `review.status`. The catalogue summary in
`spec/v0.1/catalogue/catalogue.json` repeats it as `review_status`.

| Status | Meaning |
|---|---|
| `candidate` | Proposed. No review evidence yet. |
| `draft` | Under review, not approved yet. |
| `reviewed` | Approved by the named domain reviewer. |
| `deprecated` | Still valid in existing locks, but don't use it for new work. |
| `revoked` | Has a serious error. Don't use it in new plans. |
