# Wave A — physiology, cardiopulmonary-renal, clinical, epidemiology, phenotype, pharmacology

150 profiles. 6 in the pilot. See the [shared brief](README.md) for what every reviewer is asked to
do and what approval means.

## Who is needed

- A **clinical physiologist or physician-scientist** comfortable with measurement conventions:
  measurement sites, device classes, reference ranges, and why an oral and a rectal temperature are
  not the same measurement.
- A **clinical pharmacologist** for dose, exposure and response: dose basis, exposure duration,
  free versus total concentration, and the difference between Kd, Ki and IC50.
- An **epidemiologist** for rates and denominators: person-time, standardisation, case definitions,
  and when aggregate statistics stop being personal data.
- A **clinical data or informatics specialist** for coded records: ICD and SNOMED versioning,
  problem lists versus claims, de-identification and consent.

One person rarely covers all four. Expect three or four reviewers sharing the wave, each taking the
profiles they can speak to.

## Pilot profiles

| Profile | The question it tests |
|---|---|
| [physiology/body-temperature](../pilot-profiles/physiology--body-temperature.md) | Affine units, interval scale, and measurement site |
| [pharmacology/binding-affinity](../pilot-profiles/pharmacology--binding-affinity.md) | Endpoint identity, and a ligand-target pair the contract cannot currently express |
| [pharmacology/dose-response-curve](../pilot-profiles/pharmacology--dose-response-curve.md) | Dose axis, control, response direction |
| [epidemiology/incidence-rate](../pilot-profiles/epidemiology--incidence-rate.md) | Person-time denominators, and whether consent fields belong on aggregate statistics |
| [phenotype/time-to-event](../pilot-profiles/phenotype--time-to-event.md) | Censoring as a genuine requirement, in the one place it is mandatory |
| [clinical/diagnosis-code](../pilot-profiles/clinical--diagnosis-code.md) | Coding system versions, mapping loss, and where governance sits |

## Questions this wave settles for everyone else

1. **When does context stop being context and start gating compatibility?** Measurement site,
   specimen and device class all change the number. Which of them may block a coupling?
2. **Where does governance live?** Consent and data-use mismatches are currently technical
   INCOMPATIBLE results. Should they be policy refusals instead (decision D12)?
3. **Is a requirement that is right for one profile wrong for its neighbours?** Censoring is
   mandatory for time-to-event and meaningless for a blood pressure reading. The answer shapes
   decision D10 for all 650.

## Known defects in this wave's profiles

- Body temperature in Celsius and kelvin is reported INCOMPATIBLE (BMCS-SCI-007), and its positive
  example declares a ratio scale.
- Heart rate in 1/s and per minute is reported INCOMPATIBLE (BMCS-SCI-008).
- Plasma concentration in uM and mol/L is reported INCOMPATIBLE (BMCS-SCI-009), and `uM` is not a
  valid UCUM code.
- Incidence rate is declared in `1/s`, with no person-time basis.
- Glomerular filtration rate is declared in `1/s` on a probability scale.
- Binding affinity is dimensionless with no endpoint, so a Kd and an IC50 satisfy the same contract.
- Every profile here carries the wrong conversion fixture (BMCS-SCI-011).
