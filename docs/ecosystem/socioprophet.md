# Repository Analysis — SocioProphet/socioprophet

**GitHub:** https://github.com/SocioProphet/socioprophet  
**Role in ecosystem:** Main collaborative platform  
**Last analysed:** 2026-04-08

---

## 1. Repository Purpose & Identity

### What it does
The main collaborative platform that unifies two sub-systems: **AgentOS** (a layered agent
stack: interfaces, policies, tool registry, Linux integration) and **Agentplane** (a
fleet-shaped control plane for reproducible agent execution).

SocioProphet is also the regulated-domain cognitive control surface for the
ecosystem: the place where users, roles, policies, institutional memory, evidence,
agent capabilities, procedure templates, approvals, and execution receipts are bound
into a governed action system.

The control equation is:

```text
Institutional Action
  = Actor
  + Role
  + Authority
  + Context
  + Evidence
  + Policy
  + Procedure
  + Capability
  + Approval
  + Execution Receipt
```

A SocioProphet action is not first-class unless it can identify who initiated or
approved it, which role or delegation authorized it, what contextual state and
evidence supported it, which policy or procedure constrained it, which tool or agent
capability executed it, what audit receipt proves it, and what replay path can
reconstruct it.

### Core responsibilities
- `agentos/` — interfaces, policy, tool registry, Linux integration runbook, CI definitions.
- `agentplane/` — Nix flake, bundle schema, runner scripts.
- `registry/` — canonical tool registry (YAML + CSV); "compliance + inventory source of
  truth".
- `inventory/` — stack inventory + RACI.
- `workspaces/` — workspace controllers (socio-linux + socioprophet) as Nix-first stubs.
- `socioprophet-web/` — Firebase-backed web client; deny-by-default Firestore rules.
- Security enforcement: Firestore emulator-backed tests, Gitleaks, CodeQL.
- Regulated-domain workspace governance — bind users, roles, policies, procedure
  templates, evidence bundles, approvals, and execution receipts into auditable
  workflows.
- Evidence-grounded institutional reasoning — combine public evidence, internal
  policy, case context, and authority boundaries before any high-stakes
  recommendation or action.
- Procedure templates — elevate prompt templates into governed institutional
  procedures with required inputs, evidence, policy basis, approval gates, and audit
  schema.
- Human-in-command execution — agents may synthesize, draft, route, validate, and
  execute bounded tasks, but institutional authority remains visible and reviewable.
- Evaluation and replay — workflow-level benchmarks, adversarial tests, replay
  artifacts, and governance checks are required before claims of operational
  readiness.

### What systems depend on it
- Users of the SocioProphet platform (web client consumers).
- `prophet-platform` — links to `socioprophet-web` as a deployable app.
- `sociosphere` — manifest includes `socioprophet-web` as a component.

### What it depends on
- Firebase / Google Firestore (`.firebaserc`, `firebase.json`)
- Nix (`flake.nix`) for reproducible dev environments
- TriTRPC (protocol layer, referenced through agentplane sub-system)
- Webpack (web client build)

### Key files
- `README.md` — layout overview, AgentOS / agentplane unification
- `docs/architecture.md` — 3 design principles + component breakdown
- `agentos/interfaces/` — AgentOS interface definitions
- `agentos/policy/` — policy declarations
- `agentos/registry/` — tool registry
- `registry/agentos-tool-registry.yaml` — canonical tool registry (validated by
  `scripts/validate_registry.py`)
- `agentplane/bundles/` — bundle schema and example agent
- `firebase.json` + `socioprophet-web/firestore.rules` — security posture
- `flake.nix` — Nix dev environment

---

## 2. Controlled Vocabulary & Ontology

