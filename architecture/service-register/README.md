# Service Register Architecture Control Set

Status: post-PR-418 artifact-count gate enabled.

This directory is the SocioSphere home for the service architecture control set that governs the SocioProphet / SourceOS / SociOS estate.

## Canonical inputs

The intended v1.0 control set is:

| Artifact | Purpose |
|---|---|
| `service-architecture-register.v1.0.csv` | Canonical service-level register: 46 services, 125 go-forward repos, no misc bucket. |
| `canonical-repo-estate.v1.0.csv` | Canonical go-forward repo list derived from register owner/support/contract fields. |
| `service-dependency-edges.v0.1.csv` | Canonical graph-level edge table: 119 typed dependency edges. |
| `critical-contract-path-stubs.v0.1.csv` | Four blocking services with target contract paths; target files may be missing during PR-A. |
| `critical-path-blocking-report.v0.2.csv` | Current manually curated critical path report: 4 BLOCKING and 4 HARDENING rows. |
| `repo-reconciliation-report.v0.1.csv` | A2A/MCP and Fabric/MLOps/Atlas reconciliation notes. |
| `sociosphere-service-register-ingestion-manifest.v1.0.json` | Machine-readable ingestion manifest. |
| `service-register-gate-policy.v0.1.json` | Current gate policy: strict artifact presence and row-count validation; semantic graph checks remain staged. |

## Governance decisions captured

- `SocioProphet/Shining-Apple` is removed from the go-forward estate.
- `SocioProphet/sourceos-a2a-mcp-bootstrap` is a consolidation candidate into `SocioProphet/mcp-a2a-zero-trust` and/or `SocioProphet/TriTRPC`; it is not a standalone service.
- `SocioProphet/prophet-platform-fabric-mlops-ts-suite` supports both `svc.product.model-training` and `svc.platform.compute-mesh`.
- `svc.platform.agent-runtime <-> svc.platform.compute-mesh` is an allowed optional/runtime feedback cycle, not a hard bootstrap cycle.
- `svc.platform.agent-runtime <-> svc.platform.model-governance` is an allowed policy/evaluation feedback loop, not a hard bootstrap cycle.

## Validation posture

The service-register lane has advanced past the original PR-A scaffold. As of PR #418, artifact presence and artifact row counts are strict gate checks.

Strict checks currently enforced:

1. Required service-register artifacts are present.
2. `service-architecture-register.v1.0.csv` has 46 rows.
3. `canonical-repo-estate.v1.0.csv` has 125 rows.
4. `service-dependency-edges.v0.1.csv` has 119 rows.
5. `critical-contract-path-stubs.v0.1.csv` has 4 rows.

Checks intentionally still staged / warning-only until the `workspace-inventory` export path and semantic enforcement rules are stable:

1. Repo coverage against `SocioProphet/workspace-inventory`.
2. Dependency-cycle semantics.
3. Critical-path generation semantics.
4. Workspace-inventory drift.
5. New blocking-service acknowledgement policy.

Validation hardening order:

1. PR-A: land artifacts, schemas, README, and warn-only validator.
2. PR-B: add repo coverage validator.
3. PR-C: add edge validator and cycle classifier.
4. PR-D: generate critical path report from classified graph.
5. PR-E: wire `workspace-inventory` as canonical repo source.
6. PR-F: add drift report and CI gate.
7. PR-418: enforce artifact presence and row-count validation.
8. Next: stabilize `workspace-inventory` export path, then promote repo coverage and semantic graph checks from warning-only to hard gates.
