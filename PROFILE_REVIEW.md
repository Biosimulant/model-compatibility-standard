# Profile review protocol

Executable conformance and scientific review are separate gates.

A profile may be marked `reviewed` only when it has:

- profile-specific semantic, representation, identifier, measurement, context, temporal, origin, uncertainty, and artifact decisions where applicable;
- primary or authoritative sources that support those decisions;
- a named scientific reviewer who is independent of the schema author;
- positive, contradiction, missing-evidence, and relevant transformation fixtures;
- documented intended-use boundaries and non-claims;
- schema review confirming that rules use only allowlisted operators;
- a review date and a domain owner responsible for future deprecation decisions.

Automated fixture success proves validator behavior. It does not prove biological correctness. The alpha compiler therefore preserves the imported catalogue’s actual review status and sets `release_eligible` to false until evidence-backed review is complete.
