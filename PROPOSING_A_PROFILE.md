# Proposing a new compatibility profile

A profile is a shared agreement about one kind of data passed between model
ports. It states what information must be declared and how an output is
compared with an input.

Propose a profile when two real models need to exchange data and no current
profile describes that exchange well enough. You can send the proposal to the
Biosimulant team or open a pull request yourself. Both routes use the same
[profile proposal template](PROFILE_PROPOSAL_TEMPLATE.md).

## What to prepare

Start with one concrete connection:

- the model and output port that produce the data;
- the model and input port that receive it;
- a real or faithful redacted example of the output;
- a real or faithful redacted example of what the input accepts;
- the workflow and intended use; and
- why an existing profile cannot describe it.

Complete the mapping in the proposal template. For each relevant field, say
whether it is required, conditional, recommended or deliberately excluded.
State what should happen when values match, contradict each other or are
missing.

Do not send credentials, patient data, unpublished confidential data or a large
dataset. A small synthetic or redacted example is normally enough. If the
evidence cannot be shared publicly, describe it and tell us how an authorised
reviewer can obtain access.

## Route A: send the proposal to Biosimulant

Email `demi@biosimulant.com` with the subject:

```text
Model compatibility profile proposal: <profile name>
```

Attach one folder or zip file named `<profile-name>-proposal` containing:

1. `proposal.md` — a completed copy of
   [PROFILE_PROPOSAL_TEMPLATE.md](PROFILE_PROPOSAL_TEMPLATE.md). A Word or PDF
   copy is also acceptable if it keeps the same headings and tables.
2. `source-contract.yaml` or `source-contract.json` — the smallest realistic
   description of the producing port.
3. `target-contract.yaml` or `target-contract.json` — the smallest realistic
   description of the receiving port.
4. An `examples/` folder with small, redacted examples covering a direct match,
   a known contradiction, missing evidence and every permitted conversion or
   inference. Include the expected result for each example.
5. Links, DOIs or versioned references for the sources behind the scientific
   decisions.

If YAML or JSON is not practical, put the source and target declarations in the
mapping table in `proposal.md`. The scientific information matters more than
getting the repository format right at this stage.

The team will check that the case belongs in the standard, agree a profile ID
with you, create the machine-readable draft and return any scientific questions.
Sending a proposal is not scientific approval. Independent review still happens
before the profile can leave draft status.

## Route B: open a pull request

### 1. Create a branch

Fork the repository, then create a branch from the active catalogue branch:

```bash
git clone https://github.com/<your-account>/model-compatibility-standard.git
cd model-compatibility-standard
git remote add upstream https://github.com/Biosimulant/model-compatibility-standard.git
git fetch upstream
git switch -c profile/<domain>-<profile-name> upstream/scientific-review/v0-catalogue-reset
```

The v0 catalogue reset is currently under review. After it is merged, replace
`upstream/scientific-review/v0-catalogue-reset` with `upstream/main`.

