# D12. Keeping technical status, policy and quality apart

**Status:** Decided: option (c) for v0.1. Implemented in part. **Owner:** unassigned. **Decided:** — . **Approved by:** —

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

**Adopted: option (c) for v0.1** — `policy_decision` stays in the report as a documented default
mapping, with the move to (b) reserved for the next major version.

Implemented now: comparison normalises its own inputs in both engines, so a set-like field written
in another order is no longer a contradiction for a caller who skipped the normalisation stage
(erratum E9). Normalisation degrades gracefully when a caller supplies a minimal bundle.

**Implemented: consent and data-use are out of the technical result.** A rule now declares its
`layer`, and the 100 rules on `security.data_use` and `security.consent_scope` are `policy`. A
policy rule is evaluated and reported in a new `policy_findings` array on the report, and it does
not touch the technical status: a data-use mismatch leaves two ports `DIRECT_COMPATIBLE` and raises
`BMCS_SECURITY_DATA_USE_MISMATCH` as a policy finding for the workspace-policy stage to act on.
Absent consent terms are treated the same way, as a governance question rather than an UNKNOWN.
`BMCS-SCI-113` guards it, and the generated fixtures for those paths became `comparison-policy-*`
rather than `comparison-incompatible-*`.

The field is still *required* where a profile requires it: validation continues to insist the port
declares its terms. What changed is that declaring different terms is no longer a statement about
whether the data fit together.

**Still open:** `policy_decision` remains in the report as the documented default mapping, which is
option (c) and deliberate for v0.1.
