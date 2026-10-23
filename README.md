# Biosimulant model compatibility standard

This repository defines the small, versioned profiles that Biosimulant models
use to say what their ports mean. A profile covers one scientific value or
artifact: for example, an amino-acid sequence, a molecular SMILES string, or a
specific Boltz affinity output.

Biosimulant 0.0.38+ treats these published definitions as historical descriptive metadata.
It does not run their biological payload checkers or grade connections by species or
profile meaning. Structural port checks (types, shapes, formats and declared units)
remain in the runtime independently of this optional catalogue. Existing profile bytes,
versions and digests are retained for reproducibility and historical signed records.

## Standard, profile and model mapping

`standard.yaml` identifies the stable profile format. Each file in `profiles/`
defines one independently versioned profile. A model maps one of its ports to a
profile in `model.yaml`.

```yaml
compatibility:
  standard: biosimulant.model-compatibility
  version: "0"

io:
  inputs:
    - name: protein_sequence
      signal_type: scalar
      dtype: str
      format: sequence
      contract:
        profile: protein.sequence/v1
        species: any
```

The model manifest owns the mapping. Python `SignalSpec` declarations continue
to own the executable port structure. Biosimulant checks that the two agree.

## Profiles included in 0.1.0

- `protein.sequence/v1`
- `chemical.smiles/v1`
- `protein.multiple-sequence-alignment/v1`
- `protein-ligand.complex-structure-mmcif/v1`
- `boltz.binding-probability/v1`
- `boltz.log10-ic50-micromolar/v1`

Inspect them with the Biosimulant CLI:

```bash
biosimulant compatibility profiles
biosimulant compatibility show protein.sequence/v1
```

Validate a model or compare two ports:

```bash
biosimulant compatibility validate ./model.yaml
biosimulant compatibility compare \
  ./producer/model.yaml#outputs.value \
  ./consumer/model.yaml#inputs.value
```

Current runtime checks are structural only. Semantic profile names, species and payload checker declarations are descriptive metadata. Existing definitions and digests remain readable, including references the runtime does not recognize. A signal's declared type, shape, format and unit still must fit the receiving port.

## Adding support to a model

Existing models may retain profile mappings as descriptive metadata. New interfaces need typed ports, shapes, formats and declared units; they do not need a scientific profile or catalogue proposal to run. [CONTRIBUTING.md](CONTRIBUTING.md) describes maintenance of the historical catalogue.

Released profile files are immutable. A scientific or representation change
creates a new profile version; unrelated new profiles do not change existing
references.

## Python package

The package supplies validated catalogue data and deterministic digests. It
does not compare ports or execute checkers.

```python
from biosimulant_model_compatibility_standard import get_profile, profile_digest

profile = get_profile("chemical.smiles/v1")
digest = profile_digest("chemical.smiles/v1")
```

Run the repository checks with:

```bash
python -m pip install -e '.[test]'
pytest
python -m build
```
