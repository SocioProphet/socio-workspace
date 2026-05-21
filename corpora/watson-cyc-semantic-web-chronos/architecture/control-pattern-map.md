# Control Pattern Map

Status: v0.1 corpus architecture mapping.

This file maps agent-control architectures to SocioProphet runtime responsibilities.

## Behavior Trees

Primary target: Agentplane.

Use as default fast controller for inspectable action selection.

Required concepts:

- tick-based execution
- selectors and sequences
- condition leaves
- policy-decorated action leaves
- decorators for retry, timeout, budget, risk tier, and evidence quorum
- fallback subtrees
- blackboard state
- log replay and traceability

Controls:

- subtree registry
- risk-tiered branches
- typed blackboard contracts
- validation tests
- no unreviewed high-risk leaves

## BDI

Primary target: Agentplane and Sociosphere.

Use for belief, goal, intention, commitment, and plan-library management.

Required concepts:

- evidence-bound beliefs
- policy-grounded desires/goals
- revocable intentions
- versioned plan libraries
- contradiction-aware belief revision
- provenance-bearing plan adoption

Controls:

- stale-evidence rejection
- confidence thresholds
- source-quality labels
- intention cancellation records
- policy escalation on belief conflict

## Subsumption

Primary target: SourceOS and Agentplane reflex layer.

Use for narrow, safe, low-latency base behaviors.

Allowed reflex actions:

- collect evidence
- pause or quarantine a bounded task
- degrade gracefully
- emit alert
- request policy review
- preserve audit trail

Forbidden reflex actions:

- broad destructive changes
- policy mutation
- evidence deletion
- irreversible deployment
- unreviewed credential or identity changes

## MAPE-K

Primary target: SourceOS, Sociosphere, operations control.

Loop:

- Monitor
- Analyze
- Plan
- Execute
- over Knowledge

Control placement:

- Policy check before Execute.
- Validation check before Knowledge mutation.
- Audit record after every loop transition.

## OODA

Primary target: adversarial and operational orientation.

Loop:

- Observe
- Orient
- Decide
- Act

Use for fast adversarial orientation where MAPE-K is too operations-centric.

Controls:

- Orient must include source-quality and deception checks.
- Decide must call Policy Fabric for high-impact action.
- Act must emit Model Governance Ledger audit records.

## AICA

Primary target: ProCybernetica, SourceOS, Agentplane adversarial mode.

Mission functions:

- sensing and world-state identification
- planning and action selection
- collaboration and negotiation
- action execution with monitoring
- learning and knowledge improvement

Controls:

- rules of engagement
- simulation before execution where possible
- reversible actuation preference
- bounded effectors
- adversarial evidence checks
- governed learning only
- explicit audit trail

## Recommended Agentplane control stack

```text
Reflex safety layer: Subsumption-style bounded responses
Fast controller: Behavior Trees
Goal/commitment layer: BDI
Impasse escalation: Holmes deliberation
Authorization: Policy Fabric
Audit: Model Governance Ledger
Adversarial mission envelope: AICA
```

## Do-not-cross lines

- No direct action from Holmes.
- No direct authorization from Sherlock.
- No policy mutation from Agentplane runtime branches.
- No high-risk execution from reflex layers.
- No self-modifying controller without review, sandboxing, and rollback.
