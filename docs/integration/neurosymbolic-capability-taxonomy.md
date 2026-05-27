# Neuro-Symbolic Capability Taxonomy

Status: v0.1 derived taxonomy for CHRONOS / corpus-loop integration.

This document classifies neuro-symbolic capability families for use in SocioSphere rollout and CHRONOS carrier registration. It is a derivative estate taxonomy, not a reproduction of third-party course material.

## Classification rules

A capability entry must answer four questions:

1. What kind of symbolic surface does it touch?
2. What kind of neural or statistical component does it use?
3. What artifact does it emit into CHRONOS?
4. Which authority plane may admit, reject, or promote the artifact?

A taxonomy class is not an authority grade. It is only an integration role.

## Capability classes

### NSR-FOUNDATION-LOGIC

Formal logic substrate: atoms, formulas, rules, worlds, satisfaction, consistency, entailment, grounding, annotated truth, fuzzy operators, and fixpoint closure.

CHRONOS artifact role:

- `NormalizedClaim`
- `EvidenceAnchor`
- `ExplanationTrace`
- `VerificationResult`

Boundary:

- Can define vocabulary for carrier interpretation.
- Cannot prove carrier truth unless the proof system and assumptions are explicit.

### NSR-TAXONOMY

Classification of hybrid neural/symbolic architectures, including symbolic-to-neural, neural-to-symbolic, co-routine, rule-guided, embedded-symbolic, and System-1/System-2 styles.

CHRONOS artifact role:

- `NeuroSymbolicMethodRef`
- `CapabilityClassification`

Boundary:

- Can label method family.
- Cannot determine safety, truth, maturity, or authority.

### NSR-SOFT-CONSTRAINT

Differentiable fuzzy-logic and semantic-loss systems such as LTN-like methods.

CHRONOS artifact role:

- `ConstraintEvaluationResult`
- `SoftSatisfactionScore`
- `ExplanationTrace`

Boundary:

- Can produce satisfaction scores and differentiable constraint diagnostics.
- Cannot produce policy admission, final truth, or canonical schema.

### NSR-TRUTH-BOUND

Truth-bound propagation systems such as LNN-like methods that associate formulas and atoms with lower/upper truth bounds and propagate constraints upward/downward through formula structure.

CHRONOS artifact role:

- `TruthBoundAssessment`
- `InconsistencyReport`
- `FormulaTrace`

Boundary:

- Can report local bounds and formula-level inconsistency.
- Cannot guarantee global entailment correctness or rule discovery unless separately validated.

### NSR-SYMBOLIC-ADJUDICATION

Neural-to-symbolic systems such as NeurASP-like architectures where neural outputs propose atoms and a symbolic engine adjudicates constraints.

CHRONOS artifact role:

- `SymbolGroundingAssessment`
- `StableModelSummary`
- `GovernanceDecisionRequest`

Boundary:

- Can separate perception from symbolic reasoning.
- Cannot bypass policy, provenance, model governance, or execution authority.

### NSR-DIFFERENTIABLE-CONSTRAINT-LEARNING

Differentiable combinatorial constraint systems such as SATNet-like approaches.

CHRONOS artifact role:

- `ConstraintCandidate`
- `GroundingRiskReport`
- `LeakageTestResult`

Boundary:

- Can propose learned constraints.
- Must carry anti-leakage and transduction validation.
- Cannot promote apparent grounding as validated grounding.

### NSR-RULE-LEARNING

Rule-learning systems such as dILP-style differentiable inductive logic programming.

CHRONOS artifact role:

- `RuleCandidateProposal`
- `TemplateConstraintReport`
- `ValidationResult`

Boundary:

- Can propose candidate rules.
- Cannot promote learned rules to sourceos-spec, Ontogenesis, policy, or runtime authority without owning-plane review.

### NSR-ONTOLOGY-INFERENCE

Deep ontology or recursive reasoning network approaches that learn embeddings or neural encodings of ontology-relative inference behavior.

CHRONOS artifact role:

- `OntologyDeltaProposal`
- `RelationInferenceCandidate`
- `EmbeddingInferenceReport`

Boundary:

- Can propose ontology deltas or relation candidates.
- Cannot treat embeddings as canonical ontology or explanation-complete reasoning.

### NSR-SYMBOLIC-POLICY

Symbolic regression and deep symbolic policy approaches that propose compact mathematical expressions or policies for control.

CHRONOS artifact role:

- `SymbolicPolicyProposal`
- `ObjectiveAlignmentReport`
- `ControllerAdmissionRequest`

Boundary:

- Can propose policy candidates for routing, cost control, remediation ranking, or cybernetic control.
- Cannot run as a controller until policy and runtime admission have been granted.

## Required carrier status values

CHRONOS carriers should use status values that preserve non-authority:

```text
observed
normalized
candidate
explained
verification_pending
verified
rejected
admission_pending
admitted
receipt_emitted
learning_recorded
```

Only owning authority planes may transition from `candidate` or `verified` to `admitted`.

## Failure-mode labels

Use these labels in fixtures and rollout reports:

```text
soft_score_as_truth
neural_output_as_evidence
learned_rule_as_schema
symbolic_derivation_as_policy_admission
carrier_missing_provenance
embedding_as_ontology_authority
symbolic_policy_as_live_controller
label_leakage_grounding_failure
transduction_unvalidated
```

## Integration requirement

Every neuro-symbolic capability registered under CHRONOS must state:

- method class;
- output artifact type;
- evidence source;
- validation status;
- governance status;
- authority plane;
- replay path;
- explicit forbidden promotion.
