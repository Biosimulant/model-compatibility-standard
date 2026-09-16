# Contributing

Keep changes small and tied to a real model connection or a specific defect.
Do not generate speculative catalogues.

## Add or change a profile

Edit one source file:

```text
source/profiles/<domain>/<profile-name>.yaml
```

It contains the profile's meaning, intended use, limitations, sources, complete
field decisions and scientific examples. Reuse fields from
`source/fields.yaml`; add a shared field only when the required concept is
genuinely missing.

Then regenerate the bundle:

```bash
.venv/bin/python scripts/build_standard.py
.venv/bin/python scripts/build_standard.py --check
```

Commit the source and generated files together. Do not edit `spec/v0.1/` by
hand. Published profile versions are immutable; a substantive change creates a
new version.

See [Proposing a profile](PROPOSING_A_PROFILE.md) for the email and pull-request
workflow.

## Change comparison behaviour

A new operator must be implemented and tested in both Python and TypeScript.
Both implementations must give the same result for the generated fixtures. Put
scientific assumptions in the profile, with sources and examples, rather than
hiding them in implementation code.

## Before opening a pull request

```bash
.venv/bin/python scripts/build_standard.py --check
.venv/bin/pytest
PATH="$PWD/.venv/bin:$PATH" npm test
```

Explain the model connection or defect, evidence, generated files and any
question that still needs resolution. The pull request is the review record;
merge into `main` accepts the change.

Supported automation belongs in `scripts/`. Put disposable migration or
inspection code in the ignored `.scratch/` directory and delete it when done.
