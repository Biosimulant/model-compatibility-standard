# Changelog

## Unreleased reset

- Retired the unreleased standalone compatibility specification.
- Removed the profile catalogue, generated schemas and bundles, dual-language
  implementations, generators, locks, plans and release process.
- Moved compatibility checks into the `biosimulant` Python runtime so checks run
  on real ports and values.
- Replaced profiles with small port facts and registered Python checkers.

No public standard version was released, so there is no migration guarantee for
the removed prototype.
