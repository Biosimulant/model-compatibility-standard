# Wave D — chemical, imaging, spatial, neuroscience, simulation, core

150 profiles. 6 in the pilot. See the [shared brief](README.md) for what every reviewer is asked to
do and what approval means.

## Who is needed

- A **cheminformatician** for molecular identity: relative molecular mass versus molar mass, salt
  forms, isotopes, structure hashes.
- A **medical imaging physicist or radiologist** for image volumes: voxel geometry, orientation
  conventions, Hounsfield units, and what makes a derived measurement comparable.
- A **neurophysiologist** for electrophysiology: unit identity, counting windows, sampling, and
  what spike sorting does to provenance.
- A **computational modeller** for simulation output: formalisms, solver settings, reproducibility,
  and the line between a measured and a generated value.
- A **metrologist or standards-minded engineer** for the core profiles, which everything else
  inherits from.

## Pilot profiles

| Profile | The question it tests |
|---|---|
| [core/scalar-quantity](../pilot-profiles/core--scalar-quantity.md) | The base case: what it takes to exchange one number safely |
| [core/regular-time-series](../pilot-profiles/core--regular-time-series.md) | Value unit against axis unit; sampling regime |
| [chemical/molecular-weight](../pilot-profiles/chemical--molecular-weight.md) | Two quantities that always print the same number |
| [imaging/ct-volume](../pilot-profiles/imaging--ct-volume.md) | Three-dimensional geometry, and a name that means two different things |
| [neuroscience/firing-rate](../pilot-profiles/neuroscience--firing-rate.md) | The counting window as part of the quantity |
| [simulation/state-trajectory](../pilot-profiles/simulation--state-trajectory.md) | Heterogeneous units in one container; simulated versus measured |

## Questions this wave settles for everyone else

1. **Is dimension enough to identify a quantity?** Frequency and radioactivity are both 1/s; torque
   and energy are both N·m. If not, the quantity-kind registry in decision D1 is mandatory rather
   than optional.
2. **How does one port carry many units?** A state vector mixes concentrations, counts and voltages.
   The catalogue assumes one unit per port, which no real trajectory satisfies.
3. **Must a simulated value announce itself?** The standard's own guidance says inference must never
   silently turn UNKNOWN into a pass. The same principle at the contract level is BMCS-SCI-015.
4. **Should core profiles be matchable, or only extended?** `extends` exists and is unused
   everywhere.

## Known defects in this wave's profiles

- A value in mg and a value in s compare as DIRECT_COMPATIBLE under `core/scalar-quantity`
  (BMCS-SCI-003), which also permits `matrix`, `tensor` and `table` representations.
- A firing rate converts from nM to uM as a lossless conversion (BMCS-SCI-004), and a firing rate
  declared in kg passes validation (BMCS-SCI-005).
- A simulated heart rate satisfies a port requiring measured data (BMCS-SCI-015).
- CT volumes declare voxel values in millilitres, on two spatial axes.
- Molecular weight is dimensionless with no compound identifier and no quantity distinction.
- Time series declare the time unit as the unit of their values.
- Local field potentials get image axes; stroke volume and volume of distribution get spatial axes.
