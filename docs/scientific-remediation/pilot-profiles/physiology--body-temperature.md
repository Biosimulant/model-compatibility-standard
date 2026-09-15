# Body Temperature — `physiology/body-temperature@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D4, D8.

## Proposed scientific meaning

The temperature of a living body measured at a declared anatomical site. An **absolute**
thermodynamic temperature, on an interval scale when expressed in degrees Celsius. A temperature
*difference* (a rise, a gradient, a set-point offset) is a different quantity and is out of scope
for this profile.

Site matters more than units: an oral, tympanic, axillary, rectal and oesophageal temperature are
not interchangeable, and no unit conversion relates them.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity of the quantity (D3). |
| `representation.kind` | Scalar, or a time series of scalars. |
| `measurement.quantity` | Must resolve to absolute thermodynamic temperature, which excludes differences (D1). |
| `measurement.unit` | `Cel` or `K`. Both are UCUM codes; conversion is affine. |
| `measurement.scale` | `interval`, not `ratio`. Ratios of Celsius values are meaningless: 40 °C is not "twice as warm" as 20 °C. |
| `biological_context.tissue` | The measurement site, as an anatomical term (oral, tympanic, axillary, rectal, oesophageal). This is the field most likely to make two temperatures incomparable. The catalogue has no `body_site` item, so either `tissue` carries the site or a dedicated item is added — see the proposed new items below. |

**Conditional**

| Field | Condition |
|---|---|
| `biological_context.species` | Required when the consumer applies species-specific reference ranges; mouse and human core temperatures differ by several degrees. |
| `lifecycle.time_unit`, `lifecycle.sampling`, `dimensions.axes` | Required when the value is a time series (continuous monitoring). |
| `biological_context.assay` | Required when the device class changes the value: infrared tympanic, contact probe, ingestible pill, implanted telemetry. |
| `uncertainty.interval`, `uncertainty.confidence_level` | Required when an uncertainty travels with the value. |
| `measurement.calibration_ref` | Required for regulated or clinical use, where device calibration is part of the claim. |

**Recommended.** `biological_context.age` and `biological_context.sex` (reference ranges);
`origin.instrument_model`; `lifecycle.observation_period` for continuous monitoring.

**Deliberately not gating.** `measurement.reference_range` — clinically useful, but a normal range is
an interpretation, not a property of the interface; making it gating would block valid couplings
between populations with different ranges. `artifact.*` for the scalar case.

**Proposed new items.** A quantity kind that separates absolute temperature from temperature
difference (D1). Without it the contract cannot say which it carries, and an affine conversion
applied to a difference introduces a 273.15 error.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `measurement.unit` | dimensional conversion with offsets (D1) | unknown | `Cel` vs `K` lossless for absolute values; for differences, factor 1 and no offset |
| `measurement.scale` | equal | unknown | interval vs ratio is a declaration error, not a conversion |
| `biological_context.body_site` | equal, or subsumption within one site hierarchy | unknown | Oral vs rectal INCOMPATIBLE — there is no conversion, only a clinical adjustment that is an inference |
| `biological_context.species` | subsumption (D5) | unknown | Contradiction for a species-specific port |

## What v0.1 gets wrong here

- `Cel` vs `K` returns INCOMPATIBLE (BMCS-SCI-007) because the conversion table holds only three
  molar concentration rows and no affine conversion at all.
- The positive fixture declares `scale: ratio`, which licenses arithmetic that Celsius does not
  support.
- The conversion fixture asserts `nM -> uM` for a temperature (BMCS-SCI-011).
- No site is required, so two temperatures from different sites compare as directly compatible.

## Fixtures to regenerate

- **positive**: `unit: Cel`, `scale: interval`, site oral, species `NCBITaxon:9606`.
- **conversion**: `Cel` to `K`, lossless, offset 273.15, flagged as affine so a future difference
  quantity cannot reuse it.
- **contradiction**: oral vs rectal site INCOMPATIBLE; `Cel` vs `mm[Hg]` INCOMPATIBLE.
- **unknown**: site absent on either side.
- **lossy or inference**: a site-adjusted estimate (axillary corrected to core) must surface as an
  inference requiring approval, never as a conversion.

## Questions for the reviewer

1. Which site vocabulary: UBERON terms, SNOMED CT, or a short controlled list? A short list is
   implementable now; UBERON composes better with the rest of the standard.
2. Should continuous monitoring be this profile with a time axis, or a separate time-series profile?
3. Is `interval` the right scale value, or does the standard need to say "interval with a defined
   zero offset" to keep kelvin and Celsius distinguishable?
4. Must device class be required rather than conditional for clinical use?
5. Should species be required outright here, given how different normal ranges are?

## Sources to pin

`si-brochure-9` (kelvin, Celsius, and the 273.15 relation); `ucum-2.2` (`Cel`, `K`);
`stevens-1946` (interval vs ratio); `vim-jcgm-200-2012`. A clinical thermometry standard
(ISO 80601-2-56 for clinical thermometers) should be added by the reviewer if clinical use is in
scope. Each needs a SHA-256 at sign-off.

## Tests

BMCS-SCI-007, BMCS-SCI-011, BMCS-SCI-013.
