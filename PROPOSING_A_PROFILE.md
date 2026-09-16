# Proposing a compatibility profile

A profile is an agreement about one kind of data passed from a model output to
a model input. Propose one when two real models need to exchange data and no
current profile describes that connection.

You can email the proposal to Biosimulant or open a pull request. Both routes
need the same information:

- the producing model and output port;
- the receiving model and input port;
- a small real, synthetic or redacted example from each side;
- the intended use and limits;
- the scientific facts needed to interpret and compare the data;
- the expected result when those facts match, conflict or are missing; and
- authoritative sources for the decisions.

Do not send credentials, patient data or confidential datasets.

## Send a proposal by email

Email `demi@biosimulant.com` with the subject:

```text
Model compatibility profile proposal: <profile name>
```

Attach a completed [proposal template](PROFILE_PROPOSAL_TEMPLATE.md), or a Word
or PDF containing the same information. Include small source and target
examples and links or DOIs for the supporting sources. If YAML or JSON is
unfamiliar, use the mapping table in the template; the Biosimulant team can
translate it into the repository format.

## Open a pull request

### 1. Create a branch

```bash
git clone https://github.com/<your-account>/model-compatibility-standard.git
cd model-compatibility-standard
git remote add upstream https://github.com/Biosimulant/model-compatibility-standard.git
git fetch upstream
git switch -c profile/<domain>-<profile-name> upstream/main

python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
npm install
```

### 2. Add one profile file

Create:

```text
source/profiles/<domain>/<profile-name>.yaml
```

The path becomes the profile ID. For example,
`source/profiles/proteome/protein-sequence.yaml` becomes
`proteome/protein-sequence@0.1`.

Copy the closest existing profile. A small source file looks like this:

```yaml
schema_version: "0.1"
label: Example Measurement
domain_label: Example domain
description: >
  A precise description of the data represented by this profile.
status: active
representations: [scalar, record]
intended_use: >
  Connecting an output that produces this measurement to an input that consumes
  the same declared measurement.
limitations:
  - It does not establish that the value or producing model is scientifically valid.
sources:
  - title: Authoritative measurement specification
    url: https://example.org/specification

fields:
  semantic.concept: required
  representation.kind: required
  measurement.quantity: required
  measurement.unit: required
  biological_context.species: recommended
  origin.method: recommended

examples:
  - id: BMCS-EXAMPLE-001
    title: Identical declarations are an exact match
    check: compare
    expect: {status: EXACT}
    why: No conversion or inference is needed.
    conditions: Both ports provide the same complete declarations.
    decision: Example measurement profile
    report_finding: Positive baseline
```

The file must include every relevant field, not only required fields. Give each
field one decision:

- `required`;
- `conditional`, with a `when` condition;
- `recommended`; or
- `excluded`.

If a scientific question is unresolved, explain it in the pull request and
resolve it before merge. Do not add an `under-review` state to the published
profile.

### 3. Add a shared field only when necessary

Check `source/fields.yaml` first. Reuse a field when it has the same meaning. If
the profile genuinely needs a new scientific fact, add one field with an
explicit value schema and comparison rule:

```yaml
- path: measurement.sampling_site
  family: measurement
  schema: {type: string, minLength: 1}
  comparison: equal
```

Change `source/quantity-kinds.yaml` only when the profile introduces or changes
a measurement kind. There is no central profile list or field pack to edit.

### 4. Add worked outcomes

Profile examples should cover the meaningful outcomes:

- `EXACT` or `DIRECT_COMPATIBLE` for a direct match;
- `LOSSLESS_CONVERSION_AVAILABLE` for a named lossless conversion;
- an approval-required result for a lossy transformation or inference;
- `INCOMPATIBLE` for a known contradiction; and
- `UNKNOWN` when necessary information is missing.

Use `source_patch`, `target_patch`, `source_remove` or `target_remove` to alter
the generated valid contract. The current profiles provide working examples.

### 5. Generate and test

```bash
.venv/bin/python scripts/build_standard.py
.venv/bin/python scripts/build_standard.py --check
.venv/bin/pytest -p no:cacheprovider
PATH="$PWD/.venv/bin:$PATH" npm test
```

The build generates the runtime profile, catalogue entry and test fixtures
under `spec/v0.1/`. If generated output is wrong, change the YAML or generator
and rebuild. Never edit the generated JSON directly.

### 6. Open the pull request

Use a title such as:

```text
Profile: add <profile name> for <source model> to <target model>
```

Describe the connection, intended use, limitations, full field mapping,
examples, sources, unresolved questions and test results. Keep the pull request
to one profile unless a small group shares the same scientific boundary.

The pull request is the review record. It can request scientific or technical
input appropriate to the change. Merge into `main` is the acceptance decision;
there is no separate sign-off file.

## Files changed by a typical profile

Usually:

1. `source/profiles/<domain>/<profile-name>.yaml`;
2. generated files under `spec/v0.1/`; and
3. generated browser data under `typescript/dist/`.

Sometimes:

4. `source/fields.yaml`, for a genuinely new shared field; or
5. `source/quantity-kinds.yaml`, for a new or changed measurement kind.

## Pull request checklist

- [ ] The profile supports a real output-to-input connection.
- [ ] Intended use and limitations are clear.
- [ ] Sources support the scientific decisions.
- [ ] Every relevant field is required, conditional, recommended or excluded.
- [ ] Direct, incompatible and unknown outcomes are demonstrated where relevant.
- [ ] Every permitted conversion or inference is named and visible.
- [ ] Generated files were rebuilt rather than edited.
- [ ] Python and TypeScript tests pass.
