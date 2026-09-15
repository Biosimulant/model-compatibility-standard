# D8. Scale, value domain and transform

**Status:** Open. **Owner:** unassigned. **Decided:** — . **Approved by:** —

## Question

How does a contract state the measurement level, the value domain and any transform that has been
applied?

## Why it matters

`measurement.scale` currently mixes three separate ideas in one enumeration: `nominal`, `ordinal`,
`interval` and `ratio` are Stevens levels; `probability` and `count` are value domains; `log` is a
transform, and it does not say which base. Seventeen positive fixtures declare a dimensional
quantity on a `probability` scale. A log2 fold change and a log10 fold change are different numbers
under the same declaration.

## Options

| Option | For | Against |
|---|---|---|
| (a) Keep one enumeration, fix the wrong values | Smallest change | The conflation stays, and `log` remains base-less |
| (b) Split into level, value domain and transform | Each field means one thing | Three fields to populate; migration across 124 profiles |
| (c) Level plus a free-text transform | Flexible | Free text cannot be compared |

## Recommendation

Option (b). `measurement.scale` keeps the Stevens level (`nominal`, `ordinal`, `interval`,
`ratio`). A value-domain vocabulary adds `proportion` — bounded [0,1] but not a probability —
alongside `probability` and `count`. A transform item carries the function and its parameters:
`log2`, `log10`, `ln`, `logit`, with base and any pseudocount or offset explicit.

## What adopting it changes

- A new `measurement.transform` item; the catalogue has none today.
- Scale values corrected across the 124 profiles that require a unit, and `probability` restricted
  to dimensionless quantities.
- Transform-aware comparison: log2 to linear is exact given the base and offset; log2 to log10 is a
  declared conversion; beta to M-value becomes expressible.

## Sub-questions

1. Is the value domain a separate field or part of the quantity kind (D1)?
2. Should bounds ([0,1], non-negative) be constraints instead?
3. Is an ordinal scale on a log-spaced grid (two-fold dilution titres) expressible?

## Tests

Settles BMCS-SCI-013. Add on adoption: a log2 and a log10 value of the same quantity must not be a
direct match.

## Sources to pin

`stevens-1946`, `vim-jcgm-200-2012`, `du-2010-mvalue`.

## Decision

_To be recorded._
