# Biosimulant model compatibility standard

This repository defines the small, versioned profiles that Biosimulant models
use to say what their ports mean. A profile covers one scientific value or
artifact: for example, an amino-acid sequence, a molecular SMILES string, or a
specific Boltz affinity output.

The runtime uses a profile to check two things:

- whether connected ports describe the same information in the same form; and
- whether a live value satisfies the profile's basic safety checks.

It does not judge model quality, infer missing scientific context, convert
units, or approve a result. Model evidence, provenance, limitations and fitness
for use remain separate responsibilities.

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

The runtime returns `ok`, `warning`, or `blocked`. Profiles are optional on each
port. When only one connected port declares a profile, a structurally valid
connection is allowed with a `PROFILE_PARTIAL` warning: the declared profile
still checks live values, but scientific compatibility is not verified. When
both ports declare profiles, different references, incompatible
representations, missing required context and invalid live values block the
connection. Version 0 does not perform automatic conversion.

This is a two-sided opt-in guarantee. An unprofiled model can integrate with a
profiled model, but only two matching declarations establish profile-verified
compatibility. A consumer may intentionally declare a model-family profile
such as `boltz.binding-probability/v1` even when the consumer is not a Boltz
model. The name describes the value being accepted, not who may consume it.

## Adding support to a model

First inventory the model's scientific inputs and outputs. Leave operational
ports such as run configuration and logs unprofiled. Reuse an existing profile
only when its definition and limitations really describe the port. Add the
top-level standard declaration, map each relevant port, then validate the
manifest and test both accepted and rejected values.

When no profile is accurate, propose one instead of stretching an existing
definition. The complete pull-request and email routes are in
[CONTRIBUTING.md](CONTRIBUTING.md).

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