Set up the test environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
npm install
```

### 2. Add the profile to the source catalogue

Edit `source/catalogue.review.json`. This is the source of truth.

- Reuse an entry in `item_definitions` when it already expresses the required
  scientific fact. Add a definition only when the vocabulary is genuinely
  missing one.
- Add an `item_packs` entry containing every field the reviewer should consider,
  including candidate fields that may later be excluded.
- Add one `profiles` entry. Give it a stable domain, name and ID; use version
  `0.1.0`, stage `V0_PILOT` and review status `draft`.
- Put fields that are provisionally essential in `required_items`. Do not hide a
  debatable field by omitting it from both `required_items` and the item pack.
- Keep the description, compatibility notes and scientific non-claim narrow and
  specific to the intended use.

Do not edit files under `spec/v0.1/` by hand. Build them from the source:

```bash
.venv/bin/python scripts/build_standard.py
```

The build creates or updates:

- `spec/v0.1/profiles/<domain>/<profile-name>/v0.1.json` — the profile consumed by
  implementations;
- `spec/v0.1/fixtures/profiles/<domain>/<profile-name>.json` — validation and
  comparison cases; and
- `spec/v0.1/review-packets/<domain>/<profile-name>.json` — every required and
  candidate field the scientist must review.

Read all three files. If they are wrong, change `source/catalogue.review.json`
and rebuild. Commit the source change and the generated files together.

### 3. Deal with examples correctly

Include the real or redacted source and target examples in the pull-request
description or attach them to the pull request. For each example, state the
expected result and why:

- direct compatibility;
- a named, lossless conversion;
- a transformation or inference that needs approval;
- incompatibility because two declarations contradict each other; or
- `UNKNOWN` because a necessary declaration is missing.

The generator creates baseline fixtures for every required field. Inspect those
fixtures; do not edit them directly. If an important scientific rule is not
covered by the generated cases, add a small shared case to
`scientific-checks/v0.1/cases.json` and explain it in the pull request. See
[scientific-checks/README.md](scientific-checks/README.md) for the case format.

Use `UNKNOWN` for missing evidence. Use `INCOMPATIBLE` only for a known
contradiction. A conversion or inference must be visible and versioned; it must
not be treated as a direct match.

### 4. Run the checks

```bash
.venv/bin/python scripts/build_standard.py --check
.venv/bin/pytest -p no:cacheprovider
npm test
```

The generated files must be current, both implementations must agree, and the
scientific cases must produce their declared outcomes.

### 5. Open the pull request

Use a title such as:

```text
Profile: add <profile name> for <source model> to <target model>
```

In the description, include the completed proposal template and list:

- the source and target models and ports;
- the intended use and exclusions;
- links to the example input and output;
- the full mapping and field decisions;
- the expected outcomes demonstrated by the examples;
- the authoritative sources and their versions;
- files changed by the generator;
- commands run and their results; and
- questions that still require scientific judgement.

Keep one pull request to one profile, or to a small set that shares exactly the
same scientific boundary. It is acceptable for a useful proposal to remain a
draft while a question is unresolved.

Do not create your own approval record. After the mapping is stable, an
independent scientist, a different schema reviewer and a domain owner record
their decisions in `source/reviews/<domain>/<profile-name>.json`, starting from
`source/reviews/profile-review.template.json`. Passing the tests does not count
as scientific approval.

## Worked example: Protein Sequence

Suppose a source model emits a human protein sequence with these declarations:

```yaml
identifier: P69905
sequence: MVLSPADKT...
namespace: UniProtKB
namespace_version: "2026_03"
species: NCBITaxon:9606
alphabet: IUPAC-amino-acid
encoding: single-letter
```

The target accepts a single-letter IUPAC amino-acid sequence for the same
UniProtKB release and species. The proposal should explain that:

- matching declarations are a direct match;
- a missing namespace version gives `UNKNOWN`, because the identifier cannot be
  interpreted against a known release;
- a declared mouse sequence and a target restricted to human are incompatible;
  and
- converting a three-letter sequence to a single-letter sequence is a visible
  transformation, not a direct match.

In the repository, this becomes:

1. a `protein-sequence` item pack listing all fields the scientist should
   consider;
2. a `proteome/protein-sequence@0.1` profile listing the provisional required
   fields;
3. generated direct, incompatible, missing and invalid cases in
   `spec/v0.1/fixtures/profiles/proteome/protein-sequence.json`; and
4. a generated review packet in
   `spec/v0.1/review-packets/proteome/protein-sequence.json`.

The example sequence itself is not enough. The profile exists to preserve the
meaning around the sequence: identity system and release, representation,
species, provenance and any limitation on its use.

## Pull request checklist

- [ ] The proposal starts from a real output-to-input connection.
- [ ] Small source and target examples are included or access is explained.
- [ ] The complete mapping table is filled in.
- [ ] Required, conditional, recommended and excluded fields are explicit.
- [ ] Direct, incompatible and unknown outcomes are demonstrated.
- [ ] Every permitted conversion or inference is named and visible.
- [ ] Intended use, exclusions and limitations are clear.
- [ ] Scientific decisions cite primary or authoritative sources.
- [ ] Generated files were rebuilt rather than edited by hand.
- [ ] Python, TypeScript and scientific checks pass.
- [ ] Independent review roles are recorded or clearly marked as outstanding.
