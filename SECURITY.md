# Security

Please report security problems privately to `security@biosimulant.com` instead
of opening a public issue.

## What the reference validators do

- They only read schemas and profiles from the installed package. They never
  download a `$ref`, a profile or any other URL.
- Comparison rules are data. A profile can't run code, templates, shell
  commands, Python or JavaScript.
- `Bundle.verify_integrity()` in Python and `Bundle.verifyIntegrity()` in
  TypeScript check every installed file's size and sha256, as well as the bundle
  manifest's own digest.
- Both implementations reject excessive document size, nesting, node count,
  string size, array size, object size, profile references and comparison rules
  using the same defaults. Applications may select stricter limits.
- The `pattern` operator accepts a deliberately small, bounded regular-expression
  subset and rejects lookarounds, backreferences and stacked quantifiers.

## Service responsibilities

Services must still enforce request-body limits, authentication, tenant-aware
cache keys, rate limits, execution timeouts and resolver concurrency. Library
limits are defense in depth, not a replacement for service controls.

## Services built on this standard

Keep private contracts, reports and plans visible only to their owner or
workspace.
