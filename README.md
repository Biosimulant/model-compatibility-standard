# Biosimulant Model Compatibility Standard

Open, versioned schemas, profiles, rules, conformance fixtures, and reference
validators for compatibility between executable biological model ports.

The standard is additive to Biosimulant `model.yaml` schema `2.0`. Models that
do not declare a `compatibility` block keep their existing behavior.

## Status

The `v0.1` material is a pre-GA implementation draft. The imported catalogue
contains 650 machine-executable profile definitions, but profiles remain
scientifically non-GA until their domain sources and reviewer sign-offs are
complete. Validation success is not a claim of scientific validity, clinical
safety, or regulatory suitability.

## Repository layout

- `source/catalogue.review.json` — reviewed input catalogue used to generate
  the profile registry.
- `spec/v0.1/` — canonical schemas, profiles, rules, examples, and fixtures.
- `python/` — Python validator, normalizer, digest, and comparator package.
- `typescript/` — TypeScript implementation using the identical bundle.
- `scripts/build_standard.py` — deterministic generator and integrity checker.
- `python/tests/` and `typescript/test/` — conformance tests in both languages.

## Build and verify

```bash
python3 scripts/build_standard.py --check
python3 -m pip install -e '.[test]'
python3 -m pytest python/tests

npm install
npm test
```

The GitHub Actions workflow is staged at `ci/github-actions-conformance.yml`.
It can be moved to `.github/workflows/conformance.yml` once a maintainer token
with GitHub's `workflow` scope is used; the current repository-creation token
cannot publish workflow files.

## Canonical identifiers

Released objects use identifiers below:

```text
https://biosimulant.com/standards/model-compatibility/v0.1
https://biosimulant.com/standards/model-compatibility/profiles/{domain}/{name}/v0.1
```

Published references are immutable and must be paired with their SHA-256
digest. Mutable aliases must not appear in compatibility locks or resolution
plans.

## Security model

Validators resolve references only from the installed bundle. They never fetch
arbitrary remote `$ref` or profile URLs. Declarative rules use an allowlisted
operator vocabulary and never execute code.

## License

Apache-2.0. See [LICENSE](LICENSE).
