# Workspace Context Fabric estate registration

## Purpose

This note records the first Sociosphere topology registration for Workspace Context Fabric.

The fabric spans several repositories, but no repository loses its boundary:

- `prophet-workspace` owns workspace product/domain contracts.
- `prophet-platform` owns runtime services, contracts, storage, and deployment.
- `agentplane` owns governed execution evidence.
- `agent-registry` owns agent identity, sessions, grants, and revocation references.
- `memory-mesh` owns recall services, context packs, and review-based promotion.
- `socioprophet-agent-standards` owns profile, compatibility, and conformance overlays.
- `policy-fabric` owns policy decision surfaces.
- `mcp-a2a-zero-trust` owns mediated provider/tool/agent/interface grants.

## Canonical registration

The first registration was staged in:

- `manifest/context-fabric.registration.toml`

It has now been folded into:

- `manifest/workspace.toml`
- `manifest/workspace.lock.json`

## Registered entries

- `prophet_workspace`
- `agent_registry`
- `memory_mesh`
- `socioprophet_agent_standards`

## Governance artifacts

- `docs/governance/workspace-context-fabric-boundary-map.v0.1.json`
- `docs/governance/workspace-context-fabric-source-exposure-review.v0.1.md`
- `tools/validate_workspace_context_fabric_governance.py`
- `.github/workflows/workspace-context-fabric-governance.yml`

## Completion state

- Fold the fragment into `manifest/workspace.toml`: complete.
- Regenerate `manifest/workspace.lock.json`: complete.
- Add boundary catalog entries: complete via `workspace-context-fabric-boundary-map.v0.1.json`.
- Add dependency-graph edges from `prophet_workspace` to platform, agentplane, agent-registry, memory-mesh, policy-fabric, and mcp-a2a-zero-trust: complete in the boundary map.
- Add source-exposure review for public context-sharing surfaces: complete.

## Remaining future work

The current lock uses `manifest_declared_refs_only`. A future network-aware materializer may add live commit SHA resolution, but that is outside this registration tranche.