### Key terms
| Term | Definition | Source |
|---|---|---|
| **AgentOS** | Layered agent stack: interfaces, policy, tool registry, Linux integration | `README.md` |
| **Agentplane** | Fleet-shaped control plane for reproducible execution | `README.md` |
| **Tool registry** | Canonical YAML + CSV listing of agent tools; compliance + inventory source of truth | `registry/` |
| **Agentplane bundle** | "The unit of deployment/execution across your executor fleet" | `README.md` |
| **AIWG artifacts** | System-of-record from agentic working group | `README.md` |
| **Agentplane evidence artifacts** | Validation/Placement/Run artifacts from execution | `README.md` |
| **Auditable trail** | Reconciled AIWG + agentplane artifact chain | `README.md` |
| **RACI** | Responsibility, Accountability, Consulted, Informed inventory matrix | `inventory/` |
| **window.__FIREBASE_CONFIG__** | Runtime Firebase config injection (not build-time) | `docs/architecture.md` |
| **Deny-by-default** | Firestore security posture: explicit allow rules only | `docs/architecture.md` |
| **Regulated-domain cognitive control fabric** | Governed workspace where institutional knowledge, policy, evidence, roles, procedures, agents, approvals, and execution receipts compose into auditable action | Ecosystem enrichment |
| **Institutional Action** | Complete action object: actor + role + authority + context + evidence + policy + procedure + capability + approval + receipt | Ecosystem enrichment |
| **Actor** | Human, agent, service account, organization, or delegated process initiating or participating in an action | Ecosystem enrichment |
| **Role** | Governance identity that determines authority, permitted tools, approval rights, and visibility | Ecosystem enrichment |
| **Authority boundary** | Explicit limit on what an actor or agent may decide, draft, execute, approve, or merely recommend | Ecosystem enrichment |
| **Policy basis** | Institutional rule, standard, pathway, contract, regulation, or doctrine supporting a recommendation or action | Ecosystem enrichment |
| **Evidence bundle** | Versioned source material, citations, retrieved context, artifacts, logs, and validation outputs supporting a decision or execution | Ecosystem enrichment |
| **Procedure template** | Governed workflow template with required inputs, policy basis, evidence requirements, output schema, approval gate, and replay test | Ecosystem enrichment |
| **ApprovalEvent** | Recorded human or institutional approval binding an action to accountable authority | Ecosystem enrichment |
| **OverrideEvent** | Recorded exception where an authorized actor overrides a recommendation, policy default, route, or agent proposal | Ecosystem enrichment |
| **ExecutionReceipt** | Hashable record proving what tool, agent, workflow, or infrastructure path executed an action | Ecosystem enrichment |
| **GovernanceBench** | Evaluation suite measuring authority boundaries, evidence requirements, policy gates, and audit expectations | Ecosystem enrichment |
| **WorkflowBench** | Evaluation suite measuring performance on realistic institutional workflows, not isolated model answers | Ecosystem enrichment |
| **ReplayBench** | Evaluation suite proving decisions and executions can be reconstructed from retained evidence and receipts | Ecosystem enrichment |

### Domain-specific language
- The tool registry is the **compliance source of truth** — bundles reference it, not the
  other way around.
- Firebase rules are **test-backed**: emulator rules tests must pass in CI before merge.
- Runtime config injection prevents **build-time secret taint**.
- AgentOS and agentplane are **complementary, not redundant**: AgentOS answers "what is
  allowed?", agentplane answers "where does it run and where is the evidence?".
- SocioProphet adds the institutional-control questions: "who authorized it?",
  "what evidence supports it?", "which policy governs it?", "which procedure shaped
  it?", and "what receipt proves it?".
- Prompt templates should not remain informal prompts. They should become
  `ProcedureTemplate` objects with input contracts, evidence requirements, authority
  gates, and replay tests.
- High-stakes recommendations require explicit separation between synthesis,
  recommendation, approval, and execution.
- Enterprise regulated-domain AI products demonstrate a useful pattern: secure
  workspace, evidence retrieval, institutional policy alignment, reusable templates,
  access governance, data controls, audit logs, and domain-expert workflow
  evaluation. SocioProphet should generalize this as an open, graph-native,
  provider-independent governance fabric rather than as a centralized SaaS boundary.

### Semantic bindings to other repos
- **↔ agentplane** (standalone repo): socioprophet contains an agentplane sub-directory;
  defines AgentOS tool registry that agentplane bundles reference.
- **→ sociosphere**: socioprophet-web is a component in sociosphere's manifest.
- **→ prophet-platform**: prophet-platform deploys socioprophet-web as an app.

---

## 3. Topic Modeling

