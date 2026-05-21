# Issue Candidates

Status: seed backlog. These are issue candidates, not automatically implementation-ready work items.

## Gate rule

Only records with `confirmed_bibliographic`, `confirmed_official`, `confirmed_pdf`, or `confirmed_artifact` can support implementation issues. Records with `plausible_needs_source` or `speculative_do_not_use` can only support research-normalization issues.

## Sociosphere

### Add governed neuro-symbolic corpus intake model

Target repo: `SocioProphet/sociosphere`

Evidence:
- `schemas/source-quality.schema.json`
- `papers/index.jsonl`
- `papers/needs-source-confirmation.jsonl`

Acceptance criteria:
- Source-quality enum is enforced in corpus records.
- Blocked queues exist for unverified records.
- Paper, author, artifact, patent, timeline, and graph records have machine-readable seeds.
- No implementation issue may cite unverified records.

## Ontogenesis

### Add schema families for events, KG diagnostics, semantic tables, ontology patterns, and microtheories

Target repo: Ontogenesis target, pending repo routing.

Evidence-ready records:
- `chang-2024-chronos`
- `uceda-sosa-2025-conceptual-diagnostics`
- `hassanzadeh-2024-wikicausal`
- `abdelmageed-2025-kg2tables` pending full paper-register insertion

Acceptance criteria:
- Define EventSchema, EventInstance, SourceProvenance.
- Define ConceptHierarchyProbe and KGSubgraphRiskFinding.
- Define SemanticTableAnnotationTask and ColumnOntologyLink.
- Keep Cyc microtheory work conceptual until license/source review completes.

## Sherlock

### Add neuro-symbolic evidence and diagnostic planning

Target repo: Sherlock target, pending repo routing.

Evidence-ready records:
- `uceda-sosa-2025-conceptual-diagnostics`
- `hassanzadeh-2024-wikicausal`
- `chang-2024-chronos`

Acceptance criteria:
- Define evidence panels for KG/LLM diagnostics.
- Define event evidence panels.
- Define causal evidence spans.
- Propagate source-quality labels through answers.

## GAIA

### Add event and causal world-model planning

Target repo: GAIA target, pending repo routing.

Evidence-ready records:
- `chang-2024-chronos`
- `hassanzadeh-2024-wikicausal`

Acceptance criteria:
- Define event records with source provenance.
- Define candidate causal event edges with confidence and review state.
- Keep predictions distinct from confirmed events.

## Agentplane / Policy Fabric

### Add blocked scaffold for misalignment-contagion harness

Target repo: Agentplane / Policy Fabric targets, pending repo routing.

Evidence-ready records:
- `chang-2026-misalignment-contagion` is bibliographically seeded as an arXiv preprint, but method/PDF review remains incomplete.

Acceptance criteria:
- Do not implement runtime harness until PDF/method review is complete.
- Define TraitBaseline, TraitDriftMetric, InterventionOutcomeRecord, and PolicyDecision links.
- Log every intervention into Model Governance Ledger.

## Model Governance Ledger

### Add attribution and audit record planning

Target repo: Model Governance Ledger target, pending repo routing.

Evidence-ready records:
- Final-model-only attribution is still not in `papers/index.jsonl`; add record before implementation issue.

Acceptance criteria:
- Define FinalModelAttributionRecord.
- Define ModelInfluenceTrace.
- Define RegulatoryEvidenceRecord.
- Link every governance record to source-quality metadata.

## Blocked implementation areas

- Gliozzo / Watson KGQA implementation: blocked by exact bibliography gaps.
- Witbrock / Cyc inference-control implementation: blocked by source and license review.
- Patent-sensitive enterprise data workflows: blocked by patent metadata and design-around review.
- Artifact reuse: blocked by license review for all non-confirmed artifacts.
