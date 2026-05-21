# Watson / DeepQA Lineage

Status: theme synthesis; bibliography incomplete.

## Core shift

Watson/DeepQA shifted enterprise AI from static expert systems toward evidence-ranked question answering pipelines.

The important architectural idea is not a single model. It is a pipeline:

- question analysis
- candidate generation
- document and structured retrieval
- feature extraction
- evidence scoring
- answer ranking
- confidence calibration

## Major known figures in current corpus

- Alfio Gliozzo
- Aditya Kalyanpur
- James Fan
- Radu Florian
- Salim Roukos
- Achille Fokoue
- Pavan Kapanipathi
- Ibrahim Abdelaziz

## Known gaps

- exact Watson NLP architecture papers
- exact DeepQA paper inventory
- KGQA overlap normalization
- pipeline patent review
- public artifact and license review

## SocioProphet absorption

Holmes:
- reasoning pipeline
- semantic parsing
- KGQA escalation

Sherlock:
- evidence scoring
- answer ranking
- document/table QA
- confidence propagation

Model Governance Ledger:
- evidence provenance
- confidence records
- explanation traces

## Risks

- integration complexity
- pipeline brittleness
- confidence miscalibration
- enterprise tuning burden

## Controls

- modular interfaces
- source-quality propagation
- provenance-bearing evidence
- bounded reasoning budgets
- explicit evaluation harnesses
