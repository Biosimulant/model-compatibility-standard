# Compatibility census, 2026-09-15

650 profiles, 5775 comparisons, bundle `sha256:6ada5920b218...`.

**UNKNOWN 32.5%** &middot; INCOMPATIBLE 46.9% &middot; EXACT 11.3% &middot; DIRECT_COMPATIBLE 0.0%

| Scenario | Statuses | What it should be |
|---|---|---|
| `identical` | EXACT 650 | The same contract on both ports. Anything but EXACT is a bug. |
| `required-missing-source` | UNKNOWN 650 | A required field absent from the source. Absent evidence must be UNKNOWN. |
| `required-missing-target` | UNKNOWN 650 | The same field absent from the target instead. Must behave the same way. |
| `required-value-differs` | INCOMPATIBLE 650 | A required field with a different value on each side. Should be INCOMPATIBLE. |
| `unit-mismatch` | INCOMPATIBLE 650 | Both ports declare measurement.unit, mg against s. Different dimensions, so INCOMPATIBLE. |
| `unit-convertible` | LOSSLESS_CONVERSION_AVAILABLE 543, INCOMPATIBLE 107 | Both ports declare measurement.unit, g against kg. Same quantity, so a lossless conversion. |
| `origin-mismatch` | INCOMPATIBLE 650 | Both ports declare origin.type, simulated against measured. Must not be a silent match. |
| `namespace-mismatch` | INCOMPATIBLE 650 | Both ports declare an identifier namespace, ensembl.gene against hgnc.symbol. |
| `species-any` | UNKNOWN 575, NOT_APPLICABLE 75 | The source declares species 'any' against a specific target. Absent evidence, not contradiction. |

## Change since 2026-09-15

- `unit-mismatch`: DIRECT_COMPATIBLE 526 -> 0, INCOMPATIBLE 124 -> 650
- `unit-convertible`: DIRECT_COMPATIBLE 526 -> 0, INCOMPATIBLE 124 -> 107, LOSSLESS_CONVERSION_AVAILABLE 0 -> 543
- `origin-mismatch`: DIRECT_COMPATIBLE 650 -> 0, INCOMPATIBLE 0 -> 650
- `namespace-mismatch`: DIRECT_COMPATIBLE 552 -> 0, INCOMPATIBLE 98 -> 650
- `species-any`: INCOMPATIBLE 575 -> 0, UNKNOWN 0 -> 575
