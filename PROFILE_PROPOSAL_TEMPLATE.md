# Compatibility profile proposal

Copy this file to `proposal.md` and replace the prompts. Keep the proposal to
one real output-to-input connection. If a question is unresolved, say so rather
than guessing.

## Proposal details

- **Proposed profile name:**
- **Scientific domain:**
- **Proposer:**
- **Organisation:**
- **Contact:**
- **Proposed domain owner, if known:**

## The connection

- **Source model and version:**
- **Source output port:**
- **Target model and version:**
- **Target input port:**
- **Workflow and intended use:**
- **Why no current profile fits:**

## Representative examples

Link or attach a small, real or faithful redacted source output and target
input. Do not include credentials, patient data or confidential material.

- **Source example:**
- **Target example:**
- **Expected compatibility result:**
- **Reason for that result:**

Add further examples for a known contradiction, missing information and each
permitted conversion or inference.

## Complete mapping

Write `not relevant` only when the area cannot change scientific interpretation
or compatibility.

| Area | What the source produces | What the target accepts | Expected comparison |
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

## Field decisions

Use one disposition for every field the profile may need:

- `required` — the contract cannot be interpreted safely without it;
- `conditional` — required under a stated condition;
- `recommended` — useful, but not a condition of compatibility; or
- `excluded` — deliberately outside the profile; or
- `under-review` — a draft question the scientific reviewer must resolve.

| Contract field or scientific fact | Disposition | Condition, if any | Reason and source |
|---|---|---|---|
|  |  |  |  |

## Expected outcomes

| Example | Expected result | Scientific reason |
|---|---|---|
| Matching declarations |  |  |
| Known contradiction |  |  |
| Necessary declaration missing |  |  |
| Conversion or inference, if allowed |  |  |

Use `UNKNOWN` when evidence is missing and `INCOMPATIBLE` only when declarations
are known to contradict each other. Name and version every permitted conversion
or inference.

## Scientific boundary

- **Included use:**
- **Similar data that are out of scope:**
- **Important limitations:**
- **Claims this profile must not be used to make:**

## Sources

For each scientific decision, give a primary or authoritative source and the
version or access date used.

| ID | Citation or title | DOI or URL | Version or date | Decision supported |
|---|---|---|---|---|
| S1 |  |  |  |  |

## Review information

- **Suggested independent scientific reviewer, if known:**
- **Suggested schema reviewer, if known:**
- **Conflicts of interest or relevant relationships:**
- **Questions that still need a decision:**

Submitting this template proposes a profile. It does not approve the profile.
The author must not complete the independent approval record on behalf of a
reviewer.
