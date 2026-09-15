# D6. Representation equivalence

**Status:** Decided in part: option (c). Mechanism implemented. **Owner:** unassigned. **Decided:** — . **Approved by:** —

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

**Adopted: option (c), conditional equivalence.** The mechanism is implemented; the per-profile data
it needs is not, and that half is review-gated.

Implemented:

- `representation.implicit_entry` is a new catalogue item taking `observed_zero`, `unobserved` or
  `not_applicable`, and `representation.sparsity` gains a real enum (`dense`, `sparse`) in place of
  the 4096-character free-text default it fell through to.
- A `representation-equivalent` operator in both engines. Equal kinds match. A dense/sparse pair is
  lossless only when both sides declare, and agree on, the implicit-entry meaning, the ordering and
  the sparsity; any of those undeclared is undecidable; a declared difference is a contradiction.
  Every other pair of kinds stays incompatible.
- The rule points at `/contract/representation`, not at `/contract`. Pointing it at the whole
  contract would have reached `shape` and `dtype`, but the finding's dimension is derived from the
  third pointer segment, so every representation finding would have been filed against the contract
  as a whole. Keeping the representation dimension is worth more than two fields that no profile
  requires.
- A new `evidence` loss token, reported as `BMCS_REQUIRED_EVIDENCE_MISSING`, so "nobody declared
  this" is distinguishable from "this needs a pinned snapshot". Reusing the snapshot code would have
  told a reader to go and pin an ontology that has nothing to do with the problem.
- Answering sub-question 2: a fully declared re-encoding yields `LOSSLESS_CONVERSION_AVAILABLE`, not
  `DIRECT_COMPATIBLE`. `BMCS-SCI-110` pins it, and `BMCS-SCI-104` still pins the unsafe direction.

**Narrowing reached 7 profiles, not the hundreds this record implies above.** A profile whose
reviewed structure declares an axis is not a scalar, so `scalar` is dropped from its allowed kinds.
That is the only narrowing the reviewed data supports, and most axis-bearing profiles turned out to
sit in an `applies_to` set that never offered `scalar` in the first place. 6 profiles were already
narrowed explicitly. Around 500 profiles still permit a scalar, a matrix, a tensor, a table and an
artifact at once: deciding what each of them actually admits is a scientific judgement about that
profile's meaning, and deriving it from the profile's name is exactly the heuristic D9 abolished.

**No re-encoding fixture is generated.** The lossless fixture would have to declare the three
enabling fields, and no profile requires any of them, so generating one for each of the 510
dense-and-sparse profiles would mean writing declarations the profiles never made into the
conformance suite. `BMCS-SCI-110` is hand-written instead, which is the honest home for a case whose
inputs are supplied by the case. Making those fields required for sparse-capable ports is per-profile
work for domain review.

**Sub-question 3 stays open.** A `sparse_matrix` kind is not added. The vocabulary genuinely lacks
it, but adding a kind while being unable to narrow 510 profiles widens what they accept, and
widening is the unsafe direction.
