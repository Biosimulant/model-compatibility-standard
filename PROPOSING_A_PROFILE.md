# Proposing a new compatibility profile

A profile is a shared agreement about one kind of data passed between model
ports. It states what information must be declared and how an output should be
compared with an input.

Propose a profile when two real models need to exchange data and no current
profile describes that exchange well enough. Do not start from a list of
biological concepts that might be useful one day.

## 1. Start with the connection

Describe one concrete case:

- the model and output port that produce the data;
- the model and input port that receive it;
- an example of what the output actually produces;
- an example of what the input accepts;
- the workflow in which the connection will be used; and
- why an existing profile cannot describe it.

Real examples matter because they expose assumptions that a profile name alone
does not: identifier releases, species, axes, normalisation, file variants,
time points, provenance and uncertainty.

## 2. Write the mapping before the profile

Record what the source provides, what the target expects, and the decision the
standard should make. Use this table in the issue or pull request and remove
rows that genuinely do not apply.

| Area | Source output | Target input | Required decision |
|---|---|---|---|
| Scientific meaning |  |  |  |
| Representation or file format |  |  |  |
| Identifiers and versions |  |  |  |
| Units, scale or normalisation |  |  |  |
| Dimensions, axes and ordering |  |  |  |
| Species and biological context |  |  |  |
| Timing or sampling |  |  |  |
| Origin and provenance |  |  |  |
| Uncertainty and missing values |  |  |  |

For each relevant field, decide whether it is:

- **required** — the contract cannot be interpreted safely without it;
- **conditional** — required in a stated situation;
- **recommended** — useful for interpretation but not a condition of use; or
- **excluded** — deliberately outside this profile.

Also state how the comparison should behave:

- direct match;
- lossless conversion available;
- transformation or inference requiring approval;
- incompatible because the declarations contradict each other; or
- `UNKNOWN` because information is missing.

Use `UNKNOWN` for absence of evidence. Use `INCOMPATIBLE` only for a known
contradiction.

## 3. Define the scientific boundary

Give the profile a narrow intended use and at least one important limitation.
Name any data that looks similar but should not use the profile. Cite primary or
authoritative sources for the scientific choices.

A profile only says whether interfaces fit for that stated use. It does not
approve the models, the data, the result, a clinical use, a consent basis or a
regulatory claim.

## 4. Add the draft

Add the profile and its item pack to `source/catalogue.review.json`.

- Reuse existing contract fields where they express the required decision.
- Add a field only when the current vocabulary cannot express it.
- Use a stable profile ID and version.
- Start at `V0_PILOT` with review status `draft`.
- Write comparison rules as data using the existing operator vocabulary.
- Keep the profile non-release-eligible until review is complete.

Run the generator:

```bash
python3 scripts/build_standard.py
```

This creates the profile, fixtures and a review packet under
`spec/v0.1/review-packets/<domain>/`. Inspect the generated files, but make
corrections in the source rather than editing generated JSON.

## 5. Check the examples

At minimum, the proposal must demonstrate:

- a valid contract;
- rejection when required information is missing;
- direct compatibility;
- a known incompatibility;
- `UNKNOWN` when the evidence is insufficient; and
- every conversion or inference outcome the profile permits.

The expected result should follow from the scientific mapping, not from what the
current implementation happens to return.

## 6. Obtain independent review

The profile author does not approve their own work.

- A scientific reviewer checks the meaning, scope, field decisions, rules,
  examples, sources, intended use and limitations.
- A different schema reviewer checks that those decisions are represented
  consistently and can be tested.
- A domain owner accepts responsibility for future changes and retirement.

Record the review in
`source/reviews/<domain>/<profile-name>.json`, starting from
`source/reviews/profile-review.template.json`. The reviewer must decide every
field in the generated packet, including fields proposed for exclusion.

Passing automated tests does not count as scientific approval.

## Pull request checklist

- [ ] A real output-to-input use case is identified.
- [ ] Example source and target data are included.
- [ ] The complete mapping table is filled in.
- [ ] Required, conditional, recommended and excluded fields are explicit.
- [ ] Direct, incompatible and unknown outcomes are demonstrated.
- [ ] Any conversion or inference is named and its approval requirement stated.
- [ ] Intended use, exclusions and limitations are clear.
- [ ] Scientific claims have primary or authoritative sources.
- [ ] Generated files were rebuilt rather than edited by hand.
- [ ] Python, TypeScript and scientific checks pass.
- [ ] Independent review roles are recorded or clearly marked as outstanding.

If the scientific boundary is still uncertain, open the proposal with that
question visible. A useful proposal can remain a draft; it should not hide the
uncertainty by making the profile broader.
