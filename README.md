# Biosimulant Model Compatibility Standard

This standard answers one question: can the output of one model be used as the
input of another?

Matching file types or array shapes is not enough. Two ports can still disagree
about scientific meaning, units, species, identifiers, normalisation,
coordinates or provenance. A port contract states those facts. A profile says
which facts matter for one kind of data and how to compare them.

A comparison can report a direct match, an available lossless conversion, a
transformation or inference that needs approval, an incompatibility, or
`UNKNOWN` when required information is missing. It does not approve a model,
dataset, scientific result, clinical use or regulatory claim.

## Current scope

The v0 catalogue is intentionally small:

- Protein Sequence
- Protein Structure
- Canonical SMILES

The earlier 650-profile prototype was removed from the active catalogue and
remains available in Git history. New profiles are added only when they support
a real model-to-model connection.

## The files people edit

Most profile changes touch one human-written file:

```text
source/profiles/<domain>/<profile-name>.yaml
```

That file contains the profile's definition, intended use, limitations,
sources, complete field mapping and worked examples. Edit
`source/fields.yaml` only when a necessary shared field does not already exist.
Edit `source/quantity-kinds.yaml` only for a new or changed measurement kind.

Everything under `spec/v0.1/` is generated JSON for software. Do not edit it by
hand.

| Need | Start here |
|---|---|
| Read or change a profile | [`source/profiles/`](source/profiles/) |
| Submit a profile by email or pull request | [Proposing a profile](PROPOSING_A_PROFILE.md) |
| Understand the generated bundle | [`spec/README.md`](spec/README.md) |
| Change code | [Contributing](CONTRIBUTING.md) |

## Field decisions

Every field considered by a profile has one decision:

- `required`: the comparison cannot be decided without it;
- `conditional`: required only under a stated condition;
- `recommended`: useful context, but not a compatibility gate; or
- `excluded`: deliberately outside this profile.

This complete mapping stays in the profile. There is no separate review packet
or approval record to keep in sync.

## How a profile becomes active

The pull request is the review record. Discussion, requested changes, evidence
and approvals remain visible there. A profile merged into `main` is accepted
for the stated use and is published with `status: active`. A profile that
should remain available for old locks but not new work is `deprecated`.

Extra scientific or technical review can be requested in the pull request when
the change warrants it. The standard does not require named reviewer fields,
separate sign-off files or a permanent domain owner.

## Use a profile in `model.yaml`

Compatibility metadata is optional. A model imports a profile by its versioned
reference and digest, then adds a contract to the relevant port.

```yaml
schema_version: "2.0"

compatibility:
  standard: https://biosimulant.com/standards/model-compatibility/v0.1
  profiles:
    - ref: https://biosimulant.com/standards/model-compatibility/profiles/proteome/protein-sequence/v0.1
      sha256: <digest from the installed catalogue>

io:
  inputs:
    - name: protein_sequence
      signal_type: record
      contract:
        profile_refs:
          - https://biosimulant.com/standards/model-compatibility/profiles/proteome/protein-sequence/v0.1
        semantic:
          concept: https://biosimulant.com/standards/model-compatibility/terms/proteome/protein-sequence
        representation:
          kind: record
          alphabet: IUPAC-amino-acid
          encoding: single-letter
        identifiers:
          namespace: UniProtKB
          namespace_version: "2026_03"
        biological_context:
          species: NCBITaxon:9606
```

If information required by the target is missing, the result is `UNKNOWN`; the
comparison does not guess.

## Install from a pinned commit

The packages are not yet published to PyPI or npm. During v0, install an exact
commit:

```bash
pip install "biosimulant-model-compatibility-standard @ git+https://github.com/Biosimulant/model-compatibility-standard@<commit>"
npm install "https://github.com/Biosimulant/model-compatibility-standard/archive/<commit>.tar.gz"
```

Python:

```python
from biosimulant_model_compatibility_standard import compare_contracts

report = compare_contracts(source_contract, target_contract)
print(report["status"])
```

TypeScript:

```ts
import { compareContracts } from "@biosimulant/model-compatibility-standard";

const report = compareContracts(sourceContract, targetContract);
console.log(report.status);
```

## Work on the repository

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
npm install

.venv/bin/python scripts/build_standard.py
.venv/bin/python scripts/build_standard.py --check
.venv/bin/pytest
PATH="$PWD/.venv/bin:$PATH" npm test
```

| Path | Purpose | Normally edit? |
|---|---|---|
| `source/profiles/<domain>/<name>.yaml` | Complete source for one profile | Yes |
| `source/fields.yaml` | Shared contract-field definitions | Only for a new field |
| `source/quantity-kinds.yaml` | Shared measurement meanings and units | Only when needed |
| `source/vendor/ucum/` | Pinned UCUM source and generated unit table | Only for a UCUM update |
| `spec/v0.1/` | Generated schemas, profiles, rules and fixtures | No |
| `python/`, `typescript/src/` | Reference implementations | For code changes |
| `typescript/dist/` | Generated JavaScript package | No |
| `scripts/` | Supported build and verification scripts | For build changes |

Put disposable work in the ignored `.scratch/` directory and remove it when
finished. Published versions are immutable and identified by SHA-256.

Apache-2.0 licensed. See [LICENSE](LICENSE).
