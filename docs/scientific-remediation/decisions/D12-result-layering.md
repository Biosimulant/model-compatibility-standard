# D12. Keeping technical status, policy and quality apart

**Status:** Open. **Owner:** unassigned. **Decided:** — . **Approved by:** —

## Question

Where does the technical compatibility result end, and where do workspace policy and Passport
quality begin?

## Why it matters

`INTEGRATIONS.md` says to keep the three results separate, and `compare_contracts` returns
`policy_decision` alongside `status`, derived from it: UNKNOWN and INCOMPATIBLE become `BLOCK`, a
lossy conversion becomes `APPROVAL_REQUIRED`. So the comparison already makes a policy judgement.
Two consequences show up in the scientific checks:

- Consent and data-use mismatches surface as technical INCOMPATIBLE, though they are governance
  outcomes, not statements about whether the data fit together.
- `compare_contracts` does not normalise its inputs, so a caller who skips the contract-
  normalisation stage gets INCOMPATIBLE purely from the element order of a set-like field. Whether
  normalisation belongs inside comparison is part of this decision (erratum E9).

## Options

| Option | For | Against |
|---|---|---|
| (a) Keep `policy_decision` in the report | No consumer breakage | The layers stay mixed; policy is baked into a technical artifact |
| (b) Remove it; policy is computed by the workspace-policy stage | Clean separation, matching the documented pipeline | Breaking change for consumers of the report schema |
| (c) Keep it, clearly marked as a default policy mapping that a workspace may override | Compatible and honest | Two sources of truth if a workspace overrides silently |

## Recommendation

Option (c) for v0.1 consumers, moving to (b) at the next major version, with the report stating
which policy mapping produced the decision. Independently: comparison should normalise its inputs,
or the API should refuse un-normalised contracts, rather than silently giving order-dependent
answers.

## What adopting it changes

- Report schema documentation states that `policy_decision` is a default mapping, not a workspace
  decision.
- Security and consent comparisons move out of the technical result, or are marked as policy
  findings within it.
- `compare_contracts` normalises, or documents the precondition and fails loudly.

## Sub-questions

1. Do consent and data-use mismatches produce a technical finding at all?
2. Should Passport quality ever influence a compatibility status? The current answer is no; is that
   right?
3. If comparison normalises internally, does the digest in the report cover the raw or the
   normalised contract?

## Tests

Contributes to BMCS-SCI-015 (measured versus simulated), and must keep guard 108 passing: reordering
a set-like field must not change the result once contracts are normalised.

## Sources to pin

`duo-2021`, plus the standard's own `INTEGRATIONS.md` and pipeline definition.

## Decision

_To be recorded._
