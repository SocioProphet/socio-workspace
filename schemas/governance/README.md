# Governance schema stubs

Status: v0.1 schema stubs
Owner: Sociosphere governance layer

This directory defines the first machine-readable object contracts for the regulated-domain institutional-action doctrine.

## Schemas

| Schema | Purpose |
|---|---|
| `institutional-action.v0.1.schema.json` | Complete governed action object binding actor, role, authority, context, evidence, policy, procedure, capability, approval, and execution receipt. |
| `procedure-template.v0.1.schema.json` | Governed workflow template with required inputs, policy basis, evidence requirements, output schema, approval gate, and replay test. |
| `evidence-bundle.v0.1.schema.json` | Versioned source/evidence bundle supporting a governed decision or execution. |
| `execution-receipt.v0.1.schema.json` | Hashable record proving what executed a governed action and which artifacts/replay refs support it. |

## Boundary

These files are schema stubs only. They do not imply runtime middleware, storage implementation, HellGraph ingestion, AgentPlane receipt emission, or Prophet Platform API readiness. Runtime adoption requires downstream fixtures, validators, graph queries, and admission tests.

## Ownership alignment

- SocioProphet records institutional actions.
- Sociosphere owns the governance topology and schema registration posture.
- HellGraph serves graph-backed governance state and query fixtures.
- AgentPlane emits execution and replay evidence.
- Prophet Platform exposes release/admission validator surfaces.
- Ontogenesis owns ontology and shape authority when these schemas are lifted into semantic vocabularies.
