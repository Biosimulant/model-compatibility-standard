# Reading the generated specification

`spec/v0.1/` is the machine-readable release bundle. It is generated from the
files under `source/`; do not edit it by hand.

Most people do not need to read the whole bundle. Start with the file that
matches the job:

| What you are doing | Start here |
|---|---|
| See which profiles exist | [`catalogue/catalogue.json`](v0.1/catalogue/catalogue.json) |
| Read one profile's actual rules | [`profiles/`](v0.1/profiles/) |
| Review a profile as a scientist | [`review-packets/`](v0.1/review-packets/) and [the review guide](../PROFILE_REVIEW.md) |
| Add or change a profile | Edit [`source/catalogue.review.json`](../source/catalogue.review.json), then follow [the proposal guide](../PROPOSING_A_PROFILE.md) |
| Add compatibility support to a model | Read [the root README](../README.md#what-goes-in-modelyaml) and [`examples/compatible-model.yaml`](v0.1/examples/compatible-model.yaml) |
| Implement a validator | Read [`schemas/`](v0.1/schemas/), [`rules/`](v0.1/rules/) and the conformance fixtures |
| Check an exact downloaded bundle | Use [`bundle.manifest.json`](v0.1/bundle.manifest.json) |

## What each part is for

| Path | Purpose | Intended reader |
|---|---|---|
| `bundle.manifest.json` | Lists every released file, its size and SHA-256 digest. | Package and release tooling |
| `catalogue/catalogue.json` | Main index: profiles, contract fields and field packs in one file. | Applications and catalogue browsers |
| `catalogue/items.json` | The contract-field list on its own. It backs the smaller public items endpoint. | API and documentation clients |
| `catalogue/item-packs.json` | The field-pack list on its own. It backs the smaller public packs endpoint. | API and documentation clients |
| `catalogue/terms.json` | Stable scientific concept identifiers used by profiles. | Validators and ontology-aware clients |
| `catalogue/internal-validation.json` | Technical readiness only: whether each draft is schema-valid and fixture-backed. It is not scientific approval. | Maintainers and reviewers |
| `profiles/<domain>/<name>/v0.1.json` | One versioned profile: required fields and comparison rules. | Validators and advanced users |
| `schemas/` | One JSON Schema per public document type. | Implementers |
| `rules/` | Shared statuses, operators, reason codes, normalization, quantity kinds and units. | Validators |
| `review-packets/` | The complete generated mapping a scientist must review for each profile. | Scientific reviewers |
| `fixtures/profiles/` | Generated pass, fail, incompatible and unknown cases for every profile. | Tests and reviewers checking examples |
| `fixtures/golden/` | Small cross-language cases that Python and TypeScript must handle identically. | Implementers |
| `examples/` | A model with compatibility metadata and a legacy model without it. | Model authors and tests |

## Why it is not one file

The bundle has separate files because they have different consumers and change
at different rates:

- each schema and profile needs its own stable URL and digest;
- a profile version must remain immutable when another profile changes;
- API clients can fetch the smaller items or field-packs list without loading
  every profile and rule; and
- reviewer packets and fixtures are evidence about the standard, not runtime
  declarations.

`catalogue/catalogue.json` is the consolidated entry point when a client wants
one index. The smaller catalogue files are retained because the public API and
documentation site serve them directly.

To rebuild the bundle after an authorised source change, run:

```bash
python3 scripts/build_standard.py
python3 scripts/build_standard.py --check
```

If a generated file looks wrong, fix the source or generator and rebuild it.
