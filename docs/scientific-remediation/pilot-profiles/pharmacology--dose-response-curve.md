# Dose Response Curve — `pharmacology/dose-response-curve@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D2, D10, D11.

## Proposed scientific meaning

Responses of a declared biological system measured at a series of declared doses of a declared
agent, after a declared exposure duration. The independent variable is dose. The values are
responses, normally relative to a declared control.

The current profile puts the curve on a `time` axis, which is the substring rule at work
("curve" maps to a time axis). A dose-response curve indexed by time is a different experiment.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity (D3). |
| `representation.kind` | An array kind: the curve is a series of paired dose and response values. |
| `dimensions.axes`, `axes[].name`, `axes[].meaning` | One axis, and it is dose. |
| `dimensions.dose_axis` | Names the dose axis explicitly. |
| `dimensions.axes[].unit` | The dose unit: `mg`, `mg/kg`, `umol/L`, `mg/m2`. Dose per body weight and absolute dose are different quantities. |
| `representation.ordering` | Whether dose order is part of the contract. |
| `measurement.quantity`, `measurement.unit`, `measurement.scale` | What the response is: percent of control, absolute readout, or fraction affected. |
| `measurement.control` | The reference the response is relative to (vehicle, untreated, positive control). A normalised response without its control is uninterpretable. |
| `measurement.response_direction` | Whether increasing response means inhibition or activation; the sign convention changes the meaning of every point. |
| `biological_context.intervention[].agent` | Which compound. |
| `biological_context.intervention[].duration` | Exposure time: a 24-hour and a 72-hour curve for the same agent are different experiments. |
| `biological_context.species` | The system exposed. |

**Conditional**

| Field | Condition |
|---|---|
| `biological_context.intervention[].route`, `intervention[].schedule` | Required for in vivo dosing; route changes exposure. |
| `biological_context.cell_line` | Required for in vitro assays (a Cellosaurus identifier). |
| `biological_context.assay` | Required when the readout method changes the response (viability dye vs ATP luminescence vs imaging). |
| `origin.fit_method`, `uncertainty.fit_quality` | Required when the port carries fitted parameters rather than observed points. |
| `uncertainty.interval`, `uncertainty.confidence_level` | Required when replicate dispersion travels with the points. |
| `measurement.aggregation` | Required when each point is a mean over replicates. |
| `measurement.detection_limits` | Required when the readout saturates or has a floor. |

**Recommended.** `origin.protocol_ref`; `biological_context.medium` and `oxygen` for cell culture;
`biological_context.tissue` for ex vivo systems.

**Deliberately not gating.** `artifact.*` unless exchanged as a file.
`measurement.reference_range`.

**Proposed new items.** A curve-model declaration (four-parameter logistic, Hill slope constrained
or free) for ports that carry fitted parameters, together with the parameter set. `origin.fit_method`
names the method but not the model form.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `dimensions.axes[].unit` (dose) | dimensional conversion (D1) | unknown | `mg` to `mg/kg` needs a body mass — a parameterised transformation, not a conversion |
| `measurement.control` | equal | unknown | Percent-of-vehicle vs percent-of-untreated are different normalisations |
| `measurement.response_direction` | equal | unknown | Inhibition vs activation INCOMPATIBLE |
| `intervention[].duration` | equal, or declared tolerance | unknown | 24 h vs 72 h INCOMPATIBLE |
| `intervention[].agent` | equal, or pinned mapping | unknown | Different agent INCOMPATIBLE |

## What v0.1 gets wrong here

- The axis is `[time]` for a curve whose independent variable is dose.
- `unit: 1` with no control and no response direction: a percent-inhibition curve and a
  percent-viability curve satisfy the same contract and compare as directly compatible.
- No agent, duration or route is required, so two curves for different compounds match.
- The conversion fixture asserts `nM -> uM` (BMCS-SCI-011), which would be plausible for a
  concentration axis and is not what this profile declares.

## Fixtures to regenerate

- **positive**: dose axis in `umol/L` with explicit dose levels, response percent of vehicle,
  direction inhibition, agent identified, duration 72 h, cell line declared, species.
- **parameterised conversion**: `mg` to `mg/kg` with a declared body mass — approval required.
- **lossy**: observed points reduced to fitted parameters — approval required, not reversible.
- **contradiction**: inhibition vs activation; 24 h vs 72 h; different agent.
- **unknown**: control absent; duration absent.

## Questions for the reviewer

1. Should in vivo dose-response and in vitro concentration-response remain separate profiles, given
   they differ mainly in the axis quantity?
2. Should fitted parameters (EC50, Hill slope, top, bottom) be a separate profile from the curve?
3. Is a log-spaced dose axis declared as such, or is that a property of the values?
4. What minimum context makes two viability curves comparable across labs?
5. Should the profile require raw points when fitted parameters are supplied?

## Sources to pin

`iuphar-neubig-2003`; the FDA 2005 guidance on estimating a maximum safe starting dose (body
surface area scaling, for the dose-basis question); `ucum-2.2`; Cellosaurus (Bairoch 2018,
`10.7171/jbt.18-2902-002`) if cell lines are required. Each needs a SHA-256 at sign-off.

## Tests

BMCS-SCI-011; Phase 2 cases for the dose axis and for response-direction mismatch.
