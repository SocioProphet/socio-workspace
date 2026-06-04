# PFK Stack Integration Map

Status: draft control-plane integration map.  
Authority surface: `SocioProphet/sociosphere` proof-apparatus workspace.  
PFK authority: `SocioProphet/Heller-Godel/proof_fabric_kernel/`.

## Purpose

This document defines the initial estate-level integration map for making the Heller-Godel Proof Fabric Kernel (PFK) usable across the SocioProphet proof, platform, memory, policy, execution, and workroom stack without promoting operational receipts into mathematical truth.

The goal is a thin integration membrane, not a new proof authority. Heller-Godel owns PFK. Sociosphere orchestrates the proof workspace. Domain repositories own their mathematics, tests, fixtures, notebooks, papers, and claim boundaries.

## Non-negotiable boundaries

1. PFK schemas are consumed from `SocioProphet/Heller-Godel/proof_fabric_kernel/` at a pinned merged commit SHA.
2. Consumer repositories must not create local authoritative forks of PFK schemas.
3. Schema validity is envelope validity, not theorem evidence.
4. Event-IR traces, ProofArtifact envelopes, claim-ledger rows, calibration bundles, CI status, model summaries, search packets, and memory proposals are not mathematical proof by themselves.
5. Sociosphere may register, route, test, compare, promote, demote, quarantine, archive, and snapshot claims only from emitted evidence and declared domain boundaries.
6. Sociosphere must not silently upgrade a domain claim.
7. Memory and search systems may propose context; they must not promote context into durable truth or theorem-grade evidence without governance.
8. Agent execution must be policy-mediated, evidence-producing, replayable, and bounded by declared authority.

## Authority map

| Layer | Primary repo | Responsibility |
| --- | --- | --- |
| PFK authority | `SocioProphet/Heller-Godel` | Canonical PFK schemas, framework identifiers, claim grammar, anti-seed discipline, dependency pins. |
| Proof workspace controller | `SocioProphet/sociosphere` | Workspace manifest, proof-slice routing, proof adapter validation, gate orchestration, evidence-event normalization, promotion/quarantine/archive decisions, snapshots. |
| Human workroom surface | `SocioProphet/prophet-workspace` | Proof Workroom product semantics, claim/gate/source/artifact views, review UX, attachment of office artifacts and workroom context. |
| Runtime deployment surface | `SocioProphet/prophet-platform` | Production service composition, platform contracts, trust-chain admission composition, dashboards, APIs. |
| Execution control plane | `SocioProphet/agentplane` | Validated bundle execution, placement, run evidence, replay artifacts, proof-gate runs. |
| Governed cognition | `SocioProphet/superconscious` | Recursive planning loop, safe operational traces, memory decision requests, model route requests, AgentPlane evidence handoff. |
| Discovery and reasoning | `SocioProphet/sherlock-search`, `SocioProphet/holmes` | Evidence search packets, claim candidates, explanation traces, contradiction reports, bounded verification artifacts. |
| Memory context | `SocioProphet/memory-mesh` | Review-only learning/context proposals, channel-provenance write gates, scoped context packs. |
| Authority and policy | `SocioProphet/ProCybernetica`, `SocioProphet/policy-fabric`, `SocioProphet/guardrail-fabric`, `SocioProphet/mcp-a2a-zero-trust`, `SocioProphet/agent-registry` | Cybernetic control law, policy packaging, claim/action admission, provider/tool/agent grant decisions, identity/capability/revocation posture. |
| Semantics | `SocioProphet/semantic-serdes`, `SocioProphet/ontogenesis` | Semantic object encoding, truth classes, RDF/OWL/JSON-LD governance, SHACL promotion gates. |
| Runtime/model supply chain | `SocioProphet/lattice-forge`, `SocioProphet/model-governance-ledger`, `SocioProphet/model-router` | Runtime assets, model lifecycle evidence, route decisions, local/hosted model posture, Trust Chain evidence. |
| Transport and graph runtime | `SocioProphet/TriTRPC`, `SocioProphet/tritfabric`, `SocioProphet/meshrush` | Deterministic transport, orchestration/gates, graph-native agent traversal and evidence surfaces. |
| Domain proof engines | `SocioProphet/Heller-Winters-Theorem`, `SocioProphet/Heller-Einstein`, `SocioProphet/Heller-Dirac`, `SocioProphet/bsd-proof-program`, `SocioProphet/np-program`, `SocioProphet/ns-program`, `SocioProphet/hodge-program-proof` | Domain definitions, proof claims, non-claims, obstruction registers, fixtures, notebooks, computations, repo-local gates. |

