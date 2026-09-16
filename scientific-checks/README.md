# Scientific guards

Automated conformance tests show that the implementations follow the published
rules. The scientific guards check a narrower question: do the active profiles
produce the scientifically intended result for important examples?

The shared cases are in `v0.1/cases.json`. Python and TypeScript both read that
file, so they cannot silently adopt different scientific expectations:

- `python/tests/test_scientific_checks.py`
- `typescript/test/scientific-checks.test.mjs`

Every active case is a guard and must pass. The initial v0 guards cover:

- an exact match for identical protein-sequence contracts;
- incompatible sequence alphabets;
- required sequence encoding;
- incompatible canonicalisation methods;
- required canonicalisation software version;
- incompatible protein-structure coordinate systems; and
- required protein-structure provenance.

Run both implementations with:

```bash
npm run test:scientific
```

## Adding a guard

A guard must identify the active profile, the scientific reason for the
expectation, the conditions under which it holds, and the expected comparison or
validation outcome. Build the contracts from the profile's generated positive
fixture plus the smallest explicit patch that demonstrates the case.

Supported checks are:

| Check | Purpose |
|---|---|
| `compare` | Compare two contracts and assert the technical or policy result. |
| `validate` | Validate one contract and require an error for an invalid declaration. |
| `resolve` | Exercise an explicitly supplied conversion or inference capability. |

Do not record unresolved scientific questions as passing tests. Keep the profile
at `draft`, document the open question in its review packet, and add a guard only
after the scientific decision is made.
