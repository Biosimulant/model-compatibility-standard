# Contributing

Keep changes small and tied to a real model connection or a specific defect.
Do not generate speculative catalogues.

## Change or add a profile

The human-authored profile is one YAML file:

```text
source/profiles/<domain>/<profile-name>.yaml
```

It contains the profile’s meaning, intended use, limitations, field decisions
and scientific examples. Reuse fields from `source/fields.yaml`; add a shared
field only when the required concept is genuinely missing.

Then regenerate the JSON bundle:

```bash
.venv/bin/python scripts/build_standard.py
.venv/bin/python scripts/build_standard.py --check
```

Commit the YAML and generated files together. Do not edit `spec/v0.1/` by hand.
Released profile versions are immutable; a substantive change creates a new
version.

For the full email and pull-request workflow, see
[Proposing a profile](PROPOSING_A_PROFILE.md) and the
[proposal template](PROFILE_PROPOSAL_TEMPLATE.md).

## Change comparison behaviour

A new operator must be implemented and tested in both Python and TypeScript.
Both implementations must give the same results for the generated fixtures.
Do not bury a scientific assumption in implementation code; put it in the
profile and its review evidence.

## Before opening a pull request

```bash
.venv/bin/python scripts/build_standard.py --check
.venv/bin/pytest
PATH="$PWD/.venv/bin:$PATH" npm test
```

Explain the model connection or defect, the evidence used, generated files
changed and any unresolved scientific question.

Supported repository automation belongs in `scripts/`. Disposable migration,
inspection and one-off scripts belong in the ignored `.scratch/` directory.
