# Evaluation schema stubs

Status: v0.1 schema stubs
Owner: Sociosphere governance layer

This directory defines machine-readable benchmark contracts derived from the regulated AI control-plane benchmark.

## Schemas

| Schema | Purpose |
|---|---|
| `domain-bench.v0.1.schema.json` | Domain-specific evaluation with rubric lineage, task coverage, and scoring policy. |
| `workflow-bench.v0.1.schema.json` | Operational workflow evaluation for adoption, timing, quality, correction, and override metrics. |
| `governance-bench.v0.1.schema.json` | Governance evaluation for policy, approval, override, audit, and authority behavior. |
| `replay-bench.v0.1.schema.json` | Replay evaluation for graph snapshots, evidence retention, artifact availability, and determinism posture. |

## Boundary

These schemas do not claim benchmark execution, domain certification, production readiness, or runtime product capability. They establish the contract layer required before those claims can be validated.
