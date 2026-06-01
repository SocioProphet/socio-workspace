# Computational Artifact Registry

## Purpose

Sociosphere is the **registry and mesh governance layer** for the Prophet Computational
Knowledge Plane. It owns:

- The canonical list of governed computational artifacts and their health states.
- Change-propagation rules that determine which downstream repos must be notified
  when an artifact's contract, runtime profile, policy binding, or evidence changes.
- Slash-topic governance bindings that route artifact events through the
  `/computational-artifacts/*` topic namespace.
- Promotion guardrails that prevent `privileged` or `prohibited` artifacts from
  being auto-promoted without human review.

Sociosphere does **not** implement the downstream features that consume these
artifacts. Runtime execution, model serving, search indexing, and policy
enforcement live in their respective owner repos
(`SocioProphet/prophet-platform`, `SocioProphet/lattice-forge`, etc.).

---

## Registry file

```text
registry/computational-artifacts.yaml
```

| Field | Description |
|---|---|
| `apiVersion` | `sociosphere.socioprophet.org/v1alpha1` |
| `kind` | `ComputationalArtifactRegistry` |
| `spec.safetyClasses` | `advisory`, `bounded`, `privileged`, `prohibited` |
| `spec.healthModel.freshnessStates` | `fresh`, `stale`, `drifted`, `blocked`, `deprecated` |
| `spec.propagationRules` | Change-trigger to notify-repo mapping |
| `spec.governance.slashTopicBinding` | Slash-topic namespace and approval policy |
| `spec.registryEntries` | Per-artifact entries |

### Per-artifact entry fields

| Field | Required | Description |
|---|---|---|
| `id` | yes | Unique artifact identifier, for example `gaia.bounded-osm-ingest` |
| `ownerRepo` | yes | GitHub repo that owns the artifact definition |
| `artifactPath` | no | Relative path to `prophet-artifact.yaml` within `ownerRepo` |
| `runtimeProfile` | yes | Lattice Forge runtime profile reference |
| `safetyClass` | yes | One of `advisory`, `bounded`, `privileged`, `prohibited` |
| `slashTopics` | no | Slash-topic bindings for this artifact |
| `downstreamConsumers` | yes | Repos that consume this artifact |
| `status` | no | Lifecycle status: `seed`, `fresh`, `stale`, `drifted`, `blocked`, `deprecated` |
| `requiredEvidence` | yes | Evidence items the artifact must produce |

---

## Health states

| State | Meaning |
|---|---|
| `fresh` | All required signals present, no drift detected |
| `stale` | Required evidence not yet produced, for example seed stage |
| `drifted` | Runtime profile or contract has changed since last attestation |
| `blocked` | Artifact is `privileged` or `prohibited` and awaiting human review |
| `deprecated` | Artifact is retired; downstream consumers must migrate |

---

## Change propagation

When an artifact's contract, runtime profile, policy binding, or evidence changes,
Sociosphere's propagation rules determine which downstream repos receive a
notification.

| Trigger | Notified repos |
|---|---|
| `artifactContractChanged` | prophet-platform, gaia-world-model, lattice-forge, sherlock-search, holmes, delivery-excellence |
| `runtimeProfileChanged` | prophet-platform, gaia-world-model, delivery-excellence |
| `policyChanged` | prophet-platform, policy-fabric, guardrail-fabric, agentplane |
| `evidenceChanged` | prophet-platform, sherlock-search, delivery-excellence |
| `safetyClassPrivileged` | blocks auto-promotion; requires human review |
| `safetyClassProhibited` | blocks auto-promotion; requires human review; rejected on ingest |

---

## Slash-topic governance

All computational artifact events are routed through the
`/computational-artifacts` slash-topic namespace, governed by
`SocioProphet/slash-topics`. Topic approval is required before an artifact
can be promoted.

Sub-topics:

- `/computational-artifacts/registry`
- `/computational-artifacts/health`
- `/computational-artifacts/propagation`
- `/computational-artifacts/governance`

---

## Validation

```bash
make computational-artifacts-validate
python3 tools/runner/artifact_health_report.py
python3 tools/runner/artifact_health_report.py --table
python3 tools/runner/artifact_health_report.py --output /tmp/artifact-health-report.json
```

The report lists for each artifact:

- artifact id
- owner repo
- runtime profile
- safety class
- evidence status
- downstream consumers
- health state
- whether auto-promotion is blocked

---

## Adding a new artifact

1. Add an entry to `spec.registryEntries` in `registry/computational-artifacts.yaml`.
2. Set `safetyClass` appropriately. `privileged` and `prohibited` entries are blocked from auto-promotion.
3. Run `make computational-artifacts-validate` to confirm the entry is valid.
4. Run `python3 tools/runner/artifact_health_report.py --table` to verify the new artifact appears in the health report.

Sociosphere validates and propagates registry state. Implementing the downstream
feature is the responsibility of the owning repo.
