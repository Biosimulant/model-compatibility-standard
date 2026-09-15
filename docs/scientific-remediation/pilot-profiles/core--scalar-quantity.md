# Scalar Quantity — `core/scalar-quantity@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D2, D3, D8, D10.

## Proposed scientific meaning

One numeric value of a declared quantity kind, expressed in a declared unit, or explicitly
dimensionless. The structural base of the catalogue: it says what it takes to exchange a single
number safely, and every domain scalar profile should inherit that answer rather than restate it.

It is not a category label, not an identifier, not a boolean, and not a bounded score; those are
separate core profiles.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity of the quantity, from a version-independent term (D3). |
| `representation.kind` | Restricted to `scalar`. Today the profile also admits `matrix`, `tensor` and `table`, which contradicts its own name. |
| `measurement.quantity` | The quantity kind. Dimension alone is not identity: torque and energy are both N·m, and frequency and radioactivity are both 1/s. Without a quantity kind, a dimensional check will accept Hz where Bq is meant. |
| `measurement.unit` | A UCUM code, with `1` written explicitly for a dimensionless value, so silence and dimensionlessness stay distinguishable. |
| `measurement.scale` | Whether the value is ratio or interval decides which conversions are valid: an affine unit conversion is correct for an interval quantity and wrong for a difference. |

**Conditional**

| Field | Condition |
|---|---|
| `semantic.subject` | Required only when the value is about a biological entity. A core scalar usually has no subject, and the current placeholder `data_value` carries no meaning. |
| `uncertainty.kind`, `uncertainty.interval`, `uncertainty.confidence_level` | Required when an uncertainty travels with the value; an interval without its level is uninterpretable. |
| `constraints[]` | Required when the quantity is bounded (a fraction in [0,1], a non-negative magnitude) so the bound travels with the contract. |
| `representation.precision` | Required when a consumer depends on numeric precision (checkpoint and replay use). |

**Recommended.** `origin.type` (measured, simulated, inferred); `measurement.aggregation` when the
number summarises repeats.

**Deliberately not gating.** `biological_context.*` — a core scalar is defined independently of any
organism, and requiring species here would assert biological scope the value does not have.
`artifact.*` — the value is exchanged inline. `security.*` — a bare number carries no consent scope
by itself; the domain profile that wraps it does.

**Proposed new items.** A quantity-kind registry, so `measurement.quantity` resolves to a term with
a dimension and a canonical unit (D1). Nothing in the catalogue provides that today.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `measurement.quantity` | equal, or declared equivalence | unknown | Hz vs Bq INCOMPATIBLE despite the same dimension |
| `measurement.unit` | dimensional conversion (D1) | unknown | g vs kg lossless; mg vs s INCOMPATIBLE |
| `measurement.scale` | equal | unknown | — |
| `representation.kind` | equal | unknown | Only `scalar` is allowed, so this rarely fires |

## What v0.1 gets wrong here

- Two ports declaring `mg` and `s` return DIRECT_COMPATIBLE (BMCS-SCI-003): units are declared on
  both sides but the profile does not require them, so they are never compared.
- The allowed representation set contradicts the profile name.
- `semantic.subject` is required and free-text, so the only mandatory "meaning" is a placeholder.
- No unit is required at all, which for a profile whose entire purpose is a quantity is the central
  defect.

## Fixtures to regenerate

- **positive**: `kind: scalar`, quantity a real kind, `unit: g`, `scale: ratio`, no subject.
- **conversion**: `g` to `kg` lossless.
- **contradiction**: `mg` vs `s`; Hz vs Bq (same dimension, different quantity kind).
- **unknown**: unit absent on either side.
- **invalid**: `kind: matrix` rejected once the enum is narrowed.

## Questions for the reviewer

1. Should this profile be matchable at all, or only a base that domain profiles extend? The
   `extends` mechanism exists but is empty everywhere.
2. Is a quantity kind required even when the value is dimensionless, or is `unit: 1` enough?
3. Should bounded scalars be handled here through constraints, or stay with `core/bounded-score`?
4. Is `scale` the right place for the interval/ratio distinction, given D8 may split scale from
   value domain and transform?

## Sources to pin

`vim-jcgm-200-2012` (quantity, quantity kind, unit); `iso-80000-1-2022`; `si-brochure-9`;
`ucum-2.2`; `stevens-1946`. Each needs a SHA-256 at sign-off.

## Tests

BMCS-SCI-003; guard BMCS-SCI-102.
