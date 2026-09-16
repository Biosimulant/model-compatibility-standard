# Proposing a compatibility profile

A profile is a shared agreement about one kind of data passed from a model
output to a model input. Propose one when two real models need to exchange data
and the current profiles do not describe that connection.

You can send the mapping to Biosimulant or open a pull request. Both routes need
the same scientific information.

## What to prepare

Start with one concrete connection:

- the producing model and output port;
- the receiving model and input port;
- a small real, synthetic or redacted example from each side;
- the intended workflow;
- every scientific fact needed to interpret and compare the data; and
- the expected result when facts match, conflict or are missing.

Use [the proposal template](PROFILE_PROPOSAL_TEMPLATE.md) to make the mapping
explicit. Do not send credentials, patient data or confidential datasets.

## Route A: send it by email

Email `demi@biosimulant.com` with the subject:

```text
Model compatibility profile proposal: <profile name>
```

Attach:

1. A completed `PROFILE_PROPOSAL_TEMPLATE.md`, or a Word/PDF copy with the same
   information.
2. A small source-port example in YAML or JSON.
3. A small target-port example in YAML or JSON.
4. Examples of a direct match, a known contradiction, missing information, and
   any conversion or inference the profile permits.
5. Links, DOIs or versioned references supporting the scientific decisions.

If YAML or JSON is unfamiliar, put the source and target declarations in the
template’s mapping table. The team can translate them into repository format.
Submission is not approval; independent scientific review still follows.

## Route B: open a pull request

### 1. Create a branch

```bash
git clone https://github.com/<your-account>/model-compatibility-standard.git
cd model-compatibility-standard
git remote add upstream https://github.com/Biosimulant/model-compatibility-standard.git
git fetch upstream
git switch -c profile/<domain>-<profile-name> upstream/scientific-review/v0-catalogue-reset
```

After the v0 reset is merged, branch from `upstream/main` instead.

Set up the repository:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
npm install
```

### 2. Add one profile YAML file

Create:

```text
source/profiles/<domain>/<profile-name>.yaml
```

The folder and filename become the profile ID, so
`source/profiles/proteome/protein-sequence.yaml` becomes
`proteome/protein-sequence@0.1`.

Copy the closest existing profile and replace its content. A minimal source
file looks like this:

```yaml
schema_version: "0.1"
label: Example Measurement
domain_label: Example domain
description: >
  A precise description of the data represented by this profile.
status: draft
representations: [scalar, record]
intended_use: >
  Connecting an output that produces this measurement to an input that consumes
  the same declared measurement.
limitations:
  - It does not establish that the value or producing model is scientifically valid.

fields:
  semantic.concept: required
  representation.kind: required
  measurement.quantity: required
  measurement.unit: required
  biological_context.species: under-review
  origin.method: under-review

examples:
  - id: BMCS-EXAMPLE-001
    title: Identical declarations are an exact match
    check: compare
    expect: {status: EXACT}
    why: No conversion or inference is needed.
    conditions: Both ports provide the same complete declarations.
    decision: Example profile draft
    report_finding: Positive baseline
```

This one file contains the scientific description, scope, all fields the
reviewer must consider, and profile-specific examples. Do not create a field
pack or edit a central profile list.

Every field must have one disposition:

- `required`
- `conditional` with a `when` statement
- `recommended`
- `excluded`
- `under-review`

Use `under-review` when the draft deliberately leaves the choice to the
scientist. Do not omit a debatable field simply to make the profile shorter.

### 3. Add a shared field only when necessary

Check `source/fields.yaml`. Reuse an existing path whenever it means the same
thing. If the profile needs a genuinely new scientific fact, add one field with
an explicit JSON value schema and comparison rule.

For example:

```yaml
- path: measurement.sampling_site
  family: measurement
  schema: {type: string, minLength: 1}
  comparison: equal
```

Do not add a near-duplicate field just to suit one profile. If the meaning is
not clear enough to share, raise it in the pull request.

### 4. Put scientific examples in the profile file

Each example should state what changes and what outcome is expected:

- `EXACT` or `DIRECT_COMPATIBLE` for a direct match;
- `LOSSLESS_CONVERSION_AVAILABLE` for a named lossless conversion;
- an approval-required result for a lossy transformation or inference;
- `INCOMPATIBLE` for a known contradiction; or
- `UNKNOWN` when necessary information is missing.

Use `source_patch`, `target_patch`, `source_remove` or `target_remove` to alter
the generated valid contract. The three current profiles provide working
examples. These examples are generated into
`spec/v0.1/fixtures/scientific.json` and run in both implementations.

### 5. Generate the software files

```bash
.venv/bin/python scripts/build_standard.py
```

The build creates:

- `spec/v0.1/profiles/<domain>/<profile-name>/v0.1.json` — the runtime profile;
- `spec/v0.1/fixtures/profiles/<domain>/<profile-name>.json` — baseline test
  cases; and
- `spec/v0.1/review-packets/<domain>/<profile-name>.json` — the complete mapping
  for the scientist.

The review packet includes every field from the profile YAML, not only required
fields. If a generated file is wrong, change the YAML or generator and rebuild.
Never edit `spec/v0.1/` directly.

### 6. Run the checks

```bash
.venv/bin/python scripts/build_standard.py --check
.venv/bin/pytest -p no:cacheprovider
PATH="$PWD/.venv/bin:$PATH" npm test
```

### 7. Open the pull request

Use a title such as:

```text
Profile: add <profile name> for <source model> to <target model>
```

The description should include:

- the source and target models and ports;
- intended use and limitations;
- the complete field mapping and unresolved decisions;
- worked examples and their expected outcomes;
- authoritative sources and versions;
- generated files changed; and
- test commands and results.

Keep a pull request to one profile unless a small group shares the same
scientific boundary. A useful proposal may remain a draft while a scientific
question is unresolved.

Do not create your own approval record. After the proposal is stable, an
independent scientist, a different schema reviewer and a domain owner complete
`source/reviews/<domain>/<profile-name>.yaml` using
`source/reviews/profile-review.template.yaml`.

## What changes for a typical profile?

Usually only these files:

1. `source/profiles/<domain>/<profile-name>.yaml` — written by the contributor.
2. Files under `spec/v0.1/` — regenerated by the build.

Sometimes:

3. `source/fields.yaml` — only when a necessary field is genuinely new.
4. `source/quantity-kinds.yaml` — only for a new or changed measurement kind.
5. `source/reviews/<domain>/<profile-name>.yaml` — later, when independent
   review is complete.

That is the full authoring path. There is no item pack, central profile entry or
separate scientific-cases file.

## Pull request checklist

- [ ] The profile comes from a real output-to-input connection.
- [ ] Small source and target examples are included.
- [ ] Intended use and limitations are clear.
- [ ] Every relevant field has an explicit disposition.
- [ ] Direct, incompatible and unknown outcomes are demonstrated.
- [ ] Every permitted conversion or inference is named and visible.
- [ ] Scientific decisions cite authoritative sources.
- [ ] Generated files were rebuilt rather than edited.
- [ ] Python and TypeScript tests pass.
- [ ] Independent review is recorded or clearly outstanding.
