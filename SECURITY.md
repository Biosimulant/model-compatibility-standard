# Security

Report security issues privately to `security@biosimulant.com`.

The reference validators do not resolve arbitrary network references. Only
objects present in a locally installed, digest-verified bundle are eligible for
resolution. Rules are declarative data and cannot invoke code, templates, shell
commands, Python, or JavaScript.

Implementations must bound document size, nesting, reference count, rule count,
and graph search. Private contracts and derived reports must remain scoped to
their owner or workspace.
