# Contributing

Compatibility changes are made in the
[`Biosimulant/biosimulant`](https://github.com/Biosimulant/biosimulant) repository, not in
this retired prototype.

A proposed built-in type should include:

- a real producer-to-consumer model connection;
- the small port declarations used by both models;
- a Python checker that inspects a real example value where possible;
- tests for an accepted value, a warning, and a blocked value; and
- a short addition to the model-builder guide.

Model-specific checks do not need to become built-ins. Use a namespaced type and
register the checker from the model package. This lets a model ship safely while
the shared runtime remains small.

See the [extension guide](https://docs.biosimulant.com/standards/model-compatibility/add-a-type)
for code and pull-request instructions.
