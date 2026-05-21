# ADR-0001: Flywheel hardening, authority precedence, semaphore-gated progression, and void containment

## Status

Proposed.

## Context

The SocioProphet flywheel links world evidence, ontology governance, semantic serialization, operations-domain intelligence, graph traversal, runtime proposals, defensive validation, learning/canonization, and workspace stabilization.

The risk is that this becomes an ungoverned one-way automation pipeline. A defensive finding, stale world reference, ontology drift, or revoked agent must not be laundered through downstream systems into an execution-eligible action, memory truth, or canonical learning object.

Sociosphere owns the cross-repo governance seat for this doctrine because it owns the canonical workspace manifest, workspace lock, topology/dependency rules, propagation metadata, governance registries, adversarial hardening critique, and validation lanes. Downstream repos may mirror this ADR by reference, but Sociosphere is the canonical home for the cross-repo hardening decision.

## Decision 1 — Explicit return paths

The flywheel is valid only when downstream learning returns to upstream criteria through reviewed candidate records. Downstream outputs must not directly mutate upstream authorities.

### Return path A: Alexandrian Academy → GAIA

A promoted learning object may propose a curation criterion for GAIA review. It may not declare world evidence valid.

```text
LearningObjectRef
  → CurationCriterionCandidate
  → human/domain review
  → GAIA ingestion policy candidate
```

### Return path B: SCOPE-D → Ontogenesis

A SCOPE-D exercise outcome may create an ontology risk note or promotion hold. It may not rewrite ontology.

```text
ScopeDRef
  → OntologyRiskNote | OntologyPromotionHold
  → Ontogenesis module review
  → promote | deprecate | revise | reject
```

### Return path C: FlywheelEvent → GDSI

A validated flywheel event may propose an intelligence threshold adjustment. GDSI must review, version, and validate any accepted threshold update.

```text
FlywheelEvent
  → IntelligenceThresholdAdjustmentCandidate
  → GDSI review
  → versioned profile update
```

The reviewer for threshold changes must be tied to the external defensive anchor governance role, not only to the producing flywheel component.

## Decision 2 — Ontogenesis versioning discipline

Ontogenesis is sovereign over ontology/semantic meaning. Sociosphere records downstream impact; consumers must not locally redefine ontology terms to avoid migration.

Minimum change classes:

- **Additive change:** new class, property, module, example, or SHACL extension that does not change existing semantics. Non-breaking; consumers may update voluntarily.
- **Deprecation:** an existing term remains valid but is scheduled for replacement or removal. Requires a migration issue or ADR and a default 90-day migration window unless the ontology authority declares a shorter security-critical window.
- **Breaking change:** rename, removal, namespace change, meaning change, or incompatible SHACL tightening. Requires migration ADR and downstream impact analysis.

## Decision 3 — WorldRef staleness and retroactive invalidation

GAIA is sovereign over world evidence. Any WorldRef used by proposals, intelligence projections, or learning/canon objects must be reviewable and invalidatable.

Minimum WorldRef fields:

```json
{
  "source_repo": "SocioProphet/gaia-world-model",
  "source_ref": "commit-sha-or-release",
  "world_artifact_id": "string",
  "observed_at": "RFC3339",
  "valid_until": "RFC3339",
  "review_by": "RFC3339",
  "invalidation_status": "ACTIVE|SUPERSEDED|RETRACTED|CORRUPT|UNKNOWN",
  "invalidation_ref": "optional"
}
```

Propagation rules:

- Past `review_by`: historical evidence may remain citeable, but canon promotion or execution-eligible proposal generation requires revalidation.
- Past `valid_until`: dependent proposals are stale and cannot become execution-eligible.
- `RETRACTED` or `CORRUPT`: dependent proposals become non-execution-eligible; dependent learning/canon objects degrade to `ReviewRequired`; Sociosphere emits propagation/stabilization events.

## Decision 4 — SCOPE-D provenance is non-strippable

Any object derived from SCOPE-D must carry a non-strippable provenance flag through all downstream transformations.

Minimum provenance field:

