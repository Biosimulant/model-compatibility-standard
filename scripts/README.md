# Repository scripts

This directory contains supported build and verification scripts:

- `build_standard.py` builds or checks the generated specification.
- `build_ucum_table.py` rebuilds the vendored UCUM unit table.
- `build_browser_data.mjs` prepares the browser-safe TypeScript bundle.
- `check_cross_language.mjs` checks that Python and TypeScript return the same
  canonical results.

These scripts are part of the repository workflow and are called by package
commands or tests. Keep one-off investigations, data checks and migration
helpers in the repository's ignored `.scratch/` directory. Delete them when the
work is finished rather than turning `scripts/` into an archive.
