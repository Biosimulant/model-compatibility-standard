# Molecular Weight — `chemical/molecular-weight@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D3, D7, D10.

## Proposed scientific meaning

The mass of a declared chemical entity in a declared form, as either the molar mass `M` in g/mol or
the relative molecular mass `Mr`, which is dimensionless. The two are numerically equal and
scientifically distinct, which makes this the pilot's test of whether the standard can tell apart
two quantities that always print the same number.

Averaged over natural isotopic abundance unless a monoisotopic mass is declared. The chemical form
is part of the quantity: a free base, its hydrochloride salt and a hydrate have different masses.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity (D3). |
| `representation.kind` | Scalar, or a vector over compounds. |
| `measurement.quantity` | Molar mass or relative molecular mass. The current profile cannot express the difference. |
| `measurement.unit` | `g/mol` for molar mass; `1` for relative molecular mass. UCUM 2.2 has no `Da`, so a dalton spelling must be chosen deliberately if atomic mass units are wanted. |
| `measurement.scale` | `ratio`. |
| `identifiers.namespace`, `identifiers.namespace_version` | Which compound: ChEBI, PubChem CID or an equivalent, with its release. A mass without an entity is not comparable. |
| `representation.isotope_state` | Average-abundance mass and monoisotopic mass differ by roughly one part in a thousand — enough to matter in mass spectrometry and not enough to look wrong. |

**Conditional**

| Field | Condition |
|---|---|
| `identifiers.structure_hash` | Recommended generally, required when the port is matched by structure rather than by database identifier; an InChIKey settles identity when namespaces differ. |
| `representation.formal_charge`, `representation.protonation_state` | Required when the entity is an ion or a declared protonation state; the mass follows the charge state. |
| `identifiers.mapping_refs`, `identifiers.unmapped_handling` | Required when identifiers are mapped between namespaces. |
| `representation.stereochemistry` | Not mass-relevant, but required when the same port is also used to assert compound identity for downstream use. |

**Recommended.** `origin.method` (computed from formula vs measured); `origin.software_version` when
computed.

**Deliberately not gating.** `biological_context.*` — a molecular mass is a property of a chemical
entity, not of an organism, and the profile correctly requires no species today. `artifact.*`.
`security.*`, except where a compound library is licensed, which is a policy matter rather than a
compatibility one (D12).

**Proposed new items.** A chemical-form declaration (parent, salt, hydrate, solvate). Nothing in the
catalogue carries it, and it changes the number materially. In practice it can also be carried by
using the salt's own database identifier, which the reviewer should choose between.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `measurement.quantity` | equal, or a declared exact relation | unknown | `Mr` and `M` are related exactly by the molar mass constant, so the conversion is lossless and must be declared rather than assumed |
| `measurement.unit` | dimensional conversion (D1) | unknown | `g/mol` vs `1` is a dimension difference, which is why the quantity-kind relation above has to carry it |
| `representation.isotope_state` | equal | unknown | Average vs monoisotopic INCOMPATIBLE |
| `identifiers.namespace` + version | equal, or pinned mapping (D7) | unknown | ChEBI to PubChem is a mapping, not identity |
| chemical form | equal | unknown | Free base vs salt INCOMPATIBLE |

## What v0.1 gets wrong here

- `unit: 1` with `scale: ratio` and no quantity distinction: the profile silently picks relative
  molecular mass while its name suggests molar mass.
- No compound identifier is required, so two masses of different molecules compare as directly
  compatible.
- No isotope state and no chemical form.
- The conversion fixture asserts `nM -> uM` for a mass (BMCS-SCI-011).

## Fixtures to regenerate

- **positive**: quantity molar mass, `unit: g/mol`, `scale: ratio`, compound `CHEBI:15377` with a
  ChEBI release, isotope state average.
- **lossless**: relative molecular mass to molar mass, via the declared exact relation.
- **contradiction**: average vs monoisotopic; free base vs hydrochloride salt; different compound.
- **unknown**: compound identifier absent; isotope state absent.

## Questions for the reviewer

1. Should `Mr` and `M` be one profile with a declared quantity, or two profiles?
2. How should chemical form be declared: a new item, or by requiring the identifier of the exact
   form?
3. Should this profile and `chemical/exact-mass` be merged, given exact mass is the monoisotopic
   case?
4. Which namespace is primary, and is an InChIKey sufficient on its own?
5. Are macromolecules (average protein mass from sequence) in scope, where the value is computed
   rather than looked up?

## Sources to pin

IUPAC Gold Book, relative molecular mass (`10.1351/goldbook.R05271`); `iso-80000-1-2022`;
`si-brochure-9` (the mole and the molar mass constant); `ucum-2.2` (`g/mol`; no `Da`); InChI
(Heller et al. 2015, `10.1186/s13321-015-0068-4`); ChEBI or PubChem, whichever is adopted. Each
needs a SHA-256 at sign-off.

## Tests

BMCS-SCI-011; a Phase 2 case for `Mr` against `M`, which must be a declared lossless relation
rather than either a silent match or a dimension contradiction.
