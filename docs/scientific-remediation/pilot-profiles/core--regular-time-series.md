# Regular Time Series — `core/regular-time-series@0.1`

**Status:** prepared for qualified review, not approved. **Reviewer:** unassigned.
**Drafted:** 15 September 2026, with AI assistance. **Decisions:** D1, D2, D6, D8, D11.

## Proposed scientific meaning

Values of one declared quantity sampled along a single time axis at a fixed interval, with a
declared time origin. The values carry their own quantity and unit; the axis carries the time unit
and the sampling interval. Two of them are exchangeable only when the values mean the same thing
and the sampling regimes are compatible.

## What a port must declare

**Required**

| Field | Why, for this profile |
|---|---|
| `semantic.concept` | Identity (D3). |
| `representation.kind` | An array kind. `scalar` is currently allowed, which contradicts a series. |
| `dimensions.axes`, `dimensions.axes[].name`, `dimensions.axes[].meaning` | Which axis is time, and what the others index. |
| `dimensions.axes[].unit` | The time unit of the axis (`s`, `ms`, `d`). Distinct from the unit of the values. |
| `dimensions.time_axis` | Names the time axis explicitly for multi-axis series (time × channel). |
| `representation.ordering` | A series whose sample order is not defined cannot be aligned. |
| `measurement.quantity`, `measurement.unit`, `measurement.scale` | What the sampled values are. Today `unit: s` describes the axis, so the values have no declared unit at all. |
| `lifecycle.sampling` | The fixed interval. It is what makes this profile "regular", and nothing requires it today. |
| `lifecycle.time_origin` | What t=0 means: acquisition start, stimulus onset, birth, dose. |
| `lifecycle.temporal_meaning` | Instantaneous samples, interval averages and cumulative totals are different quantities on identical axes. |

**Conditional**

| Field | Condition |
|---|---|
| `uncertainty.missingness` | Required when gaps are possible: a regular series with dropouts must say whether a gap is a missing sample or a zero. |
| `lifecycle.interpolation` | Required when the consumer may resample; states what interpolation the producer considers valid. |
| `dimensions.axes[].size` | Required when the length is fixed by contract rather than by data. |
| `measurement.aggregation` | Required when each sample summarises a window (mean, max, sum). |

**Recommended.** `origin.type`; `origin.instrument`; `uncertainty.quality_flags` per sample.

**Deliberately not gating.** `biological_context.*` — core structure, not biology; a domain time
series profile adds context. `artifact.*` unless the series is exchanged as a file, in which case
the artifact profile applies.

**Proposed new items.** None beyond the quantity-kind registry (D1) and the transform vocabulary
(D8); a log-scaled series must be able to say so.

## Comparison rules

| Field | Operator | Missing | Outcome |
|---|---|---|---|
| `measurement.unit` | dimensional conversion (D1) | unknown | Values convert if the quantity kinds match |
| `dimensions.axes[].unit` | dimensional conversion | unknown | `ms` vs `s` axis lossless |
| `lifecycle.sampling` | equal, then declared tolerance | unknown | 1 kHz vs 1 Hz is not a conversion: downsampling is lossy, upsampling is inference (D11) |
| `lifecycle.temporal_meaning` | equal | unknown | Instantaneous vs interval mean INCOMPATIBLE, unless a declared aggregation transformation applies in one direction only |
| `lifecycle.time_origin` | equal | unknown | Different origins shift every timestamp |

## What v0.1 gets wrong here

- `measurement.unit: s` is the axis unit used as the value unit, so the values are undeclared
  (BMCS-SCI-011 flags the conversion fixture built on it).
- The conversion fixture asserts `nM -> uM` for a time series.
- Nothing distinguishes this profile from `core/irregular-time-series`: both require the same
  fields, and neither requires a sampling regime.
- `scalar` is an allowed representation for a series.

## Fixtures to regenerate

- **positive**: axes `[time]` with `unit: s`, sampling 0.001 s, origin acquisition start,
  values quantity with `unit: mV`, `scale: ratio`, temporal meaning instantaneous.
- **conversion**: axis `ms` to `s` lossless.
- **lossy**: 1 kHz offered to a port requiring 100 Hz — decimation, approval required.
- **inference**: 100 Hz offered to a port requiring 1 kHz — interpolation, approval required.
- **contradiction**: instantaneous vs interval-mean; different time origin.
- **unknown**: sampling absent; temporal meaning absent.

## Questions for the reviewer

1. Should regular and irregular series be one profile with a declared sampling regime, or stay two?
2. Is a single tolerance on sampling interval enough for jittered acquisition clocks?
3. Should multi-channel series live here, or in a matrix profile with a time axis?
4. Is calendar time (with time zones and leap seconds) in scope, or only elapsed time?

## Sources to pin

`ucum-2.2` (time units); `vim-jcgm-200-2012`; `nwb-2022` and `bids-ieeg-2019` (sampling rate, start
time and channel conventions in practice). Each needs a SHA-256 at sign-off.

## Tests

BMCS-SCI-011; new cases for sampling mismatch and axis-unit conversion once D1 lands.
