# Release procedure

Every release is immutable and uses the same source bundle in GitHub, npm, and Python packages.

1. Run `python scripts/build_standard.py --check`, Python tests, and `npm test`.
2. Confirm `bundle.manifest.json` lists every public file and has a reproducible digest.
3. Confirm every changed profile has positive, negative, and `UNKNOWN` fixtures.
4. Confirm profile review claims contain named reviewers, dates, and sources. Never infer approval from fixture success.
5. Tag the repository with the package version and publish the release archive.
6. Publish npm and Python artifacts built from that tag.
7. Publish immutable resources at the canonical BioSimulant URLs and verify their bytes against the bundle manifest.
8. Update downstream pins only after all published artifacts agree.

Changing a profile definition, schema, comparison rule, reason code, or normalization rule requires a new release. Existing release paths are never overwritten.
