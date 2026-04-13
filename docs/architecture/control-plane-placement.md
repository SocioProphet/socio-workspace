# Control-plane placement

This document records the canonical upstream placement for the Matrix / MCP / A2A / capability-lease control-plane slice.

It is intentionally **placement-first** and **implementation-light**.

The goal is to stop repo-boundary drift before runtime code, schemas, and policy bundles land across the SocioProphet estate.

## Canonical split

### `sociosphere`

`Sociosphere` is the **workspace controller**.

It owns:
- workspace composition
- workspace manifest + lock
- canonical ownership registry
- trust profile references
- policy-pack references
- cross-repo placement guidance

It does **not** own downstream feature implementation for the control plane.

### `prophet-platform-standards`

This repo is the canonical home for **normative control-plane standards**.

It should carry:
- Matrix dual-estate ADRs
- capability-lease and approval ADRs
- moderation / publication ADRs
- MCP / A2A control-plane operating guidance

### `socioprophet-standards-storage`

This repo is the canonical home for **portable control-plane schemas and event contracts**.

It should carry:
- capability-lease schema
- lease issued / denied / revoked events
- Matrix room-pivot events
- moderation decision events
- provenance overlays for control-plane actions

### `mcp-a2a-zero-trust`

This repo is the canonical home for **zero-trust enforcement and registry implementation**.

It should carry:
- capability broker logic
- capability registry mechanics
- grant / ledger paths
- attestation hooks
- policy enforcement bundles
- public and extended agent-card examples

### `prophet-platform`

This repo is the canonical home for the **deployable runtime and deployment topology**.

It should carry:
- public Matrix edge runtime
- private Matrix core runtime
- Keycloak deployment profile
- capability broker runtime wiring
- MCP gateway runtime wiring
- A2A registry runtime wiring
- control-plane infra / k8s topology

### `policy-fabric`

`Policy Fabric` is a **first-class downstream consumer**, not the source of truth for the generic control plane.

It should adopt:
- capability-lease semantics
- approval / replay linkage
- broker and registry integration

## Recommended namespace additions

The following namespace candidates should be added in a follow-on ownership tranche:

```yaml
identity/capability-broker: { canonical_repo: mcp-a2a-zero-trust }
identity/capability-registry: { canonical_repo: mcp-a2a-zero-trust }
standards/control-plane: { canonical_repo: prophet-platform-standards }
standards/control-plane-contracts: { canonical_repo: socioprophet-standards-storage }
prophet/control-plane-runtime: { canonical_repo: prophet-platform }
collaboration/matrix: { canonical_repo: prophet-platform }
```

## Sequencing

Recommended order:

1. `sociosphere` manifest dedupe and controller normalization
2. `sociosphere` ownership / placement tranche
3. `prophet-platform-standards` normative ADR tranche
4. `socioprophet-standards-storage` schema tranche
5. `mcp-a2a-zero-trust` broker / registry tranche
6. `prophet-platform` runtime tranche
7. `policy-fabric` consumer-adoption tranche

## Notes

This document does not change canonical ownership by itself.

It is intended to make the next ownership / namespace follow-on PR narrow, explicit, and reviewable.
