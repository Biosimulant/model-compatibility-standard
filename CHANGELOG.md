# Changelog

## Unreleased

- Added a browser-safe TypeScript entry point with the full public schema and
  profile bundle for offline manifest and contract validation.
- Added browser-entry conformance tests and an explicit package export.

- Resolver preconditions now run in Python and TypeScript instead of being
  skipped.
- Compatibility reports and plans now record every verified ontology and
  identifier-mapping snapshot that affected the result.
- The Python package now includes a `py.typed` marker for typed consumers.

- Added TypeScript normalization, compatibility locks and deterministic graph
  resolution with the same cost ordering, ambiguity and revocation behavior as
  Python.
- Implemented the complete declarative operator vocabulary in both languages.
  Ontology and mapping operations require an exact content-verified snapshot.
- Added fail-closed resource limits and installed-bundle integrity verification
  in both packages.
- Accepted-profile contracts are now validated as refinements and cannot change
  common input invariants.
- Added a cross-language conformance process that compares normalized contracts,
  locks, reports, plans and all resulting digests byte-for-byte.

- Rewrote the README and the other docs in plain language, and made them match
  what the code actually does, including a list of what isn't implemented yet.
- Reworded the text inside the spec: profile descriptions, notes and disclaimers,
  pack descriptions, contract field notes, and reason-code messages. Fixed the
  casing of 24 profile labels (for example CRISPR, SMILES and InChI). Profile
  names and URLs are unchanged, but every profile sha256 and the bundle digest
  change.
- Python now reports an unknown profile as `BMCS_PROFILE_UNRESOLVED`, the same as
  TypeScript. It used to report `BMCS_REFERENCE_UNRESOLVED`, which isn't a
  defined reason code.
- Reordered labels (`labels-permutation`) now count as a lossless conversion in
  both languages. Python used to report them as lossy.
- Reworded finding explanations and validation messages. They're now identical
  in Python and TypeScript, so both produce the same report digest.
- Both test suites now run every profile's `comparison-unknown` fixture.
- The Python package now declares its `referencing` dependency. Both packages
  list a homepage, issue tracker and author.
- `scripts/build_standard.py` has `--help` text, and its errors say how to fix
  the problem.

## 0.1.0-alpha.2

- Fixed the capitalization of the Biosimulant name in package metadata, the docs
  and the port contract schema title.
- Released as a new version, so the `0.1.0-alpha.1` files stay unchanged.

## 0.1.0-alpha.1

First public draft.

- JSON Schemas (Draft 2020-12) for port contracts, profiles, comparison reports,
  resolution plans, locks and related objects.
- 650 profiles built from 266 contract fields, grouped into 30 reusable packs.
- A fixed list of comparison operators. Rules are written as data.
- Python and TypeScript packages that validate manifests and contracts, produce
  canonical JSON and sha256 digests, and compare contracts. Findings use the same
  status values as the report.
- Python only: compatibility locks, and resolution plans that search for the
  cheapest chain of reviewed adapters or inference models.
- Shared test vectors so both languages can be checked against the same results.
- Packages can be installed straight from a git commit.
- Example `model.yaml` files with and without a `compatibility` block.

None of the profiles has finished scientific review.
