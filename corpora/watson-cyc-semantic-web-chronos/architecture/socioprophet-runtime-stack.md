# SocioProphet Runtime Stack Doctrine

Status: v0.1 corpus-derived architecture note.

This file converts the Watson/Cyc/Semantic-Web/CHRONOS corpus and the architecture survey into a separation-of-duties runtime doctrine. The controlling rule is that reasoning, evidence retrieval, schema validation, action selection, authorization, audit, and execution are separate machines.

## Stack

```text
FAIR/PROV object store + graph store + vector index
        ↓
Ontogenesis schemas + Sociosphere governance
        ↓
Sherlock evidence retrieval / GraphRAG / diagnostics
        ↓
Holmes deliberation / KGQA / proof / causal reasoning
        ↓
Agentplane BT/BDI control loop
        ↓
Policy Fabric authorization
        ↓
Model Governance Ledger audit
        ↓
SourceOS / ProCybernetica bounded execution
```

## Separation of duties

Holmes reasons but does not actuate.

Sherlock retrieves, ranks, diagnoses, and explains but does not authorize.

Ontogenesis validates schemas, constraints, contracts, ontology mappings, and source-shape rules.

Sociosphere governs corpus intake, source quality, role workflow, release routing, and cross-repo absorption.

Agentplane selects, schedules, and coordinates action through Behavior Tree and BDI-style control structures.

Policy Fabric authorizes, denies, escalates, or constrains action.

Model Governance Ledger records attribution, evidence, drift, interventions, policy decisions, and audit outcomes.

SourceOS and ProCybernetica execute only through bounded, monitored, policy-checked interfaces.

## Design commitments

1. Natural language becomes a provenance-bearing semantic plan, not an ungoverned prompt.
2. Evidence is always source-quality labeled.
3. Every high-impact action has a policy decision and an audit record.
4. Learned behavior may propose; explicit policy must approve.
5. Graph-native reasoning may stage changes; production knowledge writes require validation gates.
6. Adversarial operations use AICA-style mission structure but remain bounded by rules of engagement and reversibility constraints.
7. Runtime monitors can escalate and collect evidence; they cannot silently perform destructive action.

## Primary absorption targets

- Cyc lineage → commonsense substrate, microtheory contexts, assertion review, inference control.
- Semantic Web lineage → interoperable schemas, ontology design patterns, RDF/OWL/SHACL-style validation, provenance semantics.
- Watson/DeepQA lineage → evidence-ranked QA, candidate generation, confidence calibration, pipeline architecture.
- KGQA lineage → AMR/query graphs, relation linking, schema grounding, language-to-knowledge compilation.
- CHRONOS/KAIROS lineage → event schemas, event predictions, provenance-bearing world-event records.
- Causal/table/data-lake lineage → causal extraction, semantic table interpretation, joinable-column search, data-lake discovery.
- Temporal-logic neuro-symbolics → runtime temporal monitors and interpretable trace satisfaction.
- Trustworthy AI/alignment lineage → contextual regulation, trait drift, attribution, explanation, and audit.

## Open questions

- Which repository is the canonical Policy Fabric home: `guardrail-fabric`, a future `policy-fabric`, or another governance repo?
- Does a DataHub repo already exist, or is DataHub a future component inside Sherlock/Ontogenesis/Sociosphere?
- Which Holmes repository should receive KGQA/deliberation work if no canonical Holmes repo exists yet?
- What source-quality threshold is required before each downstream issue can be opened?
