# Model compatibility

This repository held an unreleased prototype for a standalone Biosimulant
compatibility standard. The prototype has been retired before launch.

The useful part now lives in the `biosimulant` Python runtime, where it can check
the model ports and the values that actually cross a wire. We removed the profile
catalogue, generated schemas, rule language, lock files, TypeScript mirror and
release machinery because none had an external adopter and all duplicated the
runtime's job.

## Where to work now

- Runtime code: [`biosim.compatibility`](https://github.com/Biosimulant/biosimulant/blob/main/src/biosim/compatibility.py)
- Model builder guide: [Model compatibility](https://docs.biosimulant.com/standards/model-compatibility)
- Manifest reference: [`model.yaml`](https://docs.biosimulant.com/references/model-manifest)

The current design is intentionally small. A port uses the existing
`SignalSpec` fields for its shape, format and unit, plus this optional semantic
contract:

```yaml
contract:
  type: chemical.smiles
  species: any
```

Only `type` is required when a contract is present. `species` and
`identifier_namespace` are included only when they are meaningful for that port.

The runtime returns one of three outcomes: `ok`, `warning`, or `blocked`.
Structural and semantic checks run when models are connected. Type-specific
checks run again on the values used during a run.

## Adding a new kind of data

Do not add a catalogue entry here. First try one of the types already available:

```bash
biosimulant compatibility types
```

If none describes the data, register a small namespaced Python checker in the
model package and test it against real input and output examples. If the check
is broadly useful, propose it to `biosim` with its tests and model-builder
documentation. The [extension guide](https://docs.biosimulant.com/standards/model-compatibility/add-a-type)
contains the complete workflow.

This repository remains available as the decision record and to avoid breaking
old links. It no longer publishes a package or specification.
