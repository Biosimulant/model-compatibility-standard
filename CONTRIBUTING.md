# Propose a compatibility profile

Add a profile only when an existing profile cannot safely describe a real model
port. A new file format alone may not change the scientific meaning. A new
profile is justified when meaning, measurement scale, transformation or
representation changes what can be interpreted safely.

Use a generic name when independent models exchange genuinely equivalent
information. Use a model-family name when a score or prediction has a
model-specific meaning.

## Pull-request route

1. Open an issue or draft pull request describing the real producer and
   consumer, or another immediate use.
2. Add one file named `<profile.id>.v<version>.yaml` under `profiles/`.
3. Reuse an existing checker when it provides the required value checks.
4. Add package tests for a value that must pass and one that must be blocked.
5. If a new checker is necessary, add its implementation and tests to the
   Biosimulant runtime in the same change set.
6. Run `pytest`, build the wheel, and validate the real model manifest with the
   Biosimulant CLI.
7. Explain the scientific source, intended use and important limitations in
   the pull request.

A proposal must include:

- profile ID, version and plain-language title;
- a precise scientific definition;
- the real producer model and output port;
- the real consumer model and input port, or a clear immediate use;
- signal type, data type, file format, shape and unit where applicable;
- the checker name;
- one accepted example and one example that must be blocked;
- authoritative sources;
- important limitations; and
- whether the profile is generic or model-family-specific.

Example:

```yaml
schema_version: "1"

profile:
  id: example.fraction
  version: "1"
  title: Example bounded fraction

definition: >
  A dimensionless fraction produced and consumed by the named workflow.

representations:
  - signal_type: scalar
    dtypes: [float32, float64]
    unit: "1"

checker: probability
context_fields: []

limitations:
  - This profile does not establish how the fraction was estimated.

sources:
  - title: Source describing the value
    url: https://example.org/source
```

Merging the pull request to `main` is the review record. There is no separate
reviewer file or approval packet. Released profile versions are never edited;
create `v2` if a change alters meaning or accepted representation.

## Email route

If you cannot open a pull request, email the Biosimulant team with the subject
`Compatibility profile proposal: <proposed profile ID>` and copy this template:

```text
Proposed profile ID and version:
Plain-language definition:
Generic or model-family-specific:
Producer model and output port:
Consumer model and input port, or immediate use:
Signal type, dtype, format, shape and unit:
Proposed checker:
Example that should pass:
Example that must be blocked:
Scientific sources:
Important limitations:
Your name and contact information:
```

The Biosimulant team will turn the proposal into a pull request. An email alone
does not add a profile to the released standard.
