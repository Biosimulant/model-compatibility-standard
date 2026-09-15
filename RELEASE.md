# Releasing

A release is one bundle, published the same way to GitHub, npm and PyPI. Once
it's published, it never changes.

1. Run `python3 scripts/build_standard.py --check`, the Python tests and `npm test`.
2. Check that `spec/v0.1/bundle.manifest.json` lists every file, and that
   rebuilding gives the same `bundle_sha256`.
3. Check that every changed profile has its `positive`,
   `negative-required-missing` and `comparison-unknown` fixtures.
4. Check that any profile marked `reviewed` has a complete file under
   `source/reviews/`. It must name separate scientific and schema reviewers,
   record sources and decisions, and confirm the required fixtures. Passing
   fixtures doesn't count as approval.
5. Run `npm run test:scientific`. It runs the scientific checks in strict mode, where
   every known defect is an ordinary failing test. A stable release requires this to
   pass with no defect case left open. See `scientific-checks/README.md` and
   `docs/scientific-remediation/REMEDIATION_PLAN.md`.
6. Set the new version in `package.json`, `package-lock.json`, `pyproject.toml`,
   `python/src/biosimulant_model_compatibility_standard/__init__.py` and the
   `release` field in `scripts/build_standard.py`. Regenerate the spec and add a
   CHANGELOG entry.
7. For a stable release, also check `ga_ready: true` in the generated bundle.
   Do not override this gate.
8. Tag the commit with the version (for example `v0.1.0-alpha.2`) and create the
   GitHub release.
9. Publish the npm and Python packages from that tag.
10. Publish the spec files at their biosimulant.com URLs, and check their bytes
   against the bundle manifest.
11. Update pins in other repositories only after all of the above match.

Any change to a profile, schema, comparison rule, reason code or normalization
rule needs a new release. Never overwrite files from an earlier release.
