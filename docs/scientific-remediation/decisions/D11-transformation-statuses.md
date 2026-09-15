# D11. Lossy and inferred transformations

**Status:** Open. **Owner:** unassigned. **Decided:** — . **Approved by:** —

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

_To be recorded._
