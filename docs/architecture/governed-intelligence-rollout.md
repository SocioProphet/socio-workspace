# Governed Intelligence Rollout

Status: current-main reconciliation of stale rollout branch.  
Owner: `SocioProphet/sociosphere` for cross-repo coordination.  
First validated vertical slice: CHRONOS Evidence Loop.

## Purpose

This document defines the estate-level rollout umbrella for governed intelligence. It coordinates adoption across the evidence, ontology, reasoning, policy, agent-carrier, ledger, and world-model planes without moving ownership of those carrier surfaces into SocioSphere.

The CHRONOS Evidence Loop is the first validated vertical slice of this umbrella. It proves that a governed corpus can be converted into plane-owned, machine-validatable carriers and a customer-safe readout.

## Naming alignment

Product / external term:

```text
CHRONOS Evidence Loop
```

Internal doctrine term:

```text
Corpus-to-Governed-Carrier Loop
```

Implementation artifact family:

```text
corpus-loop v0 / v1 / v1.1
```

Broader umbrella:

```text
Governed Intelligence Rollout
```

## Canonical platform loop

```text
Observe -> Anchor -> Normalize -> Propose -> Explain -> Verify -> Govern -> Act -> Receipt -> Learn
```

This loop is a reference architecture. Individual vertical slices may implement only a bounded subset.

The current CHRONOS Evidence Loop implements a read-only evidence/coordination subset:

```text
Corpus -> Evidence carrier -> Semantic carrier -> Policy carrier -> Agent carrier -> Ledger carrier -> Coordination packet -> Customer-safe readout
```

## Required governance membranes

| Membrane | Registered owner |
|---|---|
| `/architecture/governed-intelligence` | `SocioProphet/sociosphere` |
| `/chronos/evidence-loop` | `SocioProphet/sociosphere` |
| `/sherlock/evidence-answers` | `SocioProphet/sherlock-search` |
| `/holmes/proof-claims` | `SocioProphet/holmes` |
| `/gaia/world-claims` | `SocioProphet/gaia-world-model` |
| `/agents/action-admission` | `SocioProphet/agentplane` |
| `/policy/claim-action-admission` | `SocioProphet/policy-fabric` |
| `/guardrails/evaluation-and-controls` | `SocioProphet/guardrail-fabric` |
| `/ontogenesis/schema-contracts` | `SocioProphet/ontogenesis` |
| `/ledger/governance-records` | `SocioProphet/model-governance-ledger` |

## Adoption status vocabulary

```text
not_started
schema_stubbed
adapter_in_progress
contract_tests_present
vertical_slice_ready
```

## Current adoption projection

| Repository | Role | Current status | Current anchor |
|---|---|---|---|
| `SocioProphet/sociosphere` | coordination surface | `vertical_slice_ready` | CHRONOS Evidence Loop v0/v1/v1.1 manifests, resolver, packet, readout |
| `SocioProphet/sherlock-search` | evidence answers | `contract_tests_present` | source-quality answer trace #58 |
| `SocioProphet/ontogenesis` | schema authority | `contract_tests_present` | corpus event semantics #103 |
| `SocioProphet/policy-fabric` | policy decision carrier | `contract_tests_present` | governed policy decision #85 |
| `SocioProphet/agentplane` | bounded agent carrier | `contract_tests_present` | bounded action loop #184 |
| `SocioProphet/model-governance-ledger` | ledger record carrier | `contract_tests_present` | governance record checks #20 |
| `SocioProphet/holmes` | proof-claim surface | `not_started` | broader governed-intelligence rollout remains pending |
| `SocioProphet/gaia-world-model` | world claims | `not_started` | broader governed-intelligence rollout remains pending |
| `SocioProphet/guardrail-fabric` | guardrail/evaluation controls | `not_started` | broader governed-intelligence rollout remains pending |
| `SocioProphet/slash-topics` | topic profiles | `not_started` | broader governed-intelligence rollout remains pending |

## Canonical object governance matrix

| Object | Source-of-truth repo | Current CHRONOS status |
|---|---|---|
| `SourceQualityAnswerTrace` | `SocioProphet/sherlock-search` | present |
| `CorpusEventSemantics` | `SocioProphet/ontogenesis` | present |
| `GovernedPolicyDecision` | `SocioProphet/policy-fabric` | present |
| `BoundedActionLoop` | `SocioProphet/agentplane` | present as carrier only |
| `GovernanceRecord` | `SocioProphet/model-governance-ledger` | present |
| `CoordinationManifest` | `SocioProphet/sociosphere` | present |
| `ResolutionReport` | `SocioProphet/sociosphere` | present |
| `CustomerReadout` | `SocioProphet/sociosphere` | present |
| `ProofClaim` | `SocioProphet/holmes` | pending broader rollout |
| `WorldClaim` | `SocioProphet/gaia-world-model` | pending broader rollout |
| `GuardrailEvaluation` | `SocioProphet/guardrail-fabric` | pending broader rollout |
| `SlashTopicProfile` | `SocioProphet/slash-topics` | pending broader rollout |

## CHRONOS Evidence Loop as first vertical slice

The CHRONOS Evidence Loop currently provides:

- governed source corpus in `SocioProphet/sociosphere#334`;
- evidence carrier in `SocioProphet/sherlock-search#58`;
- semantic carrier in `SocioProphet/ontogenesis#103`;
- policy carrier in `SocioProphet/policy-fabric#85`;
- bounded agent carrier in `SocioProphet/agentplane#184`;
- ledger carrier in `SocioProphet/model-governance-ledger#20`;
- pinned manifest and live-found resolution report in SocioSphere;
- customer-safe readout and workbench panel in SocioSphere.

This slice is read-only and coordination-only. It does not execute downstream actions.

## Validation

Current local entrypoint:

```bash
make corpus-loop-check
```

Current workflow:

```text
.github/workflows/corpus-loop.yml
```

Governed-intelligence umbrella validation:

```bash
make governed-intelligence-rollout-validate
```

## Non-goals

- SocioSphere does not own all canonical schemas.
- SocioSphere does not own downstream carrier internals.
- The CHRONOS Evidence Loop does not claim live runtime execution.
- The CHRONOS Evidence Loop does not claim autonomous external effects.
- The CHRONOS Evidence Loop does not claim production storage integration.
- The CHRONOS Evidence Loop does not claim completed corpus normalization.
- The CHRONOS Evidence Loop does not claim patent or license clearance.
- `VectorCandidate` and similar candidates remain candidate-only until evidence, proof, and policy gates admit downstream use.

## Relationship to stale PR #311

The older governed-intelligence rollout branch is superseded by this current-main reconciliation. Its valid intent is preserved here, but its adoption statuses are updated to account for the completed CHRONOS Evidence Loop vertical slice.
