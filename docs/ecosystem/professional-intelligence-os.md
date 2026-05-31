# Professional Intelligence OS Topology

## Purpose

This document registers Professional Intelligence OS as a managed Sociosphere ecosystem surface.

Sociosphere does not own every subsystem. It owns the cross-repo topology view, governance graph, and integration posture so platform, delivery, workspace, policy, agent, model, memory, search, query, and domain-pack work can be reasoned about as one system.

## Managed topology

### Delivery governance spine

- `SocioProphet/delivery-excellence`
- `SocioProphet/delivery-excellence-automation`
- `SocioProphet/delivery-excellence-boards`
- `SocioProphet/delivery-excellence-innersource`
- `SocioProphet/delivery-excellence-bounties`

Role: operating model, boards, work orders, KPIs, repo readiness, playbooks, bounties, and demo acceptance.

### Runtime and deployment spine

- `SocioProphet/prophet-platform`
- `SocioProphet/TriTRPC`
- `SocioProphet/tritfabric`
- `SocioProphet/prophet-cli`
- `SocioProphet/homebrew-prophet`

Role: runtime services, platform contracts, transport, validation, install path, and deployment topology.

Current runtime-boundary anchor: `SocioProphet/prophet-platform:docs/WORKROOM_UPDATE_RUNTIME_BOUNDARY.md` defines prerequisites before the workroom update contract can become a live service. It does not define an endpoint, service, persistence model, or mutation path.

### Work surface and UI

- `SocioProphet/prophet-workspace`
- `SocioProphet/socioprophet`
- `mdheller/socioprophet-web`
- `SocioProphet/sherlock-search`
- `SocioProphet/speechlab`

Role: professional workrooms, public/operator UI, dashboarding, search/discovery, and voice/work capture surfaces.

Current contract anchor: `SocioProphet/prophet-workspace:docs/workroom-substrate-alignment-v0.md` aligns Professional Workrooms to recovered privacy, memory, topic-pack, audio-review, agent, model-governance, estate-ledger, and learning-receipt surfaces without moving those authority planes into `prophet-workspace`.

### Governed AI execution

- `SocioProphet/agentplane`
- `SocioProphet/agent-registry`
- `SocioProphet/model-router`
- `SocioProphet/guardrail-fabric`
- `SocioProphet/model-governance-ledger`
- `SocioProphet/memory-mesh`

Role: workflow execution, agent identity and authority, model routing, guardrails, model/action evidence, memory recall and writeback.

### Policy, obligations, and risk

- `SocioProphet/policy-fabric`
- `SocioProphet/contractforge`
- `SocioProphet/regis-entity-graph`
- `SocioProphet/ontogenesis`

Role: executable policy, obligation semantics, entity graph, ontology, conflict/risk inputs, and information-boundary governance.

### Query, knowledge, and domain packs

- `SocioProphet/prophet-core-query`
- `SocioProphet/lattice-forge`
- `SocioProphet/semantic-serdes`
- `SocioProphet/graphbrain-contract`
- `SocioProphet/gaia-world-model`
- `SocioProphet/orion-field-intelligence`
- `SocioProphet/human-digital-twin`
- `SocioProphet/slash-topics`
- `SocioProphet/new-hope`

Role: query fabric, semantic serialization, graph/ontology contracts, real-assets and field intelligence packs, human/context models, topic routing, and domain-specific intelligence.

## Integration definition

A subsystem is integrated only when it has:

1. a contract or manifest entry;
2. a runtime, workflow, or validation touchpoint;
3. a governance owner;
4. evidence output or evidence reference;
5. a feedback path into DelEx boards, KPIs, or readiness;
6. a corrective control when telemetry or validation shows drift.

For Professional Workrooms, the current integration evidence is contract-level and runtime-boundary-level rather than runtime-implementation-level:

