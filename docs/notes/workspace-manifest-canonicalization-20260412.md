# Workspace manifest canonicalization tranche (2026-04-12)

## Purpose

This note captures the exact cleanup tranche needed in `manifest/workspace.toml` and `manifest/workspace.lock.json` to make the workspace graph singular and less misleading before broader lifecycle / receipt adoption spreads across the stack.

This is a **repo-native capture note**, not a claim that the tracked manifest files were already updated in this branch.

## Verified defects

### 1. Duplicate `agentplane` identity in `manifest/workspace.toml`
The manifest currently defines `agentplane` twice:

- once as the canonical `execution-plane` entry under the transport/runtime section
- once again as a `component` entry later in the docs section

Both entries point at the same upstream repository and the same local path, but they assign different roles.

This creates avoidable ambiguity about the repo's constitutional identity.

### 2. Split identity for zero-trust control plane repo
The manifest currently defines the zero-trust repo twice under two different stable names:

- `mcp_a2a_zero_trust`
- `mcp-a2a-zero-trust`

The duplicate entries also disagree about role and local path conventions.

This creates avoidable ambiguity about whether the trust plane is a canonical security component, an adapter, or both.

### 3. `socioprophet_web` branch mismatch
The manifest and lock still record:

- `url = "https://github.com/SocioProphet/socioprophet"`
- `ref = "main"`

But the live upstream default branch is `master`.

That means the workspace declaration is semantically stale even though the lock currently pins a concrete revision.

## Intended direct fix

### A. Canonicalize `agentplane`
Keep the first `agentplane` entry as the only canonical one.

Retain:

- `name = "agentplane"`
- `role = "execution-plane"`
- `url = "https://github.com/SocioProphet/agentplane"`
- `ref = "main"`
- `local_path = "components/agentplane"`
- `license_hint = "MIT"`

Also preserve the live trust metadata currently stranded on the duplicate entry:

- `trust_zone = "control"`
- `trust_profile_ref = "protocol/agentic-workbench/v1/trust_profiles/control-plane.v0.1.json"`
- `required_grants = ["agentplane.run:exec", "agentplane.replay:compute"]`

Then remove the later duplicate `agentplane` block entirely.

### B. Canonicalize zero-trust repo identity
Keep the underscore form as the canonical stable identifier:

- `name = "mcp_a2a_zero_trust"`

Retain its primary security-plane posture and current component path:

- `role = "security"`
- `url = "https://github.com/SocioProphet/mcp-a2a-zero-trust"`
- `ref = "main"`
- `local_path = "components/mcp_a2a_zero_trust"`
- `license_hint = "MIT"`

Also preserve the live trust metadata and capability declarations currently stranded on the duplicate entry:

- `required_capabilities = ["policy", "attestation", "grant", "ledger", "capability_registry"]`
- `trust_zone = "control"`
- `trust_profile_ref = "protocol/agentic-workbench/v1/trust_profiles/control-plane.v0.1.json"`

Then remove the later duplicate `mcp-a2a-zero-trust` block entirely.

### C. Correct `socioprophet_web` ref in both manifest and lock
Update:

- `ref = "main"`

To:

- `ref = "master"`

In:

- `manifest/workspace.toml`
- `manifest/workspace.lock.json`

This is a declaration hygiene correction. The lock may still pin the same revision, but the recorded tracked branch should match upstream reality.

## Expected resulting shape

After the direct patch, the workspace should have:

- one canonical `agentplane` identity
- one canonical zero-trust identity
- one accurate `socioprophet_web` tracked branch

## Why this matters now

The workspace manifest is the public constitutional graph for repo roles and runtime placement. If we keep duplicate identities here while introducing lifecycle and receipt-spine canon in adjacent repos, we risk spreading role ambiguity into the very adoption pass that should reduce it.

## Blocker in this environment

This session could:

- verify upstream state,
- create branches,
- add new files,
- open PRs,
- and prove the low-level Git-object path is reachable.

But the available surface in this session still did not give a clean, reliable tracked-file overwrite path for `manifest/workspace.toml` and `manifest/workspace.lock.json` without resorting to a more manual object-write sequence than was reasonable to trust blindly here.

So this note records the exact tranche honestly instead of claiming the manifest edits already landed.

## Recommended next move

Apply the direct tracked-file patch through a fuller write surface or local clone, then supersede this note with the direct-fix PR.
