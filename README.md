# Biosimulant Model Compatibility Standard

A way for simulation models to describe what their inputs and outputs mean, so
tools can check whether two models can be connected before you run them.

A model's `model.yaml` already lists its ports (name, data type, shape). This
standard lets a port also say what the data *is*: the biological concept, units,
identifiers, species, file format and so on. With that information, a tool can
tell you whether an output from one model can feed an input of another, whether
a conversion is needed, or whether there isn't enough information to decide.

It's optional. Models without a `compatibility` block in `model.yaml` keep
working exactly as before (`schema_version: "2.0"` doesn't change).

This repository holds the specification files and reference implementations in
Python and TypeScript.

## Status

`0.1.0-alpha.4` is an engineering release candidate. The schemas and validators
are conformance-tested, but the catalogue is not GA until its scientific review
gate is complete.

All 650 profiles can be checked by machine, but none has finished scientific
review yet: 591 are `candidate` and 59 are `draft`. See
[PROFILE_REVIEW.md](PROFILE_REVIEW.md).

Compatibility checks whether two model interfaces fit together. It doesn't show
that a model is scientifically valid or clinically safe.

## Key ideas

- **Port contract**: the `contract` block on a port in `model.yaml`. It describes
  the port's data in groups of fields such as `semantic` (what it is),
  `measurement` (quantity, unit, scale), `identifiers` and `biological_context`.
- **Profile**: a reusable set of rules for one kind of data, for example
  `transcriptome/gene-expression-counts`. A profile lists which contract fields
  are required and how to compare them. There are 650 profiles across 26 domains.
- **Comparison report**: the result of comparing a source (output) port with a
  target (input) port. Its `status` is one of:

  | Status | Meaning |
  |---|---|
  | `EXACT` | The contracts are identical. |
  | `DIRECT_COMPATIBLE` | The source already meets the target's requirements. |
  | `LOSSLESS_CONVERSION_AVAILABLE` | A conversion that loses nothing is available, such as nM to µM. |
  | `LOSSY_CONVERSION_REQUIRES_APPROVAL` | A conversion exists but loses information, so someone has to approve it. |
  | `INFERENCE_MODEL_REQUIRED` | Getting from source to target needs a model to infer data. |
  | `CONDITIONAL` | Compatible only if a precondition holds. |
  | `INCOMPATIBLE` | A required value doesn't match. |
  | `UNKNOWN` | There isn't enough information to decide. |

  Each report also has a `policy_decision` (`ALLOW`, `APPROVAL_REQUIRED` or
  `BLOCK`) and a list of findings. Each finding has a `reason_code` from
  [`spec/v0.1/rules/reason-codes.json`](spec/v0.1/rules/reason-codes.json).
- **Resolution plan**: when two ports don't match directly, a chain of reviewed
  adapters (for example a unit conversion) or inference models that connects them.
- **Lock**: `compatibility.lock.json`, which records the exact profiles and
  contracts a model uses, with their sha256 digests.

## Install

The packages aren't on PyPI or npm yet. Install from a tagged release on GitHub:

```bash
pip install "biosimulant-model-compatibility-standard @ git+https://github.com/Biosimulant/model-compatibility-standard@v0.1.0-alpha.4"
```

```bash
npm install github:Biosimulant/model-compatibility-standard#v0.1.0-alpha.4
```

The npm install builds the package, which runs a small Python 3 script. Python 3
needs to be on your `PATH`; it only uses the standard library.

## Use it

Python:

```python
import yaml
from biosimulant_model_compatibility_standard import compare_contracts, validate_manifest

manifest = yaml.safe_load(open("model.yaml"))
for finding in validate_manifest(manifest):
    print(finding.reason_code, finding.path, finding.message)

report = compare_contracts({"measurement": {"unit": "nM"}}, {"measurement": {"unit": "uM"}})
print(report["status"])  # LOSSLESS_CONVERSION_AVAILABLE
```

TypeScript:

```ts
import { readFileSync } from "node:fs";
import { compareContracts, parseYaml, validateManifest } from "@biosimulant/model-compatibility-standard";

const findings = validateManifest(parseYaml(readFileSync("model.yaml", "utf8")));
const report = compareContracts({ measurement: { unit: "nM" } }, { measurement: { unit: "uM" } });
console.log(report.status); // LOSSLESS_CONVERSION_AVAILABLE
```

What each package provides:

| Task | Python | TypeScript |
|---|---|---|
| Validate a `model.yaml` | `validate_manifest` | `validateManifest` |
| Validate a contract against profiles | `validate_contract` | `validateContract` |
| Validate any object against a bundled schema | `validate_object` | `validateObject` |
| Compare two contracts | `compare_contracts` | `compareContracts` |
| Canonical JSON and sha256 digest | `canonical_bytes`, `digest` | `canonicalJson`, `digest` |
| Sort set-like fields before hashing | `normalize_contract`, `normalize_manifest` | `normalizeContract`, `normalizeManifest` |
| Plan a conversion path | `resolve_contracts`, `ResolutionLimits` | `resolveContracts`, `ResolutionLimits` |
| Build `compatibility.lock.json` | `build_compatibility_lock` | `buildCompatibilityLock` |
| Verify the installed bundle | `Bundle.verify_integrity` | `Bundle.verifyIntegrity` |

The [Biosimulant docs](https://docs.biosimulant.com/standards/model-compatibility)
show a full `model.yaml` example and the profile catalogue.

For agent integrations, [MCP and Agent Skill Integration](INTEGRATIONS.md)
defines the Biosimulant Agent Gateway tools, OAuth scopes, approval boundary,
and strict managed-run sequence. MCP is an authenticated product interface;
skills are optional guidance and do not change permissions or compatibility
decisions.

## Remaining GA gate

Both implementations now support the complete operator vocabulary. Ontology
and identifier-mapping operators fail closed with `UNKNOWN` unless the caller
supplies the exact digest-pinned snapshot named by the rule. They also enforce
the same document limits, accepted-profile refinement rules, normalization,
locks, resolution order and bundle integrity checks.

The remaining release blocker is scientific rather than a missing validator
feature: every public profile still needs authoritative sources and independent
review. See [PROFILE_REVIEW.md](PROFILE_REVIEW.md).

## Repository layout

- `source/catalogue.review.json`: the input catalogue of profiles, contract
  fields and packs.
- `scripts/build_standard.py`: generates everything in `spec/v0.1/` from the
  catalogue.
- `spec/v0.1/`: the generated specification: JSON Schemas, profiles, rules,
  fixtures, examples and `bundle.manifest.json`, which lists every file with its
  sha256. **Don't edit these files by hand.** See [CONTRIBUTING.md](CONTRIBUTING.md).
- `python/`: the Python package and its tests.
- `typescript/`: the TypeScript package and its tests.
- `ci/github-actions-conformance.yml`: the CI workflow.

## Build and test

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/python scripts/build_standard.py --check
.venv/bin/pytest

npm install
npm test
```

`--check` rebuilds the spec in a temporary folder and fails if `spec/v0.1/`
doesn't match. `npm test` runs the same check, compiles the TypeScript and runs
its tests.

The CI workflow lives in `ci/` for now. Copy it to `.github/workflows/` to turn
it on; pushing workflow files needs a GitHub token with the `workflow` scope.

## Identifiers

Every published object has a stable URL:

```text
https://biosimulant.com/standards/model-compatibility/v0.1
https://biosimulant.com/standards/model-compatibility/profiles/{domain}/{name}/v0.1
```

Always pin a profile with its sha256 when you reference it. Locks and resolution
plans never use a moving reference like "latest".

## Security

The validators only read files from the installed package. They never download
a `$ref` or profile URL. Comparison rules are data, so a profile can't run code.
To report a security problem, see [SECURITY.md](SECURITY.md).

## License

Apache-2.0. See
[LICENSE](https://github.com/Biosimulant/model-compatibility-standard/blob/main/LICENSE).
