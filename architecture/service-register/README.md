# Service Register Architecture Control Set

Status: deterministic service-register gate with workspace-inventory mirror pinning and reconciliation artifacts.

This directory is the SocioSphere home for the service architecture control set that governs the SocioProphet / SourceOS / SociOS estate.

## Canonical inputs

The intended v1.0 control set is:

| Artifact | Purpose |
|---|---|
| `service-architecture-register.v1.0.csv` | Canonical service-level register: 46 services, 125 go-forward repos, no misc bucket. |
| `canonical-repo-estate.v1.0.csv` | Canonical go-forward repo list derived from register owner/support/contract fields and mirrored from Workspace Inventory authority. |
| `canonical-repo-estate.mirror.v1.0.json` | Deterministic local mirror pin for the Workspace Inventory canonical repo-estate export. |
| `workspace-inventory-source.v0.1.json` | Binding metadata for the Workspace Inventory source export and validation workflow. |
| `workspace-inventory-sync-report.generated.csv` | Generated no-network sync posture report for future upstream comparison. |
| `service-dependency-edges.v0.1.csv` | Canonical graph-level edge table: 119 typed dependency edges. |
| `critical-contract-path-stubs.v0.1.csv` | Four blocking services with target contract paths. |
| `critical-path-blocking-report.generated.csv` | Generated critical path report from the service graph. |
| `critical-path-blocking-report.v0.2.csv` | Current manually curated critical path report: 4 BLOCKING and 4 HARDENING rows. |
| `repo-reconciliation-report.v0.1.csv` | A2A/MCP and Fabric/MLOps/Atlas reconciliation notes. |
| `fabric-atlas-model-carry-reconciliation.v0.1.csv` | Expanded authority matrix for TritFabric, Atlas bundle repos, Fabric/MLOps, SourceOS model-carry, SHIR, runtime, routing, policy, governance, and lab boundaries. |
| `fabric-atlas-model-carry-propagation-plan.v0.1.csv` | Planned propagation rows for converting the reconciliation matrix into service edges, contract registry targets, repo status metadata, and follow-on archive/inspection actions. |
| `atlas-bundle-diff-status.v0.1.csv` | Negative-evidence and blocker status for the three Atlas bundle repositories pending direct tree/file confirmation. |
| `service-register-drift-report.generated.csv` | Generated deterministic drift report including row counts and canonical repo mirror-pin status. |
| `sociosphere-service-register-ingestion-manifest.v1.0.json` | Machine-readable ingestion manifest. |
| `service-register-gate-policy.v0.1.json` | Current gate policy for strict deterministic service-register validation. |

## Governance decisions captured

- `SocioProphet/Shining-Apple` is removed from the go-forward estate.
- `SocioProphet/sourceos-a2a-mcp-bootstrap` is a consolidation candidate into `SocioProphet/mcp-a2a-zero-trust` and/or `SocioProphet/TriTRPC`; it is not a standalone service.
- `SocioProphet/tritfabric` is the canonical implementation and immediate contract authority for recovered Atlas / TritFabric / Community / Serve work; SocioSphere records absorption, boundary posture, and propagation requirements.
- Atlas bundle repositories are reference / archive / incubation candidates pending direct tree/file confirmation; `atlas_os_service_full` is the strongest archive/retire candidate by current evidence.
- `SocioProphet/prophet-platform-fabric-mlops-ts-suite` is the downstream Fabric/MLOps pack lane, not the root fabric authority.
- `SocioProphet/semantic-serdes` is the SHIR / semantic serialization authority; downstream MLOps/runtime repos consume its schemas and receipts.
- `SourceOS-Linux/sourceos-model-carry` is SourceOS carry/reference authority only; it must not become authorization, routing, runtime, lifecycle, promotion, or tuning authority.
- `SocioProphet/prophet-platform-fabric-mlops-ts-suite` supports both `svc.product.model-training` and `svc.platform.compute-mesh`.
- `svc.platform.agent-runtime <-> svc.platform.compute-mesh` is an allowed optional/runtime feedback cycle, not a hard bootstrap cycle.
- `svc.platform.agent-runtime <-> svc.platform.model-governance` is an allowed policy/evaluation feedback loop, not a hard bootstrap cycle.

## Validation posture

The service-register lane has advanced past the original PR-A scaffold. Artifact presence, row counts, Workspace Inventory binding metadata, canonical repo mirror identity, generated sync-report freshness, generated drift-report freshness, reconciliation artifacts, propagation-plan structure, Atlas bundle diff status, and critical contract ledgers are now deterministic checks.

Strict checks currently enforced:

1. Required service-register artifacts are present.
2. `service-architecture-register.v1.0.csv` has 46 rows.
3. `canonical-repo-estate.v1.0.csv` has 125 rows.
4. `service-dependency-edges.v0.1.csv` has 119 rows.
5. `critical-contract-path-stubs.v0.1.csv` has 4 rows.
6. Workspace Inventory binding metadata matches the stable export contract.
7. `canonical-repo-estate.v1.0.csv` matches the pinned local Git blob SHA in `canonical-repo-estate.mirror.v1.0.json`.
8. `workspace-inventory-sync-report.generated.csv` is fresh relative to its generator.
9. `service-register-drift-report.generated.csv` is fresh relative to its generator.
10. Critical contract paths and contract target ledger checks run in strict mode.
11. `fabric-atlas-model-carry-reconciliation.v0.1.csv` has required rows, columns, confidence values, and root authority ordering.
12. `fabric-atlas-model-carry-propagation-plan.v0.1.csv` has required propagation IDs, source artifact linkage, status values, and target-artifact shape.
13. `atlas-bundle-diff-status.v0.1.csv` has exactly the three Atlas bundle rows, explicit negative evidence fields, allowed status values, and direct tree/file listing blocker language.

Checks intentionally still staged / warning-only or not yet promoted:

1. Live networked comparison against the upstream Workspace Inventory export.
2. Atlas bundle archive/retirement decision after direct tree/file confirmation.
3. Direct mutation of generated service-register and dependency-edge chunks from propagation-plan rows.
4. Blocking-service acknowledgement policy beyond the current contract ledger.

Validation hardening order:

1. PR-A: land artifacts, schemas, README, and warn-only validator.
2. PR-B: add repo coverage validator.
3. PR-C: add edge validator and cycle classifier.
4. PR-D: generate critical path report from classified graph.
5. PR-E: wire `workspace-inventory` as canonical repo source.
6. PR-F: add drift report and CI gate.
7. PR-418: enforce artifact presence and row-count validation.
8. Workspace Inventory mirror tranche: add source binding, mirror pin, generated sync report, generated drift report, and freshness checks.
9. Fabric / Atlas / Model Carry tranche: add confidence-scored authority reconciliation matrix and validator.
10. Propagation-plan tranche: add planned semantic propagation rows without mutating generated register/edge chunks blindly.
11. Atlas diff-status tranche: preserve negative Atlas evidence and direct tree/file blocker in a validated artifact.
12. Next: apply propagation rows to source-of-truth register/edge generation once artifact chunk provenance is confirmed, and confirm Atlas root trees before archive decisions.
