# State Trajectory — `simulation/state-trajectory@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D2, D10, D11, D12.

## Proposed scientific meaning

The values of a model's state variables over simulated time: a matrix indexed by time and by state
variable, where each variable has its own identity and unit, produced by a declared model under
declared solver settings.

This is the pilot's test of two things: heterogeneous units inside one container, and the
difference between reproducibility metadata and compatibility requirements. It is also where the
"checksum everything" instinct has to be resisted — a digest matters for a file and for replay, not
for every inline trajectory.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity (D3). |
| `representation.kind` | An array kind: time by state variable. |
| `dimensions.axes`, `axes[].name`, `axes[].meaning` | Which axis is time and which is state variables. |
| `dimensions.time_axis`, `dimensions.axes[].unit` | The time axis and its unit. |
| `dimensions.feature_labels_ref`, `feature_labels_sha256` | The state-variable universe, pinned. Position *i* in a state vector is meaningless without it, and state vectors are routinely reordered between model versions. |
| `representation.ordering` | Whether variable order is part of the contract. |
| `lifecycle.time_origin` | What t=0 means in the simulation. |
| `origin.type` | Simulated. A simulated trajectory must never silently satisfy a port that requires measured data — this is the single most important requirement in the profile. |
| `semantic.model_formalism` | ODE, SDE, agent-based, flux balance: the formalism determines what a state value is and whether trajectories are even comparable. |

**Conditional**

| Field | Condition |
|---|---|
| per-variable units | Required whenever variables carry different units, which is the normal case. `measurement.unit` is a single field, so a heterogeneous state vector cannot declare its units today — see proposed items. |
| `origin.model_digest` | Required when the consumer must know which model produced the trajectory, and always for replay. |
| `origin.parameter_digest` | Required when parameters vary between runs. |
| `origin.solver`, `origin.solver_version`, `origin.absolute_tolerance`, `origin.relative_tolerance` | Required for reproducibility claims. They do **not** gate scientific compatibility on their own: two trajectories from different solvers at adequate tolerance are still the same quantity. |
| `origin.random_seed` | Required for stochastic formalisms, where a trajectory is one realisation and the seed is what makes it reproducible. |
| `lifecycle.sampling` | Required when the output grid is fixed, as distinct from solver-chosen steps. |
| `artifact.format`, `artifact.format_version`, `artifact.sha256` | Required **only** when the trajectory is exchanged as a file, not for inline arrays. |
| `uncertainty.distribution`, `uncertainty.parameters` | Required for ensemble outputs, where each point is a distribution rather than a value. |

**Recommended.** `origin.software`, `origin.software_version`; `origin.generated_at`;
`lifecycle.interpolation` when consumers resample.

**Deliberately not gating.** `biological_context.*` — a trajectory of an abstract model has no
organism; a biologically grounded model should declare context through the domain profile of each
state variable. `security.*` unless the model or parameters are themselves restricted.

**Proposed new items.** Per-feature units and quantity kinds for a heterogeneous state vector. This
is a genuine gap: the catalogue assumes one unit per port, which no real state vector satisfies.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `origin.type` | equal, or an explicit policy allowance | unknown | Simulated offered to a measured-data consumer must not be DIRECT_COMPATIBLE |
| `dimensions.feature_labels_sha256` | equal | unknown | Different state-variable universes need a mapping |
| `dimensions.axes[].unit` (time) | dimensional conversion (D1) | unknown | `ms` to `s` lossless |
| per-variable units | dimensional conversion, per feature | unknown | A mismatch on any variable blocks the whole port |
| `semantic.model_formalism` | equal | unknown | An agent-based population count and an ODE concentration are not the same state |
| solver settings | compare when both declare (D2) | ignore | Informational; must not block on their own |

## What v0.1 gets wrong here

- Only concept, subject, kind, axes and ordering are required: no time unit, no time origin, no
  state-variable identities, and no declaration that the data are simulated.
- `dimensions.axes: [time]` with no axis unit, so the time base is undeclared.
- Nothing distinguishes a trajectory from a measured time series, which is exactly the substitution
  the standard exists to prevent.
- The subject placeholder is `simulation_state_or_configuration`, which carries no meaning.

## Fixtures to regenerate

- **positive**: axes `[time, state_variable]` with a pinned variable list, time unit `s`, origin
  declared, origin type simulated, formalism ODE, per-variable units declared.
- **conversion**: time axis `ms` to `s` lossless.
- **contradiction**: simulated offered where measured is required; different state-variable
  universe; different formalism.
- **unknown**: variable list absent; time unit absent.
- **lossy**: dense solver output resampled onto a coarse output grid — approval required.

## Questions for the reviewer

1. How should per-variable units be declared: a typed feature list, or one port per variable?
2. Should solver identity and tolerances ever gate compatibility, or only reproducibility?
3. Should a stochastic ensemble be this profile with a distribution, or a separate profile?
4. What must a port declare so a consumer can tell a model-generated trajectory from a fitted or
   smoothed one?
5. Should state variables be required to reference the domain profiles of the quantities they
   represent, linking simulation output back to biology?

## Sources to pin

SBML Level 3 (Keating et al. 2020, `10.15252/msb.20199110`) for model and state semantics; SED-ML
(Waltemath et al. 2011, `10.1186/1752-0509-5-198`) for simulation description and reproducibility;
KiSAO for solver identity if adopted; `ucum-2.2`. Each needs a SHA-256 at sign-off.

## Tests

No case today. Phase 2 candidates: a simulated trajectory offered to a measured-data consumer must
not be DIRECT_COMPATIBLE; two different state-variable universes must not match.