```json
{
  "scope_d_provenance": {
    "derived_from_scope_d": true,
    "scope_d_run_id": "string",
    "scope_d_exercise_id": "string",
    "safety_mode": "READ_ONLY|SYNTHETIC|DRY_RUN|GATED_MUTATION",
    "originating_evidence_refs": [],
    "operator_warning_required": true
  }
}
```

Required propagation path:

```text
SCOPE-D output
  → GDSI projection
  → IntelligenceRef
  → ActionProposal
  → HandoffCandidate
  → AgentPlane receipt/replay artifact
  → Memory/Search/Learning references
```

A SCOPE-D-derived proposal cannot be auto-approved. Any reviewer must see explicit warning language that the proposal originated from a SCOPE-D exercise.

## Decision 5 — Authority conflict protocol

Domain sovereignty is explicit:

| Domain | Sovereign authority |
|---|---|
| World evidence | GAIA |
| Ontology / semantic meaning | Ontogenesis |
| Semantic object encoding | Semantic SerDes |
| Agent identity, session, grants, revocation | Agent Registry / Regis |
| Workspace topology and propagation | Sociosphere |
| Operations-domain intelligence | Global DevSecOps Intelligence |
| Runtime proposal and deployment behavior | Prophet Platform |
| Execution receipt lifecycle | AgentPlane |
| Defensive exercise evidence | SCOPE-D |
| Learning canon | Alexandrian Academy |

Cross-domain conflicts are not resolved by implicit precedence. They produce a Sociosphere `ConflictRecord`.

Minimum ConflictRecord shape:

```json
{
  "conflict_id": "string",
  "opened_at": "RFC3339",
  "authorities": [],
  "domain": "WORLD_EVIDENCE|ONTOLOGY|AGENT_AUTHORITY|WORKSPACE_STATE|RUNTIME_POLICY|LEARNING_CANON",
  "description": "string",
  "affected_refs": [],
  "resolution_scope": "LOCAL|PROFILE|REPO|WORKSPACE|GLOBAL",
  "resolution_authority": {
    "type": "ROLE|QUORUM|NAMED_REVIEWER",
    "value": "string",
    "minimum_approvals": 1
  },
  "review_by": "RFC3339",
  "escalation_on_overdue": "SOCIOSPHERE_STABILIZATION_ALERT",
  "adopted_authority": "string",
  "resolution": "string",
  "reviewers": [],
  "status": "OPEN|RESOLVED|SUPERSEDED"
}
```

## Decision 6 — Alexandrian Academy reference-only boundary

Alexandrian Academy stores learning references, annotations, evaluations, and canonization records. It does not become the source of operational truth.

Allowed: cite `ScopeDRef`, `ProposalRef`, `WorldRef`, `OntologyRef`, `IntelligenceRef`, and `AgentRef`.

Forbidden: copy SCOPE-D evidence into a curriculum object as operational truth; re-encode Prophet Platform proposals as learning-system facts; treat learning content as runtime authority.

If a cited source artifact changes state, the learning object inherits that state. For example, a retracted WorldRef makes the dependent canon object `ReviewRequired`.

## Decision 7 — External defensive ground-truth anchor

SCOPE-D must maintain an external threat model anchor that the flywheel cannot overwrite.

Required artifact:

```text
SCOPE-D/docs/THREAT_MODEL_ANCHOR.md
```

Minimum requirements:

- Review cadence: quarterly or shorter.
- Required inputs: at least one external source citation per review cycle.
- Reviewer: named role or individual.
- Successor role: required.
- Sign-off format: committed review record.
- Flywheel override: forbidden.

Flywheel feedback may propose amendments. It cannot override the anchor.

## Decision 8 — Semaphore-gated progression

Flywheel progression reuses AgentPlane-style receipt semantics: normalized events joined by `trace_id`, required signals, optional approval signals, and fail-closed assembly when a required signal is absent.

A downstream transition is invalid unless required upstream signals exist, are valid, join by `trace_id`, and satisfy authority, policy, staleness, and provenance constraints.

For a SCOPE-D-derived proposal, the valid report-only sequence is:

```text
scope_d.validated
  → gdsi.projected
  → action.proposal.created
  → policy.evaluated(ALLOWED_REPORT_ONLY)
  → evidence.sealed
```

