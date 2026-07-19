# Inspection Without Inspection Standard v0.1

Status: draft standard
Owner: SocioSphere
Scope: privacy-bounded inspection, debugging, monitoring, and audit workflows across the SocioProphet estate

## 1. Purpose

Inspection Without Inspection converts any request to inspect private, decentralized, restricted, or otherwise non-exportable data into a governed proxy-artifact workflow.

The standard exists to prevent two failure modes:

1. privacy collapse, where raw private examples leak into debugging, labeling, monitoring, or audit artifacts; and
2. narrative collapse, where a claimed model/data issue is discussed without an executable selection predicate, diagnostic signature, privacy envelope, and comparison ledger.

## 2. Non-negotiable invariants

1. Raw private examples MUST NOT be exported as inspection artifacts.
2. Every inspection claim MUST declare a task identifier from T1 through T6.
3. Every task instance MUST declare an executable selection predicate.
4. Every proxy artifact touching private/decentralized data MUST declare a user-level DP envelope or a documented reason the DP envelope is not applicable.
5. Every proxy artifact MUST declare private-data touchpoints and post-processing boundaries.
6. Every publication candidate MUST pass a memorization/leakage gate or be quarantined.
7. T6 likelihood-ratio workflows MUST use a generator family that exposes likelihood scoring, such as `logp(x)`. Implicit samplers MUST NOT be promoted as likelihood-ratio evidence.
8. Fidelity requirements MUST be declared before the artifact is interpreted.
9. Every diagnostic conclusion MUST map to a controlled fault class.
10. Every artifact comparison MUST be ledgered with provenance and prior-artifact references.

## 3. Task taxonomy

| ID | Name | Selection criterion pattern | Default fidelity posture |
|---|---|---|---|
| T1 | sanity_check | random or representative examples from the training distribution | low to medium |
| T2 | mistake_debugging | examples selected by error, misclassification, uncertainty, or failed prediction | low to medium |
| T3 | unknown_or_oov | examples selected by unknown label, OOV token, unsupported class, or parser failure | low to medium |
| T4 | poor_slice_performance | devices, users, cohorts, slices, or examples associated with low performance | low to medium |
| T5 | human_labeling | unlabeled examples intended for annotation or training use | high |
| T6 | distribution_mismatch | examples dense under private/decentralized distribution and sparse under public/training distribution | medium to high |

## 4. Canonical control loop

```text
REGISTER_TASK
  -> COMPILE_SELECTION
  -> TRAIN_PROXY
  -> VALIDATE_DP_ENVELOPE
  -> RUN_MEMORIZATION_GATE
  -> GENERATE_OR_SCORE
  -> COMPARE_ARTIFACTS
  -> DIAGNOSE_FAULT_CLASS
  -> LEDGER_ATTESTATION
  -> PUBLISH_OR_QUARANTINE
```

## 5. Required object model

### 5.1 TTask

A `TTask` declares the inspection intent. It MUST include:

- `task_id`: one of `T1`, `T2`, `T3`, `T4`, `T5`, `T6`.
- `task_name`: canonical lowercase name.
- `selection_predicate_id`: reference to the predicate used to construct the proxy-training slice.
- `expected_diagnostic_signature`: falsifiable expectation to compare against generated samples, scores, or deltas.

### 5.2 SelectionPredicate

A `SelectionPredicate` compiles a claim into execution. It MUST include:

- `predicate_id`.
- `language`: `python`, `sql`, `rego`, `jsonlogic`, or `dsl`.
- `device_selection_rule_ref` when device/cohort selection is needed.
- `local_filter_rule_ref` when per-device filtering is needed.
- `hash` for reproducibility.
- `raw_private_examples_exported`: MUST be `false`.

### 5.3 DPEnvelope

A `DPEnvelope` declares privacy accounting. It SHOULD include:

- `epsilon`.
- `delta`.
- `user_level`.
- `clip_parameter_s`.
- `rounds`.
- `participants_per_round_qn`.
- `population_n`.
- `noise_multiplier_z`.
- `accountant`.

If DP is not applicable, the artifact MUST state why and MUST still declare private-data touchpoints.

### 5.4 ProxyArtifact

A `ProxyArtifact` is the publishable evidence proxy. It MUST include:

- standard name and version.
- task declaration.
- selection predicate declaration.
- generator declaration.
- DP envelope.
- privacy boundary.
- fidelity declaration.
- safety gates.
- provenance.
- comparison ledger.

### 5.5 ArtifactComparison

An `ArtifactComparison` records a structured delta across time, slices, model versions, public/private baselines, or control/treatment conditions.

### 5.6 FaultClass

A `FaultClass` maps evidence to a controlled diagnostic vocabulary. Initial values:

- `TokenBoundaryMerge`
- `OOVInflation`
- `NormalizationBug`
- `PixelInversion`
- `SliceUndercoverage`
- `TrainServeMismatch`
- `PublicPrivateDistributionGap`
- `LabelCoverageFailure`
- `MemorizationLeakage`

## 6. Generator capability policy

Generator families are capability-bearing objects.

`explicit_likelihood` generators MUST expose:

- `sample()`
- `logp(x)`

They MAY support T6 likelihood difference scoring:

```text
score(x) = log p_private(x) - log p_public(x)
```

`implicit_sampler` generators MUST expose:

- `sample()`

They MAY support discriminator-style comparisons, but MUST NOT be used as likelihood-ratio evidence unless an explicit likelihood adapter is declared.

## 7. Fidelity policy

Every artifact MUST declare `fidelity_required` as `low`, `medium`, or `high`.

Low-fidelity proxy samples MAY be sufficient for bug classes where the diagnostic signal is coarse, such as pixel inversion, token-boundary merge, or gross normalization errors.

High-fidelity artifacts are REQUIRED for tasks where generated outputs will be used for labeling, training, or fine-grained representational claims.

## 8. Memorization and leakage policy

Every publication candidate MUST include a memorization audit reference. Acceptable initial gates include:

- nearest-neighbor leakage check;
- duplicate or near-duplicate rejection;
- canary or membership-risk audit;
- manual quarantine decision with documented reason.

If the artifact reproduces private examples, the artifact MUST be quarantined.

## 9. Publication decisions

`publication_decision` MUST be one of:

- `publish`
- `review`
- `quarantine`

A `publish` decision requires:

- `raw_private_examples_exported=false`;
- DP envelope present or documented non-applicability;
- private-data touchpoints declared;
- post-processing boundary declared;
- memorization audit present;
- fidelity requirement declared;
- fault class declared when a diagnostic claim is made.

## 10. Estate mapping

- SocioSphere: canonical standard, schemas, examples, validation lane.
- Policy Fabric: publication, privacy-budget, memorization, and capability policies.
- AgentPlane: executor contracts and capability routing.
- Ontogenesis: RDF/OWL/SHACL representation and fault-class vocabulary.
- Gaia World Model: public/private coverage-gap and world-model inspection profiles.
- Alexandrian Academy: curriculum and canonization.
- ProCybernetica: defensive audit controls.

## 11. Minimal implementation profile

The minimum useful implementation ships three fixtures:

1. T3 OOV char-LM diagnostic.
2. T4 slice-contrast implicit sampler diagnostic.
3. T6 likelihood difference lens.

These fixtures exercise the standard's main boundaries: task typing, predicate compilation, DP declaration, generator capability enforcement, fidelity declaration, memorization gate, comparison ledger, and publication routing.
