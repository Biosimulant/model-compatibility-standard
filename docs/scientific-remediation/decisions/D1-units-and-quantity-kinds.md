# D1. Quantity kinds and units

**Status:** Open. **Owner:** unassigned. **Decided:** — . **Approved by:** —

## Question

How are units validated, how are two units compared, and what ties a unit to the quantity a profile
measures?

## Why it matters

The conversion table has four rows (nM, uM, mM). Everything else fails: g vs kg, Cel vs K, 1/s vs
/min and uM vs mol/L all return INCOMPATIBLE, while a firing rate declared in kg validates cleanly.
Dimension alone is not enough either — frequency and radioactivity are both 1/s, torque and energy
are both N·m.

## Options

| Option | For | Against |
|---|---|---|
| (a) Keep the table, extend it as needed | No new dependency | Never converges; every new unit pair is a code change |
| (b) UCUM grammar + dimensional analysis + a Biosimulant quantity-kind registry | Units become computable; the registry supplies what UCUM does not | Registry must be built and maintained; fixture spellings change |
| (c) QUDT quantity kinds with UCUM codes | Quantity kinds already modelled | Heavier dependency; overlap with UCUM needs reconciling |

## Recommendation

Option (b). Checked against UCUM 2.2 (revision 2024-06-17):

- `[PFU]`, `[TCID_50]` and `[hnsf'U]` exist and can be used directly.
- There is **no** `M` for molar — `M` is the mega prefix — so `uM`, `nM` and `mM` in today's
  fixtures are not UCUM codes. Molar concentration is `umol/L`.
- `mol` is defined as a count, which is why mass concentration and molar concentration are not
  interconvertible without a molar mass.
- `Da` is not defined; a dalton spelling must be chosen deliberately.
- `[BAU]` is a bioequivalent *allergen* unit, not WHO binding antibody units.

## What adopting it changes

- `measurement.unit` validated as a UCUM expression; `unit-convertible` implemented as dimensional
  analysis with a factor, replacing `spec/v0.1/rules/unit-conversions.json`.
- A quantity-kind registry binds each profile's quantity to a dimension and a canonical unit, and
  rejects dimensionally impossible units.
- Affine units handled explicitly: absolute temperature converts with an offset, a temperature
  difference does not. This needs distinct quantity kinds.
- Mass-to-molar becomes a declared parameterised transformation carrying a molar mass, not a
  conversion and not a contradiction.
- Fixture spelling migration across the 124 profiles that require a unit.

## Sub-questions

1. Migrate `uM` to `umol/L`, or accept non-UCUM spellings with a mapping?
2. How are annotated units (`{person}`, `{cell}`, `{DW}`) handled, given UCUM ignores annotations in
   comparison — `{BAU}/mL` and `{cells}/mL` both reduce to `/mL`?
3. Does a parameterised conversion produce `LOSSLESS_CONVERSION_AVAILABLE` with the parameter
   declared, or always require approval?

## Tests

Settles BMCS-SCI-003 to 009, 011 and 012. Must keep guards 102, 103 and 105 passing — in particular
105, where mass and molar concentration must stay non-convertible without a molar mass.

## Sources to pin

`ucum-2.2`, `si-brochure-9`, `vim-jcgm-200-2012`, `iso-80000-1-2022`, `uo-2012`.

## Decision

_To be recorded._