The forbidden v0.1 sequence is:

```text
scope_d.validated
  → gdsi.projected
  → policy.evaluated
  → placement.selected
  → run.started
```

Any SCOPE-D-derived escalation requires this explicit semaphore signal:

```text
human.reviewed.explicit_scope_d_ack
```

No execution lease may be issued from a SCOPE-D-derived proposal in v0.1.

## Decision 9 — PolicyFabric primary enforcement

PolicyFabric is the primary enforcement point for SCOPE-D-derived work.

If `scope_d_provenance.derived_from_scope_d == true`, PolicyFabric must not emit:

- `policy_status = ALLOWED_AUTO`
- `execution_eligible = true`

Permitted outcomes are:

- `DENIED`
- `ALLOWED_REPORT_ONLY`
- `REQUIRES_HUMAN_REVIEW_SCOPE_D_ACK`

AgentPlane receipt/semaphore validation remains defense in depth if an invalid policy state appears downstream.

## Decision 10 — Void Network containment

The Void Network is the non-propagation plane for unsafe, stale, unresolved, denied, or non-authoritative artifacts. Failure must not silently disappear, and it must not proceed through the normal flywheel.

Minimum VoidRecord shape:

```json
{
  "void_record_id": "void_...",
  "trace_id": "trace_...",
  "created_at": "RFC3339",
  "source_event_ref": "evt_...",
  "void_reason": "REVOKED_AGENT|STALE_WORLD_REF|SCOPE_D_REQUIRES_HUMAN_REVIEW|POLICY_DENIED|GRAPH_PATH_UNBOUNDED|EVIDENCE_INCOMPLETE",
  "containment_mode": "QUARANTINE|BLACKHOLE|REVIEW_QUEUE|DECAY|SINK_ONLY|SYNTHETIC_ONLY",
  "allowed_actions": ["review", "annotate", "link_to_conflict_record"],
  "forbidden_actions": ["execute", "promote_to_canon", "write_to_memory_as_truth", "emit_execution_lease"],
  "review_by": "RFC3339",
  "evidence_refs": []
}
```

Containment behavior:

- `REVIEW_QUEUE`: escalate if overdue.
- `DECAY`: move to expired void evidence after TTL.
- `BLACKHOLE`: audit-only; no propagation.
- `QUARANTINE`: reviewer action required.
- `SYNTHETIC_ONLY`: usable only in tests/training.

If `review_by` passes while status remains open, Sociosphere emits a stabilization alert and blocks downstream propagation for affected refs.

## Empirical-cycle gate

Before broad schema expansion, the estate must run one manual empirical cycle:

```text
SCOPE-D exercise
  → rough GDSI projection
  → rough Prophet Platform proposal
  → human review
  → Memory/Search note
  → Sociosphere flywheel event
```

Sprint 2 may begin only after ambiguities affecting `ScopeDProvenance`, `VoidRecord`, `ConflictRecord`, and the PolicyFabric enforcement rule are resolved. Ambiguities affecting `WorldRef`, `OntologyRef`, `MeshRushTraceRef`, `CairnPathRef`, or `LearningObjectRef` may be logged and deferred.

## Consequences

Positive:

- SCOPE-D findings cannot be laundered into auto-approved runtime action.
- Unsafe traces fail closed and become reviewable VoidRecords.
- Domain authorities remain sovereign without blocking cross-domain governance.
- Learning/canon objects remain reference-backed and degrade when evidence degrades.

Negative:

- Some automation paths are deliberately blocked until human review and provenance semantics mature.
- The ADR introduces cross-repo governance obligations before all schemas exist.

Follow-ups:

1. Add PolicyFabric primary-denial fixture.
2. Add AgentPlane/Void defense-in-depth fixture.
3. Add minimal validator for those fixtures.
4. Run the empirical manual flywheel cycle and capture an ambiguity log.
5. Only then expand `AgentRef`, `IntelligenceRef`, `ScopeDRef`, `WorldRef`, `OntologyRef`, `CairnPathRef`, `MeshRushTraceRef`, and `LearningObjectRef`.
