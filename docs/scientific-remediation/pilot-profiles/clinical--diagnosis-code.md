# Diagnosis Code — `clinical/diagnosis-code@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D2, D4, D7, D10, D12.

## Proposed scientific meaning

A coded clinical diagnosis for a patient, drawn from a declared code system at a declared version,
with the clinical context that makes it interpretable: what kind of assertion it is, and where it
came from.

A code carries no magnitude, so the value of this pilot is in identifiers, versioning and
governance. It is also the clearest case for keeping the three layers apart: whether two ports can
exchange codes is a technical question; whether they are *permitted* to is not.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity (D3). |
| `representation.kind` | Scalar, record, or table. |
| `identifiers.coding_system` | ICD-10-CM, ICD-11 MMS, SNOMED CT, Read: the same string means different things in different systems. |
| `identifiers.coding_version` | Code meanings change between annual releases; codes are added, retired and re-parented. |
| `identifiers.namespace`, `identifiers.namespace_version` | The identifier namespace for the code itself, consistent with the coding system. |
| `biological_context.species` | Constant human here, and worth stating as a constraint rather than a free field. |
| `lifecycle.temporal_meaning` | An encounter diagnosis, a problem-list entry and a billing claim line are different assertions about the same code. |

**Conditional**

| Field | Condition |
|---|---|
| `identifiers.mapping_refs`, `unmapped_handling`, `ambiguity_handling` | Required when codes are mapped between systems. ICD-10-CM to SNOMED CT is many-to-many and incomplete; the mapping's release and digest must travel with it. |
| `origin.type` | Required when administrative and clinical sources are both in scope: claims data and EHR problem lists have different error profiles. |
| `security.data_use`, `security.consent_scope` | Required for patient-level data, expressed as DUO terms rather than free text. |
| `security.deidentification` | Required for patient-level data: diagnosis codes are quasi-identifiers, and rare codes are re-identifying. |
| `security.workspace_boundary` | Required when the data may not leave a controlled environment. |
| `biological_context.cohort`, `biological_context.population` | Required for cohort-level ports. |
| `uncertainty.quality_flags` | Required when codes carry status (suspected, ruled out, historical). |

**Recommended.** `origin.observed_at` (diagnosis date, subject to date shifting);
`security.residency`; `semantic.qualifiers` for primary versus secondary diagnosis.

**Deliberately not gating.** `measurement.*` — no magnitude is carried; requiring a unit or scale
here would be meaningless, and the generator's measurement items do not apply.
`artifact.*` unless exchanged as a file.

**Proposed new items.** None. As with the variant profile, the vocabulary exists; the requirements
are wrong.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `identifiers.coding_system` | equal, or pinned mapping (D7) | unknown | ICD-10-CM vs SNOMED CT needs a mapping and is lossy in both directions |
| `identifiers.coding_version` | equal, or declared release mapping | unknown | Annual releases retire and redefine codes |
| `lifecycle.temporal_meaning` | equal | unknown | A claim line is not a confirmed diagnosis |
| `security.data_use` | DUO subsumption over a normalised set | unknown | `equal` on a set of codes has no subsumption, so a permitted-use set that covers the request still fails |
| `security.consent_scope` | DUO subsumption | unknown | The target's permitted use must subsume the source's declared use |

## What v0.1 gets wrong here

- `identifiers.namespace` is required but neither `coding_system` nor `coding_version` is, so the
  one thing that makes a code interpretable is optional.
- `security.data_use` is compared with `equal`, which carries no DUO subsumption: a target permitting general research use does not accept a source declaring a narrower compatible use. Element order is handled, but only if the caller normalises first: `security.data_use` is a set-like path in `spec/v0.1/rules/normalization.json`, and normalised contracts compare as EXACT regardless of order, while `compare_contracts` on raw contracts returns INCOMPATIBLE from ordering alone.
- Consent and data use are placeholders (`example-consent-scope`) in the normative example.
- `security.deidentification` is not required anywhere, although these are patient records.
- The pre-review then marked deidentification *required* across all 50 security profiles, which is
  the same blanket error in the other direction (erratum E3).

## Fixtures to regenerate

- **positive**: coding system ICD-10-CM with its release, code namespace declared, temporal meaning
  encounter diagnosis, DUO terms for data use and consent scope, de-identification level declared.
- **lossy**: ICD-10-CM to SNOMED CT with a pinned map — approval required, unmapped handling
  declared.
- **contradiction**: same code string under different coding systems; consent scope that does not
  subsume the requested use.
- **unknown**: coding version absent; mapping snapshot absent.
- **policy case**: a consent mismatch must surface as a policy refusal, not as a technical
  INCOMPATIBLE (D12).

## Questions for the reviewer

1. Should consent and data-use comparison sit in the technical layer at all, or entirely in
   workspace policy?
2. Is DUO expressive enough for the consent scopes this standard needs, or is a second vocabulary
   required?
3. Should SNOMED CT be supported given its licensing, and how is a licensed snapshot pinned and
   distributed?
4. Should diagnosis, procedure and medication codes share one coded-clinical-record profile?
5. How should date shifting be declared, so a shifted diagnosis date is not compared to a real one?

## Sources to pin

`duo-2021` (data-use terms and their subsumption); ICD-10-CM's current release from NCHS; the
SNOMED CT edition and version URI if adopted; `bioregistry-2022`. Each needs a SHA-256 at
sign-off, and the SNOMED CT licence terms need recording alongside.

## Tests

No case today. Phase 2 candidates: `security.data_use` must compare the same whether or not the
caller normalises first (today only normalised contracts do); a narrower DUO use must satisfy a
broader permitted use; the same code string under two coding systems must not be a direct match.
