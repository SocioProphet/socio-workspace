# Watson/Cyc/Semantic-Web/CHRONOS Neuro-Symbolic Corpus

Status: seed corpus infrastructure, v0.1.

This corpus captures a research lineage spanning Cyc/common-sense knowledge engineering, Semantic Web and ontology design, Watson/DeepQA and KGQA, CHRONOS/KAIROS event schemas, causal/event knowledge graphs, semantic tables/data lakes, temporal-logic neuro-symbolics, and trustworthy AI/alignment governance.

The corpus is not a marketing document and not an implementation recipe. It is a governed evidence base. Records move through explicit evidence gates before they can generate downstream implementation issues.

## Anchor authors

- Maria Chang
- Michael Witbrock
- Alfio Gliozzo
- Oktie Hassanzadeh
- Rosario Uceda-Sosa

## Promoted coauthor layer

- Achille Fokoue
- Pavan Kapanipathi
- Ibrahim Abdelaziz
- Karthikeyan Natesan Ramamurthy
- Amit Dhurandhar
- Douglas Lenat
- Cynthia Matuszek
- Aldo Gangemi
- Kavitha Srinivas
- Kush Varshney
- Aleksandra Mojsilovic
- Ronny Luss
- Aditya Kalyanpur
- James Fan

## Source-quality gates

Only records with `confirmed_bibliographic`, `confirmed_official`, `confirmed_pdf`, or `confirmed_artifact` may be used as evidence for implementation issues. Records marked `plausible_needs_source` or `speculative_do_not_use` are research leads only.

## Directory map

- `schemas/`: JSON schemas for source quality, authors, papers, artifacts, patents, and graph edges.
- `authors/`: machine-readable author records.
- `papers/`: confirmed paper records and blocked source-confirmation queue.
- `artifacts/`: dataset/system/code/benchmark records.
- `patents/`: patent and design-around records.
- `graph/`: author, paper, venue, artifact, and timeline edge lists.
- `timeline/`: source-normalized chronology seeds.
- `backlog/`: issue candidates and blocked work queues.
- `themes/`: lineage and failure-mode notes.

## Non-copying rule

IBM, Cyc, Watson, and related proprietary systems are treated as source lineage and prior art unless licenses explicitly permit reuse. Patent records are boundary signals, not build instructions.

## Downstream targets

Sociosphere owns corpus governance and issue routing. Downstream consumers include Holmes, Sherlock, Ontogenesis, GAIA, Policy Fabric/Guardrail Fabric, Agentplane, Model Governance Ledger, and DataHub.

## Current limitations

This seed is intentionally incomplete. It establishes infrastructure and a small set of confirmed or blocked records. Full DBLP/OpenAlex/Semantic Scholar/ORCID/patent/artifact normalization remains pending.
