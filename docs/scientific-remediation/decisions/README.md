# Design decisions

Twelve decisions block Phase 1 of the [remediation plan](../REMEDIATION_PLAN.md). Each has a page
here with the question, the options, a drafted recommendation, what adopting it changes, and the
tests it settles. Every page is **Open** and needs a named owner.

A page is finished when it records the decision, who approved it, and the sources pinned by
SHA-256 behind it. Then the cases it settles move from defect to guard in
[`scientific-checks/v0.1/cases.json`](../../../scientific-checks/v0.1/cases.json), in the same
change that implements it.

| Decision | Question | Settles |
|---|---|---|
| [D1](D1-units-and-quantity-kinds.md) | How are units validated, compared and bound to quantities? | SCI-003 to 009, 011, 012 |
| [D2](D2-optional-field-comparison.md) | Are fields both ports declare but the profile does not require compared? | SCI-001, 002, 003, 014, 015 |
| [D3](D3-concept-identity.md) | What carries a port's scientific meaning? | S1 |
| [D4](D4-context-vocabulary.md) | Should subject and biological context be controlled terms? | S2 |
| [D5](D5-species-and-organisms.md) | What does a species field mean, and what is "any"? | SCI-010 |
| [D6](D6-representation-equivalence.md) | When is a re-encoding lossless? | SCI-104 |
| [D7](D7-identifier-mapping.md) | When is an identifier mapping lossless? | SCI-002, 014 |
| [D8](D8-scale-and-transform.md) | How are measurement level, value domain and transform separated? | SCI-013 |
| [D9](D9-fixture-generation.md) | Where do generated fixture values come from? | SCI-011, 012, 013, 107 |
| [D10](D10-requirement-levels.md) | How is each item's requirement level decided? | E3 |
| [D11](D11-transformation-statuses.md) | What evidence must lossy and inferred conversions carry? | S9 |
| [D12](D12-result-layering.md) | Where do technical status, policy and quality separate? | SCI-015, 108 |

## Order

D1, D2 and D9 unblock the most tests and should be decided first: together they cover eleven of the
fifteen open defects. D3, D4 and D5 depend on snapshot infrastructure that does not exist yet, so
they need a build decision as well as a scientific one. D10 depends on the pilot profiles, because
it is the decision the pilot exists to inform.
