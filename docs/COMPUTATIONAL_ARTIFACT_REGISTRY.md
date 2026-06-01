# Computational Artifact Registry

Sociosphere owns the registry and mesh-governance layer for Prophet Computational Knowledge Plane artifacts. It records governed computational artifacts, health states, change propagation, slash-topic bindings, and promotion guardrails.

Sociosphere does not implement downstream runtime execution, model serving, search indexing, or policy enforcement. Those remain in their respective owner repositories.

## Registry

Registry path:

```text
registry/computational-artifacts.yaml
```

Key fields:

| Field | Meaning |
|---|---|
| `spec.safetyClasses` | `advisory`, `bounded`, `privileged`, `prohibited` |
| `spec.healthModel.freshnessStates` | `fresh`, `stale`, `drifted`, `blocked`, `deprecated` |
| `spec.propagationRules` | Change-trigger to notification mapping |
| `spec.governance.slashTopicBinding` | `/computational-artifacts` governance binding |
| `spec.registryEntries` | Per-artifact registry entries |

## Health states

| State | Meaning |
|---|---|
| `fresh` | Required signals present, no drift detected |
| `stale` | Required evidence is not yet produced |
| `drifted` | Runtime profile or contract changed since attestation |
| `blocked` | Artifact requires review or is prohibited |
| `deprecated` | Artifact is retired and consumers must migrate |

## Propagation triggers

| Trigger | Meaning |
|---|---|
| `artifactContractChanged` | Artifact contract changed |
| `runtimeProfileChanged` | Runtime profile changed |
| `policyChanged` | Policy binding changed |
| `evidenceChanged` | Required evidence changed |
| `safetyClassPrivileged` | Auto-promotion blocked; human review required |
| `safetyClassProhibited` | Auto-promotion blocked; human review required; rejected on ingest |

## Slash-topic governance

Computational artifact events are routed through `/computational-artifacts`, governed by `SocioProphet/slash-topics`.

Subtopics:

- `/computational-artifacts/registry`
- `/computational-artifacts/health`
- `/computational-artifacts/propagation`
- `/computational-artifacts/governance`

## Validation

```bash
python3 tools/validate_computational_artifacts.py
python3 tools/runner/artifact_health_report.py
python3 tools/runner/artifact_health_report.py --table
```

The report emits artifact id, owner repo, runtime profile, safety class, evidence status, downstream consumers, health state, and whether auto-promotion is blocked.
