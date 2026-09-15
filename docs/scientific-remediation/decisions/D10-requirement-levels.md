# D10. Requirement levels for candidate items

**Status:** Open. **Owner:** unassigned. **Decided:** — . **Approved by:** —

## Question

How is it decided whether an item is required, conditional, recommended or not gating — and at what
granularity?

## Why it matters

The packets list 240 distinct candidate items, 20 to 79 per profile, with no decisions attached. The
pre-review then assigned one decision per item path across all 650 profiles, and several were
over-broad: `uncertainty.censoring` marked required in 400 packets although its own reason limits it
to time-to-event data; `semantic.ontology_terms` required for all 650; `artifact.sha256` required
wherever an artifact representation is allowed. Those decisions are withdrawn (erratum E3).

Both directions are failures. Too little required, and ports pass while being incomparable. Too
much, and every real coupling returns UNKNOWN and people route around the standard.

## Options

| Option | For | Against |
|---|---|---|
| (a) One decision per item path, globally | Cheap; uniform | Produces exactly the over-broad requirements above |
| (b) One decision per profile | Precise | 650 × up to 79 decisions, unreviewable |
| (c) Profile classes, with per-profile overrides | Tractable and still justified | Classes must be validated before use |

## Recommendation

Option (c). Define classes from the pilot — scalar measurement, feature matrix, sequence and
variant, image volume, event and time-to-event, coded clinical record, simulation trajectory,
community composition — and give each a required and conditional set, each with a justification and
a source. Everything else defaults to declared-but-not-gating. A profile may override its class, and
the override carries its own reason.

## What adopting it changes

- Class definitions in `source/`, with per-profile overrides.
- The pre-review's item table becomes input to this process, never a decision.
- An UNKNOWN-rate measurement on a realistic corpus, before and after, as the check on
  over-requirement.

## Sub-questions

1. Do classes come from the pilot evidence, or are they proposed first and tested against it?
2. How is a conditional's condition expressed so it is machine-checkable?
3. Who may approve an override — the domain owner alone, or a reviewer too?

## Tests

No direct case. The guard against this decision going wrong is the UNKNOWN-rate measurement, not a
unit test.

## Sources to pin

Per item, in the class definition. None globally.

## Decision

_To be recorded._
