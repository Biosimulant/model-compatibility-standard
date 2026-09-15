# Incidence Rate — `epidemiology/incidence-rate@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D5, D10, D12.

## Proposed scientific meaning

The number of new cases of a declared condition per unit of person-time at risk, in a declared
population over a declared observation period. An incidence *rate* has person-time in its
denominator. An incidence *proportion* (risk) and an attack rate are dimensionless proportions, and
belong to different profiles.

This profile is also the pilot's test of the security requirement: it is one of the 25 epidemiology
profiles that require consent and data-use fields, and for published aggregate statistics that
requirement is probably wrong.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity (D3). |
| `representation.kind` | Scalar, or a vector over strata. |
| `semantic.endpoint` | The case definition. Incidence of "influenza" by clinical criteria, by PCR confirmation, and by hospital coding are different numbers. |
| `measurement.quantity` | Incidence rate, explicitly distinct from incidence proportion. |
| `measurement.unit` | Events per person-time, written with an annotation such as `/{person-year}`. `1/s` is dimensionally a rate but carries no person-time basis. |
| `measurement.rate_basis` | The denominator basis: person-years, person-days, or a conventional multiplier such as per 100,000 person-years. |
| `measurement.scale` | `ratio`. |
| `biological_context.population` | Who is at risk. |
| `biological_context.denominator` | The person-time actually accumulated, which is what distinguishes a rate from a count. |
| `lifecycle.observation_period` | The window over which cases were counted. |

**Conditional**

| Field | Condition |
|---|---|
| `measurement.standardization` | Required when the rate is age- or sex-standardised: the standard population is part of the value, and crude and standardised rates must never be compared directly. |
| `biological_context.stratum` | Required for stratified estimates (age band, sex, region). |
| `biological_context.geography` | Required for spatially indexed surveillance. |
| `biological_context.species` | Required only when non-human populations are in scope; for human epidemiology it is a constant and adds nothing. |
| `origin.surveillance_system` | Required when the value comes from a named surveillance system whose case ascertainment defines it. |
| `uncertainty.interval`, `uncertainty.confidence_level` | Required when a confidence interval travels with the estimate. |
| `security.data_use`, `security.consent_scope`, `security.deidentification` | Required **only** for individual-level or small-cell data. For published aggregate rates there is no personal data, and requiring consent fields blocks legitimate reuse of public statistics. |

**Recommended.** `origin.method` (how person-time was computed); `biological_context.cohort`;
`origin.observed_at` for reporting date versus onset date.

**Deliberately not gating.** `measurement.reference_range`. `artifact.*`.
`biological_context.tissue`, `cell_type` and similar laboratory context.

**Proposed new items.** None. The relevant items exist; what is wrong is which are required, which
is exactly the D10 problem.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `measurement.quantity` | equal | unknown | Rate vs proportion INCOMPATIBLE; they have different dimensions |
| `measurement.unit` + `rate_basis` | dimensional conversion (D1) | unknown | Per person-year to per 100,000 person-years lossless |
| `measurement.standardization` | equal | unknown | Crude vs age-standardised INCOMPATIBLE |
| `semantic.endpoint` | equal | unknown | Different case definitions are not comparable |
| `lifecycle.observation_period` | compare when both declare (D2) | ignore | Different windows are context, not contradiction, unless the consumer requires one |

## What v0.1 gets wrong here

- `unit: 1/s` with no person-time basis: dimensionally a rate, scientifically not an incidence rate.
- No case definition, population or denominator is required, so two incidence rates for different
  diseases in different populations compare as directly compatible.
- Consent and data-use fields are required for every epidemiology profile, including aggregate
  statistics, with the placeholder values `example-consent-scope` and `example-data_use`.
- The conversion fixture asserts `nM -> uM` (BMCS-SCI-011).

## Fixtures to regenerate

- **positive**: quantity incidence rate, unit per 100,000 person-years, rate basis declared, case
  definition declared, population and person-time denominator declared, observation period declared,
  no consent fields (aggregate data).
- **conversion**: per person-year to per 100,000 person-years lossless.
- **contradiction**: rate vs proportion; crude vs age-standardised; different case definition.
- **unknown**: denominator absent; case definition absent.
- **policy case**: individual-level data without consent scope must be refused at the policy layer,
  not by the technical comparison (D12).

## Questions for the reviewer

1. Should consent and data-use fields be required at all for aggregate published statistics, or
   only for individual-level records?
2. Should incidence rate, incidence proportion and attack rate be one family with a declared
   quantity, or separate profiles as now?
3. How should the standard population be declared for standardised rates?
4. Is `/{person-year}` an acceptable UCUM annotation, or does the standard need its own denominator
   vocabulary?
5. Should reporting delay and case ascertainment be part of the contract or of quality metadata?

## Sources to pin

`cdc-epi-3ed` (measures of risk: rate versus proportion, person-time); `ucum-2.2` (annotations);
`iso-80000-1-2022`; a standard-population reference (for example the WHO or European standard
population) if standardisation is in scope. Each needs a SHA-256 at sign-off.

## Tests

BMCS-SCI-011; Phase 2 cases for rate-versus-proportion and crude-versus-standardised.
