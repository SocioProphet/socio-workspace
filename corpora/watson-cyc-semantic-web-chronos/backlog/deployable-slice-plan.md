# Deployable Slice Plan v0

Status: execution plan.

This plan converts the corpus substrate into a deployable cross-repo cybernetic loop.

The target v0 loop is:

```text
EvidenceBundle
  -> Ontogenesis schema validation
  -> Agentplane ActionProposal
  -> Policy Fabric PolicyDecision
  -> Model Governance Ledger AuditEvent
```

The purpose is not to implement a full agent platform yet. The purpose is to create the minimum enforceable runtime contract proving that evidence, provenance, policy, and audit can move through the estate without being lost.

## 1. Workstream A: Sherlock Evidence Kernel

Target issue: SocioProphet/sherlock-search#56

### Deliverable

A minimal source-quality-aware evidence model.

### Required types

#### SourceQuality

Enum:

- `confirmed_official`
- `confirmed_bibliographic`
- `confirmed_pdf`
- `confirmed_artifact`
- `plausible_needs_source`
- `speculative_do_not_use`

Runtime rule:

- confirmed values may support implementation-grade decisions.
- plausible/speculative values may support research-only diagnostics.
- unknown values fail validation.

#### EvidenceSource

Required fields:

- `source_id`
- `title`
- `source_quality`
- `source_type`
- `locator`
- `retrieved_at` or `observed_at`

Optional fields:

- `doi`
- `arxiv_id`
- `url`
- `license`
- `artifact_id`

#### Claim

Required fields:

- `claim_id`
- `text`
- `claim_type`
- `evidence_source_ids`
- `support_status`

Support status enum:

- `supported`
- `partially_supported`
- `unsupported`
- `research_only`
- `blocked`

#### EvidenceBundle

Required fields:

- `bundle_id`
- `sources`
- `claims`
- `minimum_source_quality`
- `created_at`

Derived fields:

- `implementation_safe: boolean`
- `research_only: boolean`
- `blocked_reason`

#### AnswerTrace

Required fields:

- `answer_id`
- `question_or_task`
- `claims`
- `evidence_bundle_id`
- `diagnostic_findings`

### Acceptance tests

- Bundle with one confirmed source and supported claim passes.
- Claim without source fails.
- Source without source_quality fails.
- Bundle with only plausible/speculative sources is `research_only`.
- Bundle with speculative source cannot become implementation-safe.

## 2. Workstream B: Ontogenesis Schema Families

Target issue: SocioProphet/ontogenesis#89

### Deliverable

A minimal schema package for events, provenance, diagnostics, semantic tables, and causal relations.

### Required schemas

#### SourceProvenance

Required fields:

- `source_id`
- `evidence_bundle_id`
- `source_quality`
- `claim_ids`

Validation:

- source_quality must match Sherlock enum.
- evidence_bundle_id must be non-empty.

#### EventInstance

Required fields:

- `event_id`
- `event_type`
- `arguments`
- `provenance`
- `confidence`
- `status`

Status enum:

- `candidate`
- `confirmed`
- `rejected`
- `superseded`

Validation:

- Event without provenance fails.
- Confirmed event must have at least one confirmed source.
- Candidate event may use plausible sources but must not be confirmed.

#### CausalRelationCandidate

Required fields:

- `relation_id`
- `cause_event_id`
- `effect_event_id`
- `evidence_bundle_id`
- `confidence`
- `status`

Validation:

- confidence required.
- status defaults to candidate.
- no causal relation is treated as confirmed without evidence review.

#### ConceptHierarchyProbe

Required fields:

- `probe_id`
- `concept_a`
- `concept_b`
- `relation_type`
- `expected_result`
- `observed_result`
- `evidence_bundle_id`

#### KGSubgraphRiskFinding

Required fields:

- `finding_id`
- `subgraph_ref`
- `risk_type`
- `evidence_bundle_id`
- `severity`

### Acceptance tests

- Event without provenance fails.
- Confirmed event with research-only evidence fails.
- Causal edge without confidence fails.
- Diagnostic finding without evidence bundle fails.
- Semantic table record with missing source quality fails.

## 3. Workstream C: Agentplane Policy-Gated Action Loop

Target issue: SocioProphet/agentplane#162

### Deliverable

A minimal action proposal and runtime trace model that cannot execute without a policy decision.

### Required types

#### ActionProposal

Required fields:

- `proposal_id`
- `actor_id`
- `action_type`
- `target_ref`
- `intent`
- `evidence_bundle_id`
- `risk_tier`
- `created_at`

Risk tier enum:

- `low`
- `medium`
- `high`
- `critical`

