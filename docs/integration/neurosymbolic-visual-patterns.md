# Neuro-Symbolic Visual Pattern Capture

Status: v0.1 visual-pass capture.

This document records the additional integration patterns found during a visual review of the ASU neuro-symbolic decks and supplements. The earlier text pass captured method families and authority boundaries. The visual pass adds interface patterns that should become CHRONOS boundary objects.

This document does not vendor deck images, reproduce slides, or promote canonical schemas. It records derived integration patterns for downstream vocabulary, evidence, and governance work.

## Summary

The decks contribute more than taxonomy. Their diagrams expose concrete interfaces:

```text
neural perception
  -> symbolic atom candidate
  -> rule / ontology / solver adjudication
  -> governed carrier proposal
  -> verification / policy / replay / receipt
```

The visual material strengthens CHRONOS by naming the boundary objects that sit between neural outputs and symbolic authority.

## Pattern 1: NeuralAtomBoundary

Source pattern: NeurASP-style neural atoms.

The visual interface is direct: raw input is processed by a neural classifier; classifier outputs become probabilities over symbolic atoms; ASP choice rules and constraints adjudicate allowed worlds.

CHRONOS implication:

```text
NeuralAtomBoundary
  -> neural probability output
  -> symbolic atom candidate
  -> symbolic adjudication result
  -> carrier proposal
  -> evidence / policy admission
```

Required fields:

- neural model reference;
- input evidence reference;
- candidate atom namespace;
- probability vector or confidence interval;
- symbolic program / constraint reference;
- adjudication summary;
- non-authority declaration.

Forbidden promotion:

- neural probability output as evidence;
- symbolic atom candidate as truth;
- stable-model result as execution permission.

## Pattern 2: SymbolGroundingAssessment

Source pattern: SATNet visual critique and transduction diagrams.

The diagrams distinguish three grounding hazards:

```text
label leakage
initialization sensitivity
transduction failure
```

CHRONOS implication:

A perception-to-symbol claim requires a grounding assessment before admission.

Required fields:

- leakage assessment;
- transduction assessment;
- masked-output evaluation status;
- held-out grounding validation;
- initialization sensitivity status;
- source of labels / symbolic targets;
- failed-assessment handling.

New failure modes:

- `transduction_certificate_missing`
- `masked_output_not_tested`
- `initialization_sensitivity_unreported`

## Pattern 3: GroundingScope

Source pattern: LTN Real Logic, guarded quantification, and diagonal quantification visuals.

LTN diagrams distinguish constants, tensors, predicates, functions, formulas, quantifiers, masks, and aggregators. For CHRONOS, this becomes scoped evidence evaluation.

CHRONOS implication:

```text
GroundingScope
  -> domain
  -> guard / mask
  -> diagonal pairing rule
  -> aggregation operator
  -> satisfaction semantics
```

This is needed whenever a carrier says a claim holds over:

- a corpus subset;
- a time window;
- a source class;
- a user-approved evidence bundle;
- a graph neighborhood;
- a paired set of observations.

Forbidden promotion:

- unscoped satisfaction as global truth;
- averaged satisfaction as universal proof;
- hidden guard/mask as evidence selection without provenance.

## Pattern 4: TruthRegionCalibration

Source pattern: LNN truth regions and tailored activation-function diagrams.

The LNN visuals show that truth / falsehood / uncertainty depend on alpha, weights, bias, and threshold regions. The supplement also emphasizes that outputs may be intervals rather than scalars.

CHRONOS implication:

```text
TruthRegionCalibration
  -> alpha
  -> lowerBound
  -> upperBound
  -> threshold policy
  -> contradiction state
  -> decision-threshold provenance
```

New failure mode:

- `thresholded_interval_as_hard_truth`

Forbidden promotion:

- interval output as scalar truth;
- thresholded output as policy admission;
- contradiction state ignored in carrier validation.

## Pattern 5: ClauseSpaceProvenance

Source pattern: dILP template, generated-clause, Boolean-flag, and rule-selection diagrams.

A learned rule is a selected point inside a generated clause space. Its provenance must include the template and clause-generation context.

CHRONOS implication:

```text
RuleCandidateProposal
  -> templateRef
  -> generatedClauseCount
  -> selectedClauseRefs
  -> inventedPredicateBudget
  -> inferenceStepLimit
  -> clauseSpacePruning
  -> localMinimaRisk
```

Forbidden promotion:

- learned rule as canonical ontology;
- selected clause as schema;
- training-data loss as general proof.

## Pattern 6: OntologyEmbeddingBoundary

Source pattern: Deep Ontological Networks / Recursive Reasoning Networks visuals.

The decks show Semantic Web stack diagrams, ontology examples, knowledge graph structure, RRN embeddings, and t-SNE visualizations. This strengthens the GAIA + Ontogenesis connection, but also introduces a risk: visual embeddings are persuasive but not evidence.

CHRONOS implication:

```text
OntologyDeltaProposal
  -> source ontology / graph
  -> embedding model reference
  -> relation candidate
  -> inference scope
  -> explanation status
  -> ontology authority handoff
```

New failure mode:

- `visual_embedding_as_evidence`

Forbidden promotion:

- t-SNE cluster as evidence;
- embedding neighborhood as ontology authority;
- neural relation candidate as canonical graph edge.

## Pattern 7: SymbolicPolicyProposal

Source pattern: DSR / DSP expression-tree and symbolic-policy visuals.

The symbolic-policy diagrams show that symbolic expressions can function as interpretable controllers, but the deck also warns that ordinary symbolic regression can fail for control because of objective-function mismatch.

CHRONOS implication:

```text
SymbolicPolicyProposal
  -> expressionTree
  -> rewardObjective
  -> anchorModelRef
  -> actionDimension
  -> objectiveMismatchAssessment
  -> controllerAdmissionState
```

Forbidden promotion:

- symbolic expression as live controller;
- fit-to-trace as policy success;
- controller without safety envelope and replay.

## Pattern 8: SemanticDoubleBus

Source pattern: Semantic Web double-bus architecture visuals.

The product surface and semantic substrate can be separated:

```text
product / agent interaction surface
  -> CHRONOS / Superconscious cognition surface
  -> semantic substrate: GAIA + Ontogenesis + Semantic SerDes
  -> evidence / policy / replay planes
```

CHRONOS implication:

The user-facing workflow can remain product-native while the semantic/evidence machinery runs underneath. This supports our architecture: visible cognition is not the same as ontology, schema, or evidence authority.

## Downstream work

This visual pass should create follow-on work for:

- `SocioProphet/superconscious`: add failure modes for visual embedding, missing transduction certificate, and thresholded interval truth;
- `SocioProphet/ontogenesis`: draft vocabulary for `NeuralAtomBoundary`, `GroundingScope`, `TruthRegionCalibration`, `RuleCandidateProposal`, and `SymbolicPolicyProposal`;
- `SocioProphet/agentplane`: add evidence/replay surfaces for grounding assessments and rule/policy proposals;
- `SocioProphet/gaia-world-model`: capture external source metadata and source graph anchors;
- `SourceOS-Linux/sourceos-spec`: receive only stabilized schemas after Ontogenesis review.

## Non-goals

This document does not implement the interfaces.

This document does not assert that the ASU methods are sufficient for our product claims.

This document does not promote any neuro-symbolic output to evidence, policy, ontology, schema, routing, memory, or runtime authority.
