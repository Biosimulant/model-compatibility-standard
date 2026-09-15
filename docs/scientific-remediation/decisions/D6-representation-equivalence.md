# D6. Representation equivalence

**Status:** Open. **Owner:** unassigned. **Decided:** — . **Approved by:** —

## Question

When are two representations of the same values interchangeable, and when is the re-encoding
lossless?

## Why it matters

`representation.kind` is compared with `equal`, so dense and sparse encodings of the same matrix
return INCOMPATIBLE. That is the safe direction of error, but it blocks valid couplings. The
tempting fix — declaring dense and sparse equivalent — is wrong: the re-encoding is lossless only
when the implicit entry's meaning (an observed zero, or an unobserved value), the ordering, the
shape and the dtype are all declared and equal. In single-cell data the zero-versus-missing
distinction is exactly what is at stake.

## Options

| Option | For | Against |
|---|---|---|
| (a) Keep exact equality | Never wrong in the unsafe direction | Blocks correct couplings; pushes adapters outside the standard |
| (b) A fixed equivalence table between kinds | Simple | Ignores the conditions that make it true |
| (c) Conditional equivalence: lossless only when the enabling fields are declared equal | Correct | Requires those fields to exist and be required where relevant |

## Recommendation

Option (c). Declare dense to sparse lossless when implicit-entry meaning, ordering, shape and dtype
are declared and equal; UNKNOWN when any is undeclared; INCOMPATIBLE when one differs. Matrix to
table requires a declared schema mapping. Narrow each profile's allowed kinds to those its meaning
admits — `core/scalar-quantity` currently permits `matrix`, `tensor` and `table`.

## What adopting it changes

- `representation.sparsity` gains an implicit-entry meaning, required for sparse ports.
- Allowed-kind enumerations narrowed per profile, which changes 395 profiles carrying the full
  eight-kind set.
- A lossless re-encoding fixture per affected profile.

## Sub-questions

1. Is dtype part of the contract, or of the transport layer described by `model.yaml`?
2. Does a lossless re-encoding produce `LOSSLESS_CONVERSION_AVAILABLE` or `DIRECT_COMPATIBLE`?
3. Are sparse matrices representable at all, given the kind vocabulary has `sparse_vector` but no
   sparse matrix?

## Tests

Must keep guard BMCS-SCI-104 passing: dense against sparse with nothing declared is not a lossless
match. Add on adoption: the fully declared pair must be lossless.

## Sources to pin

`svensson-2020-zeros`, `edam-2013`.

## Decision

_To be recorded._