#### RuntimeTrace

Required fields:

- `trace_id`
- `proposal_id`
- `policy_decision_id`
- `execution_status`
- `audit_event_id`

Execution status enum:

- `not_executed`
- `executed`
- `blocked`
- `modified`
- `escalated`
- `failed`

#### InterventionOutcomeRecord

Required fields:

- `intervention_id`
- `proposal_id`
- `policy_decision_id`
- `intervention_type`
- `outcome`

### Runtime rules

- `execute(action)` must fail unless a valid PolicyDecision exists.
- `execute(action)` must emit RuntimeTrace.
- Any denied, modified, or escalated action must emit InterventionOutcomeRecord.
- High and critical risk tiers must require confirmed evidence or escalation.

### Acceptance tests

- Action without policy decision fails.
- Action with allow decision succeeds in a bounded test executor.
- Deny decision blocks execution and emits trace.
- Modify decision records original proposal and modified constraint.
- Escalate decision prevents execution and emits escalation trace.

## 4. Workstream D: Policy Fabric Decision Primitives

Target issue: SocioProphet/policy-fabric#78

### Deliverable

A minimal policy decision object that Agentplane can call and Model Governance Ledger can audit.

### Required types

#### PolicyInput

Required fields:

- `proposal_id`
- `actor_id`
- `action_type`
- `risk_tier`
- `evidence_bundle_id`
- `requested_scope`

#### PolicyDecision

Required fields:

- `decision_id`
- `proposal_id`
- `decision`
- `policy_rule_refs`
- `evidence_bundle_id`
- `reason`
- `created_at`

Decision enum:

- `allow`
- `deny`
- `modify`
- `escalate`

#### RuntimeConstraint

Required fields:

- `constraint_id`
- `decision_id`
- `constraint_type`
- `value`

### Required rules

- Missing evidence -> deny or escalate.
- Research-only evidence -> deny or escalate for implementation-grade actions.
- High-risk action with plausible/speculative evidence -> deny.
- Critical action -> escalate by default in v0.
- Modified action must preserve original proposal reference.

### Acceptance tests

- Low-risk action with confirmed evidence can allow.
- Action with missing evidence denies/escalates.
- Research-only evidence cannot authorize implementation-grade action.
- Critical action escalates.
- Decision serializes to audit-ready payload.

## 5. Workstream E: Model Governance Ledger Audit Primitives

Target issue: SocioProphet/model-governance-ledger#19

### Deliverable

A minimal audit record package that records policy decisions, runtime action outcomes, source quality, and intervention traces.

### Required types

#### AuditEvent

Required fields:

- `audit_event_id`
- `event_type`
- `actor_id`
- `proposal_id`
- `policy_decision_id`
- `source_quality_summary`
- `created_at`

#### RegulatoryEvidenceRecord

Required fields:

- `record_id`
- `policy_decision_id`
- `evidence_bundle_id`
- `source_quality_summary`
- `regulatory_context`

#### TrustMetricRecord

Required fields:

- `metric_id`
- `subject_ref`
- `metric_type`
- `value`
- `evidence_bundle_id`

### Acceptance tests

- AuditEvent without policy_decision_id fails.
- AuditEvent without source_quality_summary fails.
- InterventionOutcomeRecord links to AuditEvent.
- TrustMetricRecord links to evidence bundle.

## 6. Cross-Repo Integration Test v0

### Test scenario

A Sherlock evidence bundle contains a confirmed bibliographic source for CHRONOS and a claim that event instances require provenance.

Ontogenesis validates a candidate EventInstance using that evidence bundle.

Agentplane proposes a low-risk action: `record_event_instance`.

Policy Fabric evaluates the proposal.

Model Governance Ledger records the policy decision and runtime trace.

### Expected result

- evidence bundle validates
- EventInstance validates
- ActionProposal validates
- PolicyDecision returns allow
- RuntimeTrace emitted
- AuditEvent emitted

### Negative tests

- event without provenance fails before action proposal
- action without evidence denies/escalates
- action using speculative evidence cannot allow
- audit event missing policy decision fails

## 7. Implementation order

1. Ontogenesis schema definitions.
2. Sherlock source-quality and evidence bundle model.
3. Policy Fabric decision model.
4. Model Governance Ledger audit model.
5. Agentplane action proposal and runtime trace model.
6. Cross-repo fixture and documentation.

## 8. Done criteria for v0

v0 is done when a bounded test action can flow through:

```text
EvidenceBundle -> schema validation -> ActionProposal -> PolicyDecision -> RuntimeTrace -> AuditEvent
```

with failure cases enforced for missing provenance, missing policy, missing audit, and unsupported evidence.
