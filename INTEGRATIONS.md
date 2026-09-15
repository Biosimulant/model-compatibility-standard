# MCP and Agent Skill Integration

The Biosimulant Model Compatibility Standard is the portable data and validation
layer. It does not require an agent, an MCP host, or a hosted API. Python and
TypeScript consumers can validate and compare locally from an exact installed
bundle.

MCP and Agent Skills expose the same standard through agent workflows:

- The Biosimulant Agent Gateway is the authoritative hosted execution surface.
  It enforces authentication, ownership, workspace policy, approval receipts,
  expiry, and digest binding.
- Agent Skills are optional workflow guidance. They do not add tools, grant
  scopes, approve lossy or inferred work, or replace server-side validation.
- An agent must not infer missing biological context merely to turn `UNKNOWN`
  into a passing result.

## OAuth scopes

| Scope | Allows |
|---|---|
| `compatibility:read` | Read the installed standard identity, public profiles, and owned reports or plans |
| `compatibility:compute` | Validate, compare, and prepare a resolution plan |
| `compatibility:approve` | Prepare and create an exact approval receipt for a lossy or inferred plan |

## MCP tools

| Tool | Purpose |
|---|---|
| `compatibility_standard_get` | Return the installed release, bundle digest, counts, and canonical resources |
| `compatibility_profiles_search` | Search the bundled profile catalogue |
| `compatibility_profile_get` | Return one exact immutable profile definition |
| `compatibility_validate` | Validate a manifest, contract, or other standard object |
| `compatibility_compare` | Compare source and target contracts without selecting transformations |
| `compatibility_resolve_prepare` | Prepare an expiring resolution plan, optionally bound to an exact workspace revision |
| `compatibility_report_get` | Read an owned immutable compatibility report |
| `compatibility_plan_get` | Read an owned immutable plan and its lifecycle state |
| `compatibility_approval_prepare` | Prepare a digest-bound approval operation |
| `compatibility_approval_create` | After explicit confirmation, create the exact approval receipt |

## Strict managed-run sequence

1. Read the installed bundle identity and select exact profiles.
2. Validate each opted-in manifest and contract.
3. Compare ports. Keep technical status, workspace policy, and Passport quality
   as separate results.
4. Resolve using only declared, immutable adapter or inference capabilities.
5. If policy requires approval, prepare the exact approval and create the
   receipt only after explicit user confirmation.
6. Pass both `compatibility_plan_id` and `compatibility_plan_digest` to
   `run_prepare`.
7. The server revalidates the bundle, plan content, revision digest, policy,
   expiry, and active receipts when preparing and creating the run.
8. Runtime boundary findings become run evidence; they do not silently mutate
   the contract or become a scientific-quality claim.

The downloadable `biosimulant-model-compatibility` Agent Skill contains this
workflow for supported agent hosts. The general Biosimulant, composition, model
building, runtime-specific, discovery, and publication skills route to it when
compatibility metadata is in scope.
