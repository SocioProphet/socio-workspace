# Service Register Architecture Control Set

Status: PR-A scaffold, warn-only validation.

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

## Governance decisions captured

- `SocioProphet/Shining-Apple` is removed from the go-forward estate.
- `SocioProphet/sourceos-a2a-mcp-bootstrap` is a consolidation candidate into `SocioProphet/mcp-a2a-zero-trust` and/or `SocioProphet/TriTRPC`; it is not a standalone service.
- `SocioProphet/prophet-platform-fabric-mlops-ts-suite` supports both `svc.product.model-training` and `svc.platform.compute-mesh`.
- `svc.platform.agent-runtime <-> svc.platform.compute-mesh` is an allowed optional/runtime feedback cycle, not a hard bootstrap cycle.
- `svc.platform.agent-runtime <-> svc.platform.model-governance` is an allowed policy/evaluation feedback loop, not a hard bootstrap cycle.

## Validation posture

PR-A is intentionally warn-only. It establishes canonical artifact locations and schemas before enforcing coverage or graph checks.

Validation hardening order:

1. PR-A: land artifacts, schemas, README, warn-only validator.
2. PR-B: add repo coverage validator.
3. PR-C: add edge validator and cycle classifier.
4. PR-D: generate critical path report from classified graph.
5. PR-E: wire `workspace-inventory` as canonical repo source.
6. PR-F: add drift report and CI gate.
