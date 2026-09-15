# D1. Quantity kinds and units

**Status:** Decided: option (b). Implemented. **Owner:** unassigned. **Decided:** — . **Approved by:** —

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

## Evidence from the prototype

A working prototype of option (b) exists on branch `scientific-review/phase-0`, not yet wired into
comparison:

- `scripts/build_ucum_table.py` flattens the vendored UCUM 2.2 file, whose digest matches the pinned
  source, into `source/vendor/ucum/ucum-table.json`: 294 units resolved, 41 arbitrary, 3 affine
  (`Cel`, `[degF]`, `[degRe]`), and 18 logarithmic units (bel, neper and similar) listed as
  unrepresentable rather than converted.
- `python/src/.../units.py` and `typescript/src/units.ts` parse expressions over that table. The
  two agree on all 30 conversions tested.

What it gets right: g to kg ×0.001; Cel to K +273.15; [degF] to Cel ×5/9, −17.78; 1/s to /min ×60;
mm[Hg] to kPa ×0.1333; mo to d ×30.4375 (UCUM's mean Julian month); mass against molar concentration
incommensurable; [PFU] against [TCID_50] undecidable; `Cel/min` refused, because an offset means
nothing once combined.

What it cannot do, and why the quantity-kind registry is **required** rather than optional:

- **Hz converts to Bq with factor 1.** Both are 1/time. Radioactivity is not a firing rate.
  BMCS-SCI-016 pins this, so D1 cannot be declared done on dimensional analysis alone.
- **[hnsf'U] converts to 1 with factor 1.** UCUM does not flag Hounsfield units as arbitrary.
- **Annotations are ignored**, as UCUM specifies. `{BAU}/mL` and `{cells}/mL` both reduce to `/mL`
  and would convert silently. `[IU]/mL` against `{BAU}/mL` is refused only because `[IU]` happens
  to be flagged arbitrary.
- **`fmol/(cell.h)` is not UCUM**: `cell` is not a unit. The valid spelling is
  `fmol/({cell}.h)`, which parses, and then loses the per-cell basis to the annotation rule above.

The v0.1 spellings `nM`, `uM`, `mM` and `M` are carried as explicit, deprecated aliases so existing
contracts keep working until the fixtures migrate. Guard BMCS-SCI-103 depends on that.

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

**Adopted: option (b), UCUM plus a quantity-kind registry.** Implemented on
`scientific-review/phase-0`.

- `source/vendor/ucum/ucum-essence.xml` is vendored and pinned; `scripts/build_ucum_table.py`
  flattens it into `spec/v0.1/rules/units.json`, published with the bundle.
- `source/quantity-kinds.json` declares 37 kinds, published as `spec/v0.1/rules/quantity-kinds.json`.
  A kind fixes a dimension through its canonical unit and may forbid units whose UCUM property
  belongs to another quantity, which is what separates hertz from becquerel.
- `unit-convertible` is dimensional analysis in both engines, with affine units handled and
  arbitrary units commensurable only with themselves.
- Validation rejects a unit that cannot belong to the profile's quantity kind; comparison refuses to
  convert between contracts where one is internally inconsistent.
- **Spellings migrated, no aliases.** `uM`, `nM` and `mM` are not UCUM codes and no longer appear;
  the declarations use `umol/L` and friends. v0.1 has not been released, so nothing carries a
  deprecated spelling.

Settles BMCS-SCI-003 to 009, 011, 012 and 016, all now guards.
