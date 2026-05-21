# Causal Extraction Evaluation

Status: scaffold.

Derived from:
- WikiCausal
- Causal Knowledge Extraction through Large-Scale Text Mining
- Cross-Domain Evaluation of Approaches for Causal Knowledge Extraction
- Knowledge Graph Embeddings for Causal Relation Prediction

## Goal

Evaluate extraction, representation, and validation of causal claims from text, tables, and knowledge graphs.

## Candidate tasks

- cause/effect phrase identification
- causal relation candidate generation
- causal evidence span extraction
- cross-domain robustness
- causal KG link prediction
- candidate vs confirmed causal edge separation

## Metrics

- causal edge precision
- causal edge recall
- evidence span support rate
- unsupported causal claim rate
- cross-domain transfer degradation
- provenance completeness

## Target components

GAIA:
- CausalRelationCandidate
- CausalEventConcept

Sherlock:
- CausalEvidenceSpan
- causal evidence panel

Ontogenesis:
- causal relation schema validation

Model Governance Ledger:
- causal provenance record

## Blocking conditions

No high-impact causal decision workflow should depend on extracted causal edges without provenance, confidence, and review status.
