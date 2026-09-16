# Contributing

Small, reviewable changes are preferred. Please do not generate a catalogue of
possible profiles or add a profile without a real model connection behind it.

## Change an existing profile

Released objects do not change in place. A scientific or technical change to a
released profile creates a new version.

Profiles, contract fields and packs are maintained in
`source/catalogue.review.json`. Files under `spec/v0.1/` are generated. After a
source change, regenerate the bundle and commit both the source and generated
files:

```bash
python3 scripts/build_standard.py
python3 scripts/build_standard.py --check
```

If you are adding a profile, follow [Proposing a profile](PROPOSING_A_PROFILE.md)
and complete the [proposal template](PROFILE_PROPOSAL_TEMPLATE.md). The guide
covers both email submission and the exact branch, source, generated-file,
example and pull-request steps. The process starts with a real output-to-input
mapping and includes independent scientific review.

## Change comparison behaviour

A new comparison operator must be implemented and tested in both Python and
TypeScript. The two implementations must produce the same result on the shared
fixtures in `spec/v0.1/fixtures/golden/`.

Do not add scientific assumptions to implementation code to make a test pass.
Those decisions belong in a reviewed profile or capability.

## Before opening a pull request

Run:

```bash
.venv/bin/python scripts/build_standard.py --check
.venv/bin/pytest
npm test
```

Explain the model connection or defect the change addresses, list the evidence
used, and call out any question that still needs scientific judgement.

Supported repository automation belongs in `scripts/`. Put disposable local
work in the ignored `.scratch/` directory rather than committing it.
