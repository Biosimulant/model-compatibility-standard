# Releasing

A release is one bundle, published the same way to GitHub, npm and PyPI. Once
it's published, it never changes.

1. Run `python3 scripts/build_standard.py --check`, the Python tests and `npm test`.
2. Check that `spec/v0.1/bundle.manifest.json` lists every file, and that
   rebuilding gives the same `bundle_sha256`.
3. Check that every changed profile has its `positive`,
   `negative-required-missing` and `comparison-unknown` fixtures.
4. Check that any profile marked `reviewed` names its reviewer, review date and
   sources. Passing fixtures doesn't count as approval.
5. Set the new version in `package.json`, `package-lock.json`, `pyproject.toml`,
   `python/src/biosimulant_model_compatibility_standard/__init__.py` and the
   `release` field in `scripts/build_standard.py`. Regenerate the spec and add a
   CHANGELOG entry.
6. Tag the commit with the version (for example `v0.1.0-alpha.2`) and create the
   GitHub release.
7. Publish the npm and Python packages from that tag.
8. Publish the spec files at their biosimulant.com URLs, and check their bytes
   against the bundle manifest.
9. Update pins in other repositories only after all of the above match.

Any change to a profile, schema, comparison rule, reason code or normalization
rule needs a new release. Never overwrite files from an earlier release.
