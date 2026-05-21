# Event Schema Instantiation Evaluation

Status: scaffold.

Derived from:
- CHRONOS: A Schema-Based Event Understanding and Prediction System
- WikiCausal
- event-sequence distillation lineage

## Goal

Evaluate whether GAIA/Ontogenesis/Sherlock can represent event-centric claims with arguments, event types, provenance, uncertainty, and schema justification.

## Candidate tasks

- event extraction
- event argument identification
- event type grounding
- source provenance linking
- schema justification generation
- event prediction labeling
- candidate vs confirmed event distinction

## Metrics

- event type accuracy
- argument completion rate
- provenance completeness
- schema justification quality
- unsupported event prediction rate
- evidence-backed event ratio

## Target components

GAIA:
- world-event record
- causal/event relation record

Ontogenesis:
- EventSchema
- EventInstance
- SourceProvenance

Sherlock:
- event evidence panel
- source-quality propagation

Model Governance Ledger:
- event audit record

## Blocking conditions

No production event-ingestion issue should be generated until CHRONOS/WikiCausal artifacts and licenses are reviewed.
