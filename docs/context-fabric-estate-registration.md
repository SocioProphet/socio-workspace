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

## Registration fragment

The initial registration is staged in:

- `manifest/context-fabric.registration.toml`

It is intentionally separate from `manifest/workspace.toml` for the first review so the new entries can be checked before canonical manifest and lock regeneration.

## New entries

- `prophet_workspace`
- `agent_registry`
- `memory_mesh`
- `socioprophet_agent_standards`

## Follow-up after merge

1. Fold the fragment into `manifest/workspace.toml`.
2. Regenerate `manifest/workspace.lock.json`.
3. Add boundary catalog entries.
4. Add dependency-graph edges from `prophet_workspace` to platform, agentplane, agent-registry, memory-mesh, policy-fabric, and mcp-a2a-zero-trust.
5. Add source-exposure review for public context-sharing surfaces.
