# Security

Please report security problems privately to `security@biosimulant.com` instead
of opening a public issue.

## What the reference validators do

- They only read schemas and profiles from the installed package. They never
  download a `$ref`, a profile or any other URL.
- Comparison rules are data. A profile can't run code, templates, shell
  commands, Python or JavaScript.

## What they don't do yet

- They don't check installed files against the sha256 values in
  `spec/v0.1/bundle.manifest.json`. In a source checkout,
  `python3 scripts/build_standard.py --check` confirms the files match what the
  build produces.
- They don't limit document size, nesting depth, or the number of references or
  rules. Only the Python resolver limits its search (see `ResolutionLimits`).

If you run the validators on untrusted input, enforce your own size and time
limits around them.

## Services built on this standard

Keep private contracts, reports and plans visible only to their owner or
workspace.
