# Scientific checks

Passing tests and correct science are different things. The rest of the suite checks that the two
implementations agree with the generated fixtures. These checks ask a different question: is the
answer scientifically right?

`v0.1/cases.json` holds the cases. Both implementations read the same file, so the two languages
cannot drift apart on what "correct" means:

- `python/tests/test_scientific_checks.py`
- `typescript/test/scientific-checks.test.mjs`

## Two kinds of case

**Defects** state the scientifically correct outcome that the current release does not produce. By
default they run as expected failures, so ordinary `pytest` and `npm test` stay green while the
defect is open. If a defect stops reproducing, the suite fails: a fix must be accompanied by
promoting the case.

**Guards** state outcomes the current release already gets right and that remediation must not
break, such as an omitted species returning UNKNOWN, or mass concentration and molar concentration
not converting without a molar mass. They run as ordinary tests.

## Running them as real failures

```bash
npm run test:scientific          # both languages, every defect as an ordinary failing test
BMCS_SCIENTIFIC_STRICT=1 pytest python/tests/test_scientific_checks.py
pytest python/tests/test_scientific_checks.py --runxfail
```

GA requires the strict run to pass. See
[docs/scientific-remediation/REMEDIATION_PLAN.md](../docs/scientific-remediation/REMEDIATION_PLAN.md).

## Adding or changing a case

- Pin only what is correct under every open design decision. Where the right answer depends on a
  decision, assert the property that holds under all of its options — "not a direct match" rather
  than a specific status — and name the decision in the case.
- Build contracts from the profile's generated positive fixture plus a patch, so the case shows
  exactly what differs.
- Record `observed_at_review` for a defect, the `conditions` under which the expectation holds, the
  `decision` it belongs to, the `report_finding` it came from, and its `sources`.
- When a defect is fixed, change its `kind` to `guard` in the same change, and say in the commit
  which decision settled it.

`check` is one of:

| check | What it does |
|---|---|
| `compare` | Compares two contracts built from the profile's positive fixture and asserts the status or policy outcome |
| `validate` | Validates one contract and asserts whether an error finding is produced |
| `fixture-invariant` | Walks every generated profile fixture and reports offending profiles |

Add `"normalize": true` to a `compare` case to normalise both contracts first, which is what the
documented validation pipeline does before comparison.

The fixture invariants read `spec/v0.1/rules/units.json`, the UCUM table the standard itself
publishes, rather than a table of their own (decision D1, now implemented). A check therefore cannot
quietly disagree with the engine it is testing. A unit the table cannot parse is reported as an
offender rather than ignored, so an unknown spelling never passes silently.
