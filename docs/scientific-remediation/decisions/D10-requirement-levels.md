# D10. Requirement levels for candidate items

**Status:** Recorded, not implemented: the classes need the pilot. **Owner:** unassigned. **Decided:** — . **Approved by:** —

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

**Option (c) is accepted in principle, and nothing is implemented. The one change that looked
implementable was built, measured and withdrawn.**

This record's own ordering note says why the classes wait: D10 is the decision the pilot exists to
inform. Inventing eight classes and assigning 650 profiles to them ahead of that evidence would
repeat, one level up, the mistake erratum E3 withdrew — a decision applied across hundreds of
profiles that nobody reviewed profile by profile.

**What was tried.** The published schema has always allowed `required`, `conditional`,
`recommended` and `optional`, and the generator emits exactly one of them: every profile document
says `required` and nothing else. The items a profile's own packs carry but the profile does not
require are already computed as `candidate_recommended_items`. Emitting those in the profile
document at `level: "recommended"` would have given the vocabulary a real producer without any
per-profile judgement, since pack membership is authored, reviewed data.

**Why it was withdrawn.** It cost too much for what it added. With a value schema on each entry the
bundle grew from 31.0 MiB to 48.5 MiB, +56.7%. Dropping the schemas — nothing reads them, because
validation and comparison both skip any level but `required` — still left +9.2 MiB, +29.7%, for
42,016 entries of the form `{"path": ..., "level": "recommended"}`. The review packet already
publishes that same list, its schema requires the field, and the pre-review tooling reads it in six
places, so it could not be removed in exchange. The profile document would have been carrying a
second copy of an existing list, at a third again the size of the bundle, that no engine reads.

A distinction worth having does not justify stating it twice. The finding stands as a finding: the
four-level vocabulary is published but has only one producer, and giving it a real one is part of
the class definitions, not a separable change.

**Still open.** The classes, the per-profile overrides, and the machine-checkable form of a
conditional's condition all wait on the pilot. So does the UNKNOWN-rate measurement this record
names as the real guard against over-requirement: measuring it against a realistic corpus needs a
corpus, and the census in `measurements/` runs against generated fixtures, which cannot stand in for
one.
