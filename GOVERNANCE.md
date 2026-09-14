# Governance

BioSimulant maintains this standard in public. Specification releases use
semantic versioning; every released schema, profile, rule bundle, and fixture
is immutable and content-addressed.

Technical review establishes conformance. Domain review establishes that a
profile faithfully describes its bounded biological representation. Neither
review certifies a model's general scientific validity or fitness for clinical
use.

The `review_status` field is normative:

- `candidate`: machine-readable proposal without complete review evidence;
- `draft`: actively reviewed but not approved for GA;
- `reviewed`: approved by the named domain reviewer;
- `deprecated`: retained for existing locks but not recommended for new work;
- `revoked`: excluded from new plans because of a material defect.