| Topic | Keywords | Weight |
|---|---|---|
| Agent infrastructure | AgentOS, tool registry, interfaces, policy, linux, RACI | dominant |
| Execution control plane | agentplane, bundle, validate, place, run, evidence, replay | dominant |
| Security / compliance | Firebase rules, deny-by-default, Gitleaks, CodeQL, emulator tests | high |
| Web platform | socioprophet-web, webpack, Firebase, Firestore | high |
| Reproducible environments | Nix flake, Fedora Silverblue, Lima, immutable OS | medium |
| Knowledge commons | knowledge graph, provenance, attribution, local-first, federation | medium (planned) |
| Agentic audit trail | AIWG artifacts, evidence artifacts, auditable trail | medium |
| Regulated-domain governance | roles, authority, policy basis, approval, override, audit, compliance | high |
| Evidence-grounded reasoning | evidence bundle, citation, provenance, public evidence, institutional policy, case context | high |
| Procedure templates | workflow template, required inputs, output schema, approval gate, replay test | high |
| Human-in-command control | recommendation boundary, approval event, override event, accountable authority | high |
| Evaluation / red-team governance | WorkflowBench, GovernanceBench, ReplayBench, adversarial tests, institutional simulations | medium-high |
| Sovereign enterprise AI pattern | open control plane, graph-native governance, non-SaaS portability, provider independence | medium |

---

## 4. Dependency Graph

### Direct dependencies
- Firebase / Firestore (runtime storage + auth)
- Nix (dev environment)
- Webpack (web client build)
- TriTRPC (protocol, referenced through agentplane sub-system)

### Semantic governance dependencies
- `sociosphere` — canonical ecosystem inventory, repo intelligence index, workspace
  topology, and governance graph.
- `hellgraph` — graph reasoning layer for querying actors, roles, policies, evidence
  bundles, authority boundaries, and release-readiness state.
- `socioprophet-standards-knowledge` — upstream vocabulary and schema authority for
  institutional memory, evidence context, provenance, and semantic object models.
- `socioprophet-standards-storage` — storage invariants for evidence bundles,
  receipts, hashes, artifacts, and retention posture.
- `agentplane` — execution and replay substrate for tool and agent actions.
- `prophet-platform` — deployment, validation, release-readiness, and environment
  binding.

### Dependent systems
- `prophet-platform` — deploys `apps/socioprophet-web`
- `sociosphere` — lists `socioprophet-web` as managed component

### Cross-repo impact when socioprophet changes
- Tool registry changes → agentplane bundles referencing changed tools must update.
- AgentOS interface changes → all consumers of those interfaces must update.
- Firebase rules changes → security posture shift; requires emulator test pass.

---

## 5. Change Impact Rules

| What changed | Downstream repos affected | DevOps actions | Governance gates |
|---|---|---|---|
| `registry/` tool registry | agentplane (bundles referencing changed tools) | Re-validate bundles | Registry version bump; RACI review |
| `agentos/interfaces/` | Any service implementing those interfaces | Rebuild + test all AgentOS consumers | Interface versioning; ADR |
| `agentos/policy/` | Policy enforcement throughout the stack | Policy regression tests | Security review gate |
| `socioprophet-web/firestore.rules` | Socioprophet-web + any Firestore consumer | Emulator rules test + Gitleaks must pass | Security review mandatory before merge |
| `flake.nix` | Dev environment reproducibility | Nix build validation | Lock hash update |
| `agentos/policy/` authority or governance rule | agentplane, sociosphere, prophet-platform, standards-knowledge | Re-run policy regression tests; regenerate governance graph; validate affected procedure templates | Security + governance review mandatory |
| `registry/` tool capability or permission metadata | agentplane bundles, ProcedureTemplate objects, WorkflowBench fixtures | Re-validate bundles and template/tool bindings | Registry version bump; RACI and authority-boundary review |
| Procedure template schema or governed workflow | socioprophet-web, agentplane, standards-knowledge, standards-storage | Validate required inputs, evidence bundle schema, output schema, approval gates, replay test | Domain-owner approval required |
| Evidence bundle or receipt schema | standards-storage, agentplane, hellgraph, prophet-platform | Validate serialization, hashing, replay, retention, and graph ingestion | Evidence-chain review mandatory |
| Role / Actor / ApprovalEvent / OverrideEvent model | socioprophet-web, sociosphere, hellgraph, AgentOS policy | Rebuild access-control tests and graph queries | Governance review mandatory |
| High-stakes recommendation workflow | AgentOS policy, ProcedureTemplate registry, WorkflowBench/GovernanceBench | Run adversarial tests, uncertainty tests, citation/provenance checks, and human-approval path tests | Human-in-command gate mandatory |
