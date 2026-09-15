# D11. Lossy and inferred transformations

**Status:** Decided in part: option (c). Mechanism implemented. **Owner:** unassigned. **Decided:** — . **Approved by:** —

## Question

What must a declared transformation carry, and how are the lossy and inference paths exercised?

## Why it matters

`transformation_policy` declares `lossless: allow`, `lossy: approval` and `inference: approval` for
every profile, but no profile has a lossy or an inference fixture. 526 profiles have an empty
transformations group and the remaining 124 have one lossless fixture — the nM to uM one that is
wrong for most of them. Both approval branches are therefore untested in both implementations, and
those branches are exactly where a silent scientific substitution would happen, because the failure
mode is a status that reads as "fine".

## Options

| Option | For | Against |
|---|---|---|
| (a) Leave the paths untested | No work | The standard's main safety claim is unverified |
| (b) A shared set of synthetic transformation fixtures | Cheap coverage | Does not exercise real domain transformations |
| (c) Per-profile lossy and inference fixtures, generated from declarations | Tests the real paths | Needs D9, and a transformation registry |

## Recommendation

Option (c). Every profile whose policy admits them gets at least one lossy fixture (a continuous
value binned to an ordinal category, counts to log-normalised values) and one inference fixture (a
value only a model can produce: imputed, deconvolved, or derived from a different assay). A declared
transformation must carry its direction, its parameters, its digest, and whether it is invertible.

## What adopting it changes

- A transformation registry, with digests, sitting alongside the profile catalogue.
- Generated lossy and inference fixtures across the catalogue (D9).
- Approval receipts become testable end to end, which is what `compatibility_approval_create`
  assumes.

## Sub-questions

1. Is a parameterised conversion (mass to molar with a molar mass) lossless with the parameter
   declared, or always approval?
2. Must an inference declare the model that performs it, and does the model's digest gate the
   result?
3. Can a transformation chain be composed automatically, or must each step be declared?

## Tests

No case today. Add on adoption: counts to log-normalised must require approval; an inferred value
must never be `DIRECT_COMPATIBLE`.

## Sources to pin

`wagner-2012-tpm`, `robinson-2010-tmm`, `svensson-2020-zeros`.

## Decision

**Adopted: option (c).** The mechanism is implemented and both approval paths are now exercised in
both languages. The per-profile fixtures are not, and that half is review-gated.

**The defect turned out to be larger than missing fixtures.** Every one of the 650 profiles
publishes `transformation_policy`, and nothing read it. `_policy_decision` in the resolution layer
accepts a policy keyed exactly `lossless` / `lossy` / `inference` / `conditional` / `unknown` — the
published shape — but no code path ever handed a profile's policy to it, so the only policy that
could take effect was one a caller passed in by hand. A profile declaring `lossy: block` still
produced `APPROVAL_REQUIRED`. Both engines now default the policy to the one published by the
target contract's own profiles, with the most restrictive setting winning where a contract names
several, and the published `allow` / `approval` / `block` vocabulary translated into the
`ALLOW` / `APPROVAL_REQUIRED` / `BLOCK` decision vocabulary.

Fixing that exposed a divergence in the same function: TypeScript accepted a configured value only
when it already belonged to the decision vocabulary and otherwise fell through to the default
mapping, while Python returned whatever it found verbatim. Feeding Python a published policy would
have emitted the literal `"approval"` where TypeScript emitted `"APPROVAL_REQUIRED"`, and the plan
schema would not have caught it because `policy` is an open object. Python now guards it the same
way.

**The plan carries its own status.** `technical_status` is a new required field on the resolution
plan. `reports[]` holds the *terminal* comparison, which is `EXACT` whenever the last adapter lands
exactly on the target, so a lossy chain, an inference chain and a direct match were
indistinguishable to a reader of the plan — and to any test asserting on the report. This was found
by probing the resolver rather than by reasoning about it: the first version of the guards below
asserted `reports[0].status` and would have passed while testing nothing.

**Both approval paths are now tested, for the first time.** Every capability in every existing test
in both languages used `information_loss: "none"`, and no test anywhere built an inference
capability, so the two branches carrying the standard's central safety claim were unexercised.
`BMCS-SCI-111` bins a continuous firing rate into ordinal bands through a lossy adapter;
`BMCS-SCI-112` bridges the same two contracts with an inference model. The contracts and the patch
are deliberately identical, so the capability kind is the only difference between them.

The scientific-checks harness gained a fourth check kind, `resolve`, in both languages. A capability
is indexed by the digest of its source contract, so a case written into the file cannot name a
contract the harness builds from a profile fixture; `$source` and `$target` stand in for those and
are substituted before the resolver validates anything.

Answering the sub-questions: an inference must declare its model — `inferred_modality`, `assumptions`
and `uncertainty` are all required by the schema, and the capability is pinned by `ref` and `sha256`
in the plan's `immutable_references`. Chains are composed automatically, bounded by
`max_transformations` (8) and `max_inferences` (2).

**Still open: the per-profile lossy and inference fixtures.** A real lossy fixture has to declare an
actual domain transformation with its parameters — counts to log-normalised values with the
normalisation named, a continuous measure binned with its cut points. That is scientific content per
profile, not something a generator can synthesise, and inventing it for 650 profiles is the failure
mode D9 exists to prevent. A published transformation registry is open for the same reason; the
mechanism does not need one, since capabilities are already pinned by digest.
