# Releasing

A release is one immutable bundle published consistently to GitHub, npm, PyPI
and the public specification URLs.

1. Confirm that every profile intended for publication is `active` or
   deliberately `deprecated`, and that its sources, mappings, examples,
   intended use and limitations are complete.
2. Run `python3 scripts/build_standard.py --check`, the Python tests and
   `npm test`.
3. Confirm that `spec/v0.1/bundle.manifest.json` lists every file and that a
   rebuild gives the same `bundle_sha256`.
4. Run `npm run test:scientific`; every profile-authored example in
   `spec/v0.1/fixtures/scientific.json` must pass in both implementations.
5. Set the version in `package.json`, `package-lock.json`, `pyproject.toml`,
   `python/src/biosimulant_model_compatibility_standard/__init__.py` and
   `scripts/build_standard.py`. Regenerate the bundle and update the changelog.
6. Tag the commit, create the GitHub release, and publish the npm and Python
   packages from that tag.
7. Publish the specification files and verify their bytes against the bundle
   manifest.
8. Update exact pins in dependent repositories only after the release commit
   and bundle digest are final.

The merged pull requests are the approval history. Do not create a second
release gate from separate reviewer records. Any change to a published profile,
schema, comparison rule, reason code or normalisation rule requires a new
release; never overwrite an earlier release.
