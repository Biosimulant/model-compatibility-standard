# Generated specification

`spec/v0.1/` is generated from the YAML under `source/`. Do not edit generated
files directly.

| Path | Purpose |
|---|---|
| `catalogue/catalogue.json` | Index of available profiles and shared fields |
| `catalogue/fields.json` | Shared field vocabulary |
| `catalogue/terms.json` | Stable scientific concept identifiers |
| `profiles/<domain>/<name>/v0.1.json` | Complete runtime profile, including sources, field decisions and examples |
| `fixtures/profiles/` | Generated validation and comparison cases per profile |
| `fixtures/scientific.json` | Profile-authored examples run in both languages |
| `fixtures/golden/` | Cross-language conformance cases |
| `schemas/` | JSON Schemas for public documents |
| `rules/` | Statuses, operators, reason codes, units and normalisation |
| `examples/` | Example model manifests |
| `bundle.manifest.json` | File list, sizes, digests and bundle digest |

Profiles and schemas use separate files because consumers need stable URLs and
individual digests. `catalogue/catalogue.json` is the single entry point for
discovering them.

To change a profile, edit `source/profiles/<domain>/<name>.yaml`, then run:

```bash
.venv/bin/python scripts/build_standard.py
.venv/bin/python scripts/build_standard.py --check
```

See [Proposing a profile](../PROPOSING_A_PROFILE.md) for the full workflow.