- `SocioProphet/prophet-workspace:contracts/workspace/professional-workroom.schema.json`
- `SocioProphet/prophet-workspace:contracts/workspace/professional-workroom.v0.1.example.json`
- `SocioProphet/prophet-workspace:tools/validate_professional_workrooms.py`
- `SocioProphet/prophet-workspace:.github/workflows/professional-workrooms.yml`
- `SocioProphet/prophet-platform:contracts/workspace/workroom-update-request.example.json`
- `SocioProphet/prophet-platform:contracts/workspace/workroom-update-response.accepted.example.json`
- `SocioProphet/prophet-platform:contracts/workspace/workroom-update-response.invalid-runtime-mutation.example.json`
- `SocioProphet/prophet-platform:tools/validate_workroom_update_contract.py`
- `SocioProphet/prophet-platform:docs/WORKROOM_UPDATE_RUNTIME_BOUNDARY.md`
- `SocioProphet/workspace-inventory:inventory/estate-overlays/prophet-workspace-workroom-substrate.yaml`
- `SocioProphet/workspace-inventory:inventory/estate-overlays/prophet-platform-workroom-update-boundary.yaml`
- `SocioProphet/systems-learning-loops:kb/receipts/prophet-workspace-workroom-substrate.receipt.yaml`
- `SocioProphet/systems-learning-loops:kb/receipts/prophet-platform-workroom-update-boundary.receipt.yaml`

The invalid mutation fixture is a regression guard: it proves `accepted_for_review` cannot carry `runtimeMutationPerformed: true`.

## Cybernetic control loops

### Delivery loop

Signal -> Intake -> Board Item -> Work Order -> PR -> Validation -> Evidence -> Demo Acceptance -> KPI Update

### Runtime loop

Playbook -> Context Resolve -> Policy Check -> Agent Step -> Workroom Update -> Evidence Receipt -> Adoption Event

### Governance loop

Obligation or Policy -> Decision -> Enforcement -> Evidence -> Exception -> Review -> Updated Policy

### Intelligence loop

Search, Memory, Graph, and Query -> Context Pack -> Agent Output -> Human Feedback -> Adoption Event -> Playbook, Policy, or Model Update

## Current completion readout

As of 2026-05-30:

- Overall Professional Intelligence OS alignment: 27%
- Architecture spine: 41%
- DelEx governance and operating model: 40%
- DelEx automation: 25%
- Platform contracts: 35%
- Professional Workroom contract alignment: 45%
- Workroom runtime-boundary readiness: 20%
- Governance loops: 31%
- Cybernetic controls: 21%
- SocioProphet UI/dashboard integration: 8%
- Sociosphere topology integration: 26%
- Agentplane execution integration: 15%
- Policy Fabric integration: 25%
- ContractForge / Obligation Ledger integration: 25%
- Runtime implementation: 5%
- Demo readiness: 12%

The increase reflects contract-level, runtime-boundary, and governance-ledger alignment only. It does not represent runtime service implementation, UI integration, deployment, live mutation, or demo completion.

## Control references

- Platform manifest: `SocioProphet/prophet-platform:professional-intelligence.manifest.yaml`
- DelEx control register: `SocioProphet/delivery-excellence:docs/professional-intelligence-control-register.md`
- UI definition: `SocioProphet/socioprophet:docs/professional-intelligence-ui-dashboard.md`
- Workspace boundary: `SocioProphet/prophet-workspace:docs/professional-workrooms.md`
- Workroom substrate alignment: `SocioProphet/prophet-workspace:docs/workroom-substrate-alignment-v0.md`
- Workroom update runtime boundary: `SocioProphet/prophet-platform:docs/WORKROOM_UPDATE_RUNTIME_BOUNDARY.md`
- Workspace estate overlay: `SocioProphet/workspace-inventory:inventory/estate-overlays/prophet-workspace-workroom-substrate.yaml`
- Platform runtime-boundary estate overlay: `SocioProphet/workspace-inventory:inventory/estate-overlays/prophet-platform-workroom-update-boundary.yaml`
- Workroom learning receipt: `SocioProphet/systems-learning-loops:kb/receipts/prophet-workspace-workroom-substrate.receipt.yaml`
- Workroom runtime-boundary learning receipt: `SocioProphet/systems-learning-loops:kb/receipts/prophet-platform-workroom-update-boundary.receipt.yaml`

## Sociosphere responsibilities

Sociosphere should:

- index the managed repo map;
- expose topology and governance relationships;
- track whether a repo is source-of-truth, runtime, UI, staging, or integration-only;
- prevent duplicated ownership between platform, workspace, agent, policy, contract, and delivery repos;
- surface drift when a repo claims integration without contracts, validation, evidence, or feedback loops.

## Non-goals

- Do not turn Sociosphere into the canonical home for all Professional Intelligence schemas.
- Do not duplicate DelEx control registers or Prophet Platform manifests.
- Do not count a README reference as integration.
- Do not count workroom contract alignment as runtime implementation or demo readiness.
- Do not count runtime-boundary readiness as runtime implementation.
- Do not mark demo readiness without evidence and adoption telemetry.
