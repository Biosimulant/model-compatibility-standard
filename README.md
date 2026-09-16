# Biosimulant Model Compatibility Standard

The standard helps decide whether the output of one model can be used as the
input of another.

Matching file shapes and data types is not enough. Two ports can both carry a
string, array or file while disagreeing about the scientific meaning, species,
identifier system, units, normalisation, coordinate system or provenance. A
port contract records those details. A profile says which details matter for a
particular kind of data and how they should be compared.

The result is one of four practical answers:

- the ports can connect directly;
- a stated conversion or inference step is needed;
- the ports are incompatible; or
- there is not enough information to decide.

This is an interface check. It does not approve a model, dataset, result,
clinical use or regulatory claim.

## Current scope

Version `0.0.1` is a deliberately small incubator. It contains three draft
profiles:

- Protein Sequence
- Protein Structure
- Canonical SMILES

None has completed independent scientific review. They are usable for testing
the format and review process, but should not be presented as approved
scientific standards.

The former 650-profile catalogue was an exploratory prototype and has been
removed from the active standard. It remains in Git history. New profiles will
be added only when there is a real model-to-model mapping to support and people
available to review it.

See [Proposing a profile](PROPOSING_A_PROFILE.md) if the data exchanged by your
models is not covered by the current catalogue.

## What goes in `model.yaml`

Compatibility is optional. A model can import one or more profiles and add a
contract to the ports it wants to describe. Existing models without a
`compatibility` block continue to work.

```yaml
schema_version: "2.0"

compatibility:
  standard: https://biosimulant.com/standards/model-compatibility/v0.1
  profiles:
    - ref: https://biosimulant.com/standards/model-compatibility/profiles/proteome/protein-sequence/v0.1
      sha256: sha256:5000e512dc105f96c4ad4da65dc1305011522682f555b88a35213e8d20a5a179

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
          kind: scalar
          alphabet: IUPAC-amino-acid
          encoding: single-letter
        identifiers:
          namespace: UniProtKB
          namespace_version: "2026_03"
        biological_context:
          species: NCBITaxon:9606
```

The profile fixes the scientific concept and requires enough information to
interpret and compare the sequence. If required information is missing, the
comparison returns `UNKNOWN`; it does not guess.

## Use the libraries

The Python and TypeScript packages validate manifests and contracts, compare
ports, build resolution plans and create compatibility lock files. Packages are
not published to PyPI or npm yet. Until the first v0 tag is cut, install the
exact incubator commit:

```bash
pip install "biosimulant-model-compatibility-standard @ git+https://github.com/Biosimulant/model-compatibility-standard@7ed53a619fee78641998226c1ce7c8479259ff8a"
npm install "https://github.com/Biosimulant/model-compatibility-standard/archive/7ed53a619fee78641998226c1ce7c8479259ff8a.tar.gz"
```

The npm build requires Python 3 on `PATH`.

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

Browser and desktop applications can use the `/browser` entry point for public,
local validation. Resolution plans, approvals and private data stay on the
authenticated Biosimulant service.

## Work on the standard

The source of truth is `source/catalogue.review.json`. Files under `spec/v0.1/`
are generated and must not be edited by hand.

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/python scripts/build_standard.py --check
.venv/bin/pytest

npm install
npm test
```

The repository is organised as follows:

- `source/` — profile source and independent review records
- `spec/v0.1/` — generated schemas, profiles, rules, fixtures and review packets
- `python/` and `typescript/` — reference implementations and tests
- `scientific-checks/` — shared cases for scientifically important outcomes
- `scripts/` — supported build and verification scripts

One-off scripts and local investigation files belong in `.scratch/`, which Git
ignores. See [scripts/README.md](scripts/README.md).

For changes, start with [CONTRIBUTING.md](CONTRIBUTING.md). A new profile has a
separate, evidence-led route in [PROPOSING_A_PROFILE.md](PROPOSING_A_PROFILE.md).
The scientific review gate is described in
[PROFILE_REVIEW.md](PROFILE_REVIEW.md).

## Stable references

Published profiles and bundles are versioned and identified by SHA-256. Lock
files and plans must use the versioned reference and digest, never a moving
`latest` reference.

The validators use only the installed bundle. They do not fetch remote schemas
or execute code from profile rules. Report security issues as described in
[SECURITY.md](SECURITY.md).

Apache-2.0 licensed. See [LICENSE](LICENSE).
