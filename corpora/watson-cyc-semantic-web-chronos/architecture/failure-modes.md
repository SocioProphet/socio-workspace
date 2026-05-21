# Failure Modes and Design Controls

Status: v0.1.

This file records the major historical and architectural failure modes identified across Cyc, Semantic Web, Watson/DeepQA, KGQA, CHRONOS, causal extraction, GraphRAG, cognitive architectures, and agent-control systems.

The goal is not only to absorb strengths from the lineage, but to explicitly design against the failures.

## Cyc

Failure modes:

- knowledge acquisition cost
- ontology maintenance burden
- closed licensing and limited ecosystem participation
- brittle symbolic assumptions
- inference scaling difficulty
- social/governance bottlenecks

Controls:

- open governed corpus intake
- source-quality tiers
- machine-readable evidence
- bounded reasoning budgets
- modular ontology families
- provenance-bearing assertion review

## Semantic Web

Failure modes:

- tooling friction
- ontology politics
- schema drift
- weak developer ergonomics
- RDF/OWL complexity barriers
- incomplete adoption

Controls:

- Ontogenesis compiler approach
- typed schemas and SHACL-like validation
- property graph interoperability
- developer-facing schema emitters
- reusable ontology design patterns

## Watson / DeepQA

Failure modes:

- integration complexity
- pipeline brittleness
- domain-specific tuning cost
- confidence calibration difficulty
- enterprise deployment mismatch

Controls:

- explicit evidence pipelines
- modular architecture
- source-quality propagation
- bounded domain specialization
- governance and audit built-in from the start

## KGQA

Failure modes:

- relation-linking fragility
- entity-linking ambiguity
- schema incompleteness
- semantic parsing brittleness
- query grounding failure

Controls:

- canonical query graphs
- provenance-bearing query plans
- confidence thresholds
- fallback retrieval/evidence modes
- human review for high-impact operations

## CHRONOS / Event Schemas

Failure modes:

- event uncertainty
- weak provenance chains
- schema-instantiation ambiguity
- event prediction hallucination
- causal overclaiming

Controls:

- event confidence and uncertainty fields
- source provenance on every event edge
- candidate vs confirmed event distinction
- evidence-backed event prediction
- causal relation confidence scores

## Causal Extraction

Failure modes:

- spurious causality
- weak transfer across domains
- evaluation fragility
- benchmark overfitting

Controls:

- cross-domain evaluation
- causal evidence spans
- provenance-bearing causal claims
- candidate-only causal edge classes

## GraphRAG

Failure modes:

- incorrect graph extraction
- summary hallucination
- graph contamination
- community summary drift

Controls:

- graph-edge provenance
- extraction confidence
- source-quality propagation
- entity-link validation
- replayable graph build pipeline

## Behavior Trees

Failure modes:

- spaghetti trees
- hidden fallback loops
- decorator abuse
- unreadable blackboard state

Controls:

- subtree registry
- typed blackboard contracts
- risk-tiered branches
- trace replay and linting
- bounded retry policies

## BDI

Failure modes:

- stale or poisoned beliefs
- oscillating intentions
- brittle plan libraries
- goal conflict deadlock

Controls:

- evidence-bound belief revision
- provenance-aware plan adoption
- contradiction handling
- escalation to Holmes deliberation

## AICA

Failure modes:

- unsafe autonomy
- adversarial deception
- uncontrolled escalation
- over-broad actuation

Controls:

- rules of engagement
- simulation-before-execution
- bounded effectors
- reversible actions where possible
- policy and audit gates

## OpenCog / Hyperon

Failure modes:

- integrative sprawl
- self-modification bypass
- uncontrolled graph mutation
- hard-to-audit heterogeneous reasoning

Controls:

- sandboxed graph reasoning
- read-only default graph access
- staged writes
- external policy enforcement
- mutation review and rollback

## FAIR / Provenance

Failure modes:

- FAIR-washing
- metadata without machine-actionability
- stale provenance
- disconnected audit trails

Controls:

- required provenance schema
- persistent identifiers
- versioned records
- source-quality validation
- issue-generation gates

## Trustworthy AI / Alignment

Failure modes:

- governance theater
- metric gaming
- policy/runtime mismatch
- untracked trait drift
- unverifiable explanations

Controls:

- intervention audit records
- trait drift metrics
- explicit policy objectives
- attribution and evidence linkage
- runtime monitoring with rollback