## Canonical loop

```text
Observe
  -> Anchor
  -> Normalize
  -> Propose
  -> Explain
  -> Verify
  -> Govern
  -> Act
  -> Receipt
  -> Learn
  -> Promote | Quarantine | Archive
```

### Observe

Sources include domain repo fixtures, manuscripts, notebooks, source imports, Lampstand local file evidence, Sherlock search packets, GAIA source records, Orion field events, Regis graph edges, and runtime observations.

### Anchor

Every source-backed item should carry source refs, hashes where available, citation anchors, evidence refs, freshness posture, and sensitivity/handling constraints.

### Normalize

Semantic SerDes, Ontogenesis, and PFK adapters normalize candidate objects into typed envelopes without changing their claim grade.

### Propose

Holmes, domain proof repos, Superconscious, or human operators may propose claims, gates, non-claims, proof artifacts, calibration bundles, and memory context. Proposed objects remain proposed until admitted.

### Explain

Explanation traces should describe evidence used, transformations performed, assumptions, non-claims, contradiction candidates, and next obstruction walls.

### Verify

Verification includes repo-local tests, proof gates, fixture checks, deterministic computations, PFK validators, AgentPlane execution, and calibration runs. Passing verification may support state movement; it does not imply theorem truth by itself.

### Govern

Guardrail Fabric, Policy Fabric, MCP/A2A Zero Trust, Agent Registry, and ProCybernetica authority rules decide whether an action, promotion, route, memory writeback, or public surface is allowed, denied, provisional, or review-required.

### Act

Effectful work is performed by bounded, validated execution surfaces, primarily AgentPlane. Proof work should prefer no-network, deterministic, replayable gates whenever feasible.

### Receipt

Receipts include PFK Event-IR traces, ProofArtifact envelopes, calibration bundles, AgentPlane run/replay artifacts, policy decisions, guardrail decisions, and promotion decisions.

### Learn

Memory Mesh receives review-only proposals. Durable writeback requires explicit approval and must preserve provenance, scope, redaction posture, and writeback posture.

### Promote, quarantine, archive

Sociosphere emits the controller-visible state transition. Promotion by prose alone is forbidden.

## Minimum consumer maturity

| Level | Meaning | Allowed statement | Forbidden statement |
| --- | --- | --- | --- |
| M0 | Citation-only dependency | PFK compatibility target identified. | Native PFK integration complete. |
| M1 | Pinned PFK dependency | Heller-Godel PFK commit SHA and consumed schema identifiers are declared. | Receipts are PFK-native without examples. |
| M2 | Example compatibility | Repo examples validate against one or more PFK schemas. | Full pipeline integration. |
| M3 | Native receipt emission | Normal workflow emits PFK-compatible Event-IR, ProofArtifact, claim-ledger, or calibration outputs. | Theorem-grade evidence. |
| M4 | Migration-disciplined consumer | Dependency pinning, CI validation, migration notes, anti-seed compliance, and replay behavior exist. | PFK validates mathematical correctness. |

## Target repository file set

Each proof-facing domain repository should eventually expose:

```text
PFK_ADAPTER.json
DEPENDENCIES.md
claims/<repo>.claims.jsonl
gates/<repo>.gates.jsonl
nonclaims/<repo>.nonclaims.jsonl
obstructions/<repo>.walls.jsonl
```

The exact schema for `PFK_ADAPTER.json` is owned by Sociosphere under `standards/proof-apparatus/proof-adapter.schema.json`.

## Immediate implementation sequence

1. Land this integration map in Sociosphere.
2. Add PFK authority fields to the Sociosphere proof-adapter schema for PFK consumers.
3. Add a proof repo role catalog to classify proof authority, controller, runtime, memory, policy, semantic, and domain-engine roles.
4. Validate adapter examples before requiring all domain repos to implement the adapter.
5. Add repo-local adapter files to Heller-Winters, BSD, NP, NS, Hodge, Heller-Einstein, and Heller-Dirac in separate domain-owned PRs.
6. Add AgentPlane proof-gate runner support only after adapter examples stabilize.
7. Add Prophet Workspace Proof Workroom UI only after the controller object model is stable.

## Anti-overclaim clause

This map does not add mathematical content. It does not assert progress on any Clay problem. It does not convert Heller-Godel methodology into a proof-transfer theorem. It only defines how proof-facing artifacts can be routed, checked, governed, and reviewed across the estate.
