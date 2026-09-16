# Biosimulant Model Compatibility Standard

This standard answers a practical question: can the output of one model be
used safely as the input of another?

A matching file type or array shape is not enough. Two ports may still disagree
about what the value means, its units, species, identifier system,
normalisation, coordinate system or provenance. The standard gives each port a
small contract and uses a compatibility profile to say which parts of that
contract matter for a particular kind of data.

A comparison can report:

- a direct match;
- a named conversion that does not lose information;
- a transformation or inference that needs approval;
- an incompatibility; or
- `UNKNOWN` when information is missing.

It does not approve a model, dataset, scientific result, clinical use or
regulatory claim.

## Current scope

This is a deliberately small v0 incubator. It has three draft profiles:

- Protein Sequence
- Protein Structure
- Canonical SMILES

None has completed independent scientific review. The profiles are useful for
testing the format and review process, but are not approved scientific
standards.

The earlier 650-profile prototype has been removed from the active catalogue.
It remains in Git history. New profiles are added only for real model-to-model
connections, with examples and reviewers.

## The simple mental model

There are three kinds of human-maintained YAML:

1. One file per profile under `source/profiles/`. This is where almost every
   profile proposal starts and ends. It contains the meaning, intended use,
   limitations, every field the scientist should consider, and worked examples.
2. `source/fields.yaml`. This is the shared vocabulary of contract fields. Edit
   it only if the proposed profile genuinely needs a field that does not exist.
3. One completed review record under `source/reviews/` after independent review.

Everything under `spec/v0.1/` is generated JSON for software and review
packets. Do not edit it by hand. There are no field packs and no second profile
catalogue to keep in sync.

## Where to start

| Goal | Read |
|---|---|
| See the three active profiles | [`source/profiles/`](source/profiles/) |
| Propose a profile by email or pull request | [Proposing a profile](PROPOSING_A_PROFILE.md) |
| Review a profile scientifically | [Profile review](PROFILE_REVIEW.md) |
| Understand generated files | [`spec/README.md`](spec/README.md) |
| Change implementation code | [Contributing](CONTRIBUTING.md) |

## A profile in plain language

A profile is a named agreement for one kind of model data. For example, the
Protein Sequence profile says that a sequence connection must declare its
scientific concept, representation, alphabet, encoding, identifier namespace
and version, and species.

The profile file also shows fields still open for review. A scientist sees the
whole proposed mapping rather than only the required fields. Each field is
labelled as one of:

- `required` — the comparison cannot be decided without it;
- `conditional` — required only in a stated situation;
- `recommended` — useful but not a compatibility gate;
- `excluded` — deliberately outside this profile; or
- `under-review` — the draft has not made the scientific decision yet.

## What goes in `model.yaml`

Compatibility metadata is optional. Existing models without it continue to
work. A model imports a profile by its versioned reference and digest, then
adds a contract to the relevant port.

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

If information required by the target is missing, the comparison returns
`UNKNOWN`; it does not guess.

## Use the libraries

The Python and TypeScript packages validate contracts, compare ports and build
resolution plans and lock files. They are not published to PyPI or npm yet.
During the incubator phase, install a specific commit rather than a moving
branch.

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

The PATH prefix makes the npm build use the virtual environment, including its
YAML dependency.

### Repository map

| Path | Purpose | Normally edit? |
|---|---|---|
| `source/profiles/<domain>/<name>.yaml` | One complete human-authored profile | Yes, for that profile |
| `source/fields.yaml` | Shared contract-field definitions | Only for a genuinely new field |
| `source/quantity-kinds.yaml` | Shared measurement meanings and units | Only for measurement-rule changes |
| `source/reviews/` | Independent scientific review records | During review |
| `source/vendor/ucum/` | Pinned UCUM source and generated unit table | Only for a deliberate UCUM update |
| `spec/v0.1/` | Generated JSON bundle, fixtures and review packets | No; rebuild it |
| `python/` and `typescript/src/` | Reference implementations | For implementation changes |
| `typescript/dist/` | Generated JavaScript package files | No; `npm run build` recreates them |
| `scripts/` | Supported build and verification scripts | Only for build-system changes |

Put disposable investigations in `.scratch/`, which Git ignores. See
[`scripts/README.md`](scripts/README.md) before adding a script.

Published profile versions are immutable and identified by SHA-256. Validators
use the installed bundle; they do not fetch remote schemas or execute profile
code.

Apache-2.0 licensed. See [LICENSE](LICENSE).
