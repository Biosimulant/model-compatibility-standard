# Scientific checks

These checks protect the scientifically important outcomes of the active
profiles. They answer questions such as: should two sequence alphabets be
treated as incompatible, and should a structure without provenance be rejected?

The cases are stored in `v0.1/cases.json`. Python and TypeScript both run the
same cases:

- `python/tests/test_scientific_checks.py`
- `typescript/test/scientific-checks.test.mjs`

Run them with:

```bash
npm run test:scientific
```

## Add a case

Each case must name the profile, explain the scientific reason for the expected
result, state the conditions under which it holds, and specify the validation,
comparison or resolution outcome.

Use the profile's generated positive fixture as the starting point and change
only the fields needed to show the case.

Do not turn an unresolved scientific question into a passing test. Leave the
profile in `draft`, record the question in its review packet, and add the check
after a scientific decision has been made.

These checks show that implementations preserve recorded decisions. They do not
replace independent scientific review.
