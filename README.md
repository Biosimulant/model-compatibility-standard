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

If your models exchange data that the catalogue does not cover, you can either
send the scientific mapping to Biosimulant or add the profile in a pull request.
The [profile proposal guide](PROPOSING_A_PROFILE.md) gives the email package,
branch commands, files to change, example requirements and review process. Start
with the reusable [proposal template](PROFILE_PROPOSAL_TEMPLATE.md).

## Where to start

You do not need to understand every repository file to use or review the
standard.

| If you want to… | Open |
|---|---|
| See the active profiles | [`spec/v0.1/catalogue/catalogue.json`](spec/v0.1/catalogue/catalogue.json) |
| Understand one profile scientifically | Its file under [`spec/v0.1/review-packets/`](spec/v0.1/review-packets/) and [the review guide](PROFILE_REVIEW.md) |
| Add a profile | [The profile proposal guide](PROPOSING_A_PROFILE.md) |
| Use a profile in `model.yaml` | [The example below](#what-goes-in-modelyaml) |
| Work on the implementation | [The contributing guide](CONTRIBUTING.md) |
| Understand the generated folders | [`spec/README.md`](spec/README.md) |

`v0.1` in the `spec/` path is the format version of the standard. The package
currently carrying that format is version `0.0.1`; those version numbers serve
different purposes.

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

### Repository map

| Path | What belongs there | Edit it? |
|---|---|---|
| `source/catalogue.review.json` | Profile definitions, contract fields and field packs | Yes, when adding or changing a profile |
| `source/reviews/` | Independent scientific and schema review records | Yes, through the review process |
| `source/quantity-kinds.json` | Reviewed meanings for quantities and their canonical units | Only when changing measurement rules |
| `source/vendor/ucum/` | The pinned UCUM source and the generated unit table used for reproducible builds | Only when deliberately updating UCUM |
| `spec/v0.1/` | Generated release files consumed by software and reviewers | No; rebuild it |
| `python/` and `typescript/src/` | The two reference implementations | Yes, for implementation changes |
| `typescript/dist/` | Generated npm entry points | No; `npm run build` recreates them |
| `scientific-checks/` | Small, shared cases that protect reviewed scientific decisions | Yes, after a scientific decision |
| `scripts/` | The four supported build and cross-language verification scripts | Only for build-system changes |
| `package.json` and `package-lock.json` | npm package metadata, commands and exact JavaScript dependency versions | Only when the JavaScript package or dependencies change |
| `pyproject.toml` | Python package metadata and dependencies | Only when the Python package or dependencies change |

The detailed map of every generated folder, including why the catalogue has
both a consolidated file and smaller public endpoint files, is in
[`spec/README.md`](spec/README.md).

One-off scripts and local investigation files belong in `.scratch/`, which Git
ignores. See [scripts/README.md](scripts/README.md).

For changes, start with [CONTRIBUTING.md](CONTRIBUTING.md). A new profile has a
separate, evidence-led route in [PROPOSING_A_PROFILE.md](PROPOSING_A_PROFILE.md):
prepare the complete output-to-input mapping, add it to
`source/catalogue.review.json`, rebuild the generated profile and fixtures, run
both implementations' tests, and open a pull request with the real or redacted
examples. If you do not want to edit the repository, complete
[PROFILE_PROPOSAL_TEMPLATE.md](PROFILE_PROPOSAL_TEMPLATE.md) and send the
package by email as described in the guide. The scientific review gate is
described in [PROFILE_REVIEW.md](PROFILE_REVIEW.md).

### Other repository documents

| Document | Use it for |
|---|---|
| [CONTRIBUTING.md](CONTRIBUTING.md) | Making implementation or profile changes |
| [GOVERNANCE.md](GOVERNANCE.md) | Versioning, review roles and profile status |
| [RELEASE.md](RELEASE.md) | Cutting and publishing a release |
| [SECURITY.md](SECURITY.md) | Reporting vulnerabilities and understanding validator limits |
| [CHANGELOG.md](CHANGELOG.md) | User-visible changes between releases |

## Stable references

Published profiles and bundles are versioned and identified by SHA-256. Lock
files and plans must use the versioned reference and digest, never a moving
`latest` reference.

The validators use only the installed bundle. They do not fetch remote schemas
or execute code from profile rules. Report security issues as described in
[SECURITY.md](SECURITY.md).

Apache-2.0 licensed. See [LICENSE](LICENSE).
