# Generated specification

`spec/v0.1/` is generated JSON consumed by software and reviewers. Its source
is the YAML under `source/`. Do not edit generated files directly.

## Start with the file for your job

| Goal | File or folder |
|---|---|
| See available profiles | [`v0.1/catalogue/catalogue.json`](v0.1/catalogue/catalogue.json) |
| Read one runtime profile | [`v0.1/profiles/`](v0.1/profiles/) |
| Review the complete mapping for one profile | [`v0.1/review-packets/`](v0.1/review-packets/) |
| See the shared contract fields | [`v0.1/catalogue/fields.json`](v0.1/catalogue/fields.json) |
| Implement a validator | [`v0.1/schemas/`](v0.1/schemas/) and [`v0.1/rules/`](v0.1/rules/) |
| Check examples | [`v0.1/fixtures/`](v0.1/fixtures/) |
| Verify a downloaded bundle | [`v0.1/bundle.manifest.json`](v0.1/bundle.manifest.json) |

## What the folders mean

| Path | Purpose |
|---|---|
| `catalogue/catalogue.json` | The main index of fields and profiles |
| `catalogue/fields.json` | The shared field vocabulary as a small standalone file |
| `catalogue/terms.json` | Stable scientific concept identifiers used by profiles |
| `catalogue/internal-validation.json` | Technical readiness; never scientific approval |
| `profiles/<domain>/<name>/v0.1.json` | One versioned runtime profile |
| `review-packets/` | Complete field mappings and examples for scientific review |
| `fixtures/profiles/` | Generated validation and comparison cases per profile |
| `fixtures/scientific.json` | Profile-authored scientific guards run in both languages |
| `fixtures/golden/` | Small cross-language conformance cases |
| `schemas/` | JSON Schemas for public documents |
| `rules/` | Shared statuses, operators, reason codes, units and normalisation |
| `examples/` | Example manifests with and without compatibility metadata |
| `bundle.manifest.json` | File list, sizes, digests and bundle digest |

Files are split because profiles and schemas need stable URLs and individual
digests. `catalogue/catalogue.json` is still the single consolidated entry
point for clients that want one index.

## Change a profile

Edit `source/profiles/<domain>/<name>.yaml`. Edit `source/fields.yaml` only if
the profile needs a genuinely new shared field. Then run:

```bash
.venv/bin/python scripts/build_standard.py
.venv/bin/python scripts/build_standard.py --check
```

See [the profile proposal guide](../PROPOSING_A_PROFILE.md) for the full
workflow.
