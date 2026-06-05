# Repository Analysis — SocioProphet/prophet-platform

**GitHub:** https://github.com/SocioProphet/prophet-platform  
**Role in ecosystem:** Runtime/deployment hub and release-readiness validator surface  
**Last analysed:** 2026-06-05

---

## 1. Repository Purpose & Identity

### What it does
Prophet Platform is the runtime and deployment hub for the SocioProphet platform. It is a
thin platform monorepo: deployable services live in `apps/`, platform-facing event,
evidence, and receipt contracts live in `contracts/`, deployment wiring lives in `infra/`,
platform guidance lives in `docs/`, validation helpers live in `tools/`, and shared runtime
bindings live in `libs/`.

Its governance role is to turn upstream standards and graph-backed governance state into
product/API contracts, deployment gates, release-readiness summaries, and operator-facing
admission decisions. Standards and ontology authority stay upstream; Prophet Platform owns
runtime deployment, service composition, product/API invocation contracts, and platform-side
validators.

In the institutional-action chain, Prophet Platform does not author policy, topology,
execution evidence, or ontology terms. It consumes them:

```text
SocioProphet records InstitutionalAction
Sociosphere indexes topology and authority boundaries
Ontogenesis defines vocabulary and shapes
HellGraph serves graph-backed governance state
AgentPlane emits execution and replay evidence
Prophet Platform validates and exposes release/admission surfaces
```

### Core responsibilities
- `apps/` — deployable services: API, gateway, web portal, search/index daemons, and
  execution-related services.
- `apps/api` — long-lived platform API service.
- `apps/gateway` — HTTP/WebSocket edge bridge relaying over TriTRPC/UDS.
- `apps/socioprophet-web` — web portal surface.
- `contracts/` — platform-facing event, evidence, receipt, validation, and admission
  contracts consumed by runtime services.
- `docs/` — platform-level guidance: architecture, transport binding, security,
  evaluation fabric, channel gates, trust chain, and runtime boundaries.
- `infra/` — Kustomize, Argo CD appsets, namespaces, and deployment wiring.
- `tools/` — validation and smoke-test helpers; `standards.lock.yaml` gates platform drift.
- `libs/` — small runtime bindings adapting pinned upstream standards into platform code.
- Runtime and deployment ownership for Professional Intelligence / Workroom surfaces while
  product semantics, workspace topology, policy, memory, and receipt authority remain in
  their owning repos.
- Release-readiness validators for graph-backed governance state: evidence bundles,
  execution receipts, procedure templates, trust-chain admission, environment validation,
  channel-governed runtime gates, and integration-drift posture.
- Product/API invocation contracts for governed validation without falsely claiming live
  infrastructure, runtime mutation, production certification, or agent autonomy from
  fixtures alone.

### What systems depend on it
- Browser clients and operators consuming the gateway, API, portal, and Argo CD deployment
  surfaces.
- `socioprophet` — deployment target for institutional-action UI/API surfaces.
- `sociosphere` — consumes platform readiness posture and depends on Prophet Platform to
  expose deployment/readiness facts rather than duplicating runtime responsibility.
- `hellgraph` — supplies graph-backed governance state that Prophet Platform must query for
  release/admission decisions.
- `agentplane` — supplies execution, synthetic environment, run, replay, and receipt evidence
  referenced by platform validators.
- `socioprophet-standards-storage` and `socioprophet-standards-knowledge` — upstream storage
  and knowledge-context standards consumed by platform contracts.
- Platform evaluation, observability, and competition-intelligence consumers.

### What it depends on
- **TriTRPC** — normative transport and platform-specific stream binding; `docs/TRITRPC_SPEC.md`
  and `docs/TRITRPC_PLATFORM_BINDING.md` describe the platform binding.
- **socioprophet-standards-storage** — storage standards and integration blueprint.
- **socioprophet-standards-knowledge** — knowledge-context, provenance, and semantic standards.
- **sociosphere** — workspace/environment state, topology, authority boundaries, and canonical
  repo estate posture.
- **hellgraph** — graph-backed release-readiness, semantic activation, semantic diff,
  provenance, and replay state.
- **agentplane** — execution, environment validation, synthetic run, replay, and receipt
  evidence.
- Kubernetes, Kustomize, and Argo CD for deployment.
- Vue 3 + Vite for portal surfaces.

### Key files
- `README.md` — runtime/deployment hub overview and reading order.
- `docs/ARCHITECTURE.md` — wire, browser access, portal, k8s, and security posture.
- `docs/TRITRPC_SPEC.md` — platform-pinned TriTRPC reference.
- `docs/TRITRPC_PLATFORM_BINDING.md` — platform-specific TriTRPC runtime binding.
- `professional-intelligence.manifest.yaml` — cross-repo runtime/platform ownership manifest.
- `docs/WORKROOM_UPDATE_RUNTIME_BOUNDARY.md` — runtime boundary for workroom update contracts.
- `docs/PLATFORM_EVAL_FABRIC.md`, `docs/LOCAL_DEV_EVAL_FABRIC.md`, and
  `docs/EVAL_FABRIC_GOVERNANCE.md` — evaluation, observability, and competition-intelligence lane.
- `docs/SVF_VALIDATE_CHANGE_AGENT_CONTRACT.md` — Sovereign Validation Fabric agent contract.
- `docs/standards/PROPHET_TRUST_CHAIN_V0.md` — trust-chain standard map.
- `docs/TRUST_CHAIN_ADMISSION_CONTRACT.md` — platform-side artifact admission contract.
- `docs/CHANNEL_GOVERNED_RUNTIME_GATES.md` — channel-conditioned runtime gate contract.
- `contracts/` — event, evidence, workspace, SVF, environment, trust-chain, and channel-governance fixtures.
- `tools/validate_*.py` — contract and admission validators.
- `infra/k8s/` — Kubernetes/Kustomize deployment wiring.

---

## 2. Controlled Vocabulary & Ontology

### Key terms
| Term | Definition | Source |
|---|---|---|
| **Thin platform monorepo** | Runtime/deployment hub that ships services and contracts while standards stay upstream | `README.md` |
| **Runtime and deployment hub** | Repo owning concrete platform services, deployment topology, validators, and product/API contracts | `README.md` |
| **TriTRPC over UDS** | Internal service transport binding using TriTRPC framing over Unix Domain Sockets | `docs/TRITRPC_PLATFORM_BINDING.md` |
| **Gateway** | HTTP/WebSocket edge bridge that relays to internal services | `docs/ARCHITECTURE.md` |
| **Portal** | Web portal surface, currently Vue/Vite oriented | `README.md` |
| **Professional Intelligence manifest** | Cross-repo alignment manifest recording runtime/platform ownership and upstream authority surfaces | `professional-intelligence.manifest.yaml` |
| **Workroom update contract** | No-runtime, no-network contract lane validating request/response shape for recovered-substrate refs | `README.md` |
| **SVF validate_change contract** | Read-only, selection-oriented agent-facing validation contract for Sovereign Validation Fabric | `README.md` |
| **Environment validation / validate_change v2** | Synthetic/no-network environment-validation request surface referencing Sociosphere state and AgentPlane evidence | `README.md` |
| **Prophet Trust Chain** | Cross-repo evidence/admission standard map for package, runtime, model, dataset, agent, tool, workflow, policy, execution, receipt, remediation, rollback, revocation, and learning evidence | `README.md` |
| **Channel-governed runtime gate** | Runtime-gate contract for channel-conditioned observations and sink permissions | `README.md` |
| **Evaluation fabric** | Platform-owned evaluation, observability, ranking, replay, and intelligence lane | `README.md` |
| **Release-readiness summary** | Platform-facing decision artifact summarizing graph state, evidence bundles, receipts, policy gates, drift state, and deployment posture | Ecosystem enrichment |
| **Admission validator** | Platform-side validator that allows, denies, or requests review for a governed artifact, action, release, or runtime gate | Ecosystem enrichment |
| **Graph-backed release gate** | Release gate that consumes HellGraph governance state instead of relying only on local fixtures | Ecosystem enrichment |
| **Procedure-template validator** | Validator proving a governed workflow template has required inputs, policy basis, evidence requirements, output schema, approval gate, and replay test | Ecosystem enrichment |
| **Integration-drift posture** | Platform-readable state indicating whether required repo topology, pins, fixtures, runtime touchpoints, evidence outputs, and owners exist | Ecosystem enrichment |

### Domain-specific language
- Prophet Platform turns standards into running services, deployment topologies, product/API
  contracts, and platform validators.
- Contract alignment does not imply runtime implementation.
- Runtime implementation does not imply demo readiness without evidence and adoption telemetry.
- Accepted-for-review is not execution.
- Synthetic/no-network fixtures do not claim live infrastructure, traffic routing, queue
  isolation, stateful resource isolation, production certification, or agent autonomy.
- AgentPlane owns execution and replay evidence; Sociosphere owns workspace/environment state;
  HellGraph serves graph-backed governance state; Prophet Platform owns the product/API
  invocation contract and release/admission surface.
- Graph-backed release gates should fail closed when required evidence, verified replay,
  policy binding, approval posture, or authority-boundary proof is missing.

### Semantic bindings to other repos
- **→ TriTRPC**: platform transport and service contracts bind to the normative protocol.
- **→ socioprophet-standards-storage**: storage posture follows storage standards.
- **→ socioprophet-standards-knowledge**: knowledge-context and provenance contracts follow knowledge standards.
- **← sociosphere**: topology, workspace/environment state, repo authority boundaries, and integration-drift facts.
- **← hellgraph**: graph-backed release-readiness, semantic activation, semantic diff, provenance, and replay state.
- **← agentplane**: execution, environment, run, replay, and receipt evidence.
- **↔ socioprophet**: platform deploys and validates the institutional-action surface.
- **↔ evaluation/intelligence consumers**: evaluation fabric exposes platform-owned ranking, replay, and intelligence surfaces.

---

## 3. Topic Modeling

| Topic | Keywords | Weight |
|---|---|---|
| Runtime/deployment platform | apps, API, gateway, portal, services, deployment hub | dominant |
| TriTRPC transport | UDS, stream binding, AEAD, replay guards, canonical encoding, gateway | dominant |
| Release/admission validation | trust chain, admit_artifact, validate_change, readiness, fail closed | high |
| Graph-backed governance | HellGraph, semantic activation, semantic diff, provenance, replay, release gate | high |
| Evidence and receipts | evidence contracts, receipt contracts, replay, AgentPlane, environment validation | high |
| Professional Intelligence / Workroom | manifest, workroom update, substrate refs, runtime boundary | high |
| Channel governance | runtime gates, channel-conditioned observations, sink permissions, repair posture | high |
| Evaluation fabric | evaluation, observability, ranking, replay, intelligence, schemas/eval | high |
| Kubernetes deployment | Kustomize, Argo CD, appsets, namespaces, overlays | medium-high |
| Standards consumption | standards.lock.yaml, storage standards, knowledge standards, platform bindings | medium-high |
| MCP | Model Context Protocol, tool protocol, integration surface | medium |

---

## 4. Dependency Graph

### Direct dependencies
- TriTRPC protocol and platform binding.
- Sociosphere workspace/environment state and governance topology.
- HellGraph graph-backed governance and release-readiness state.
- AgentPlane execution, environment validation, run, replay, and receipt evidence.
- Storage and knowledge standards repos.
- Kubernetes, Kustomize, and Argo CD.
- Vue 3 + Vite portal stack.

### Dependent systems
- Browser and API clients consuming platform services.
- SocioProphet institutional-action surfaces deployed through the platform.
- Operators managing desired state through Argo CD.
- Sociosphere release/admission checks that consume platform readiness posture.
- Evaluation and intelligence consumers using the platform eval fabric.

### Cross-repo impact when prophet-platform changes
- `rpc/` or TriTRPC platform binding change → service clients and protocol fixtures must update.
- `contracts/*.json` schema change → all event, evidence, receipt, admission, and evaluation
  consumers must update.
- Release-readiness validator change → Sociosphere, HellGraph query fixtures, AgentPlane evidence
  expectations, and SocioProphet institutional-action workflows must re-validate.
- Trust-chain admission change → evidence-chain, replay, risk, remediation, rollback, and revocation
  expectations must re-run.
- Environment validation change → Sociosphere workspace/environment state and AgentPlane synthetic
  execution references must re-validate.
- Channel-governed runtime gate change → channel provenance, sink permission, and repair posture
  fixtures must re-run.
- `infra/k8s/` change → platform deployment, Argo CD sync, staging validation, and rollback plan
  are affected.

---

## 5. Change Impact Rules

| What changed | Downstream repos affected | DevOps actions | Governance gates |
|---|---|---|---|
| `rpc/` TriTRPC contract or platform binding | API, gateway, clients, TriTRPC consumers | Rebuild API/gateway/clients; run protocol fixtures | Contract versioning; backward-compat check |
| `contracts/*.json` event/evidence/receipt schema | Event consumers, evidence stores, eval fabric, graph consumers | Schema migration and fixture validation | Schema registry and evidence-chain review |
| Release-readiness validator | sociosphere, hellgraph, agentplane, socioprophet | Re-run graph-backed release fixtures and admission summaries | Fail-closed if required graph/evidence/receipt state is missing |
| Procedure-template validator | socioprophet, sociosphere, standards-knowledge, agentplane | Validate inputs, policy basis, output schema, approval gate, replay test | Human-in-command and domain-owner review |
| Trust-chain admission contract | agentplane, sociosphere, storage/knowledge standards, platform services | Re-run admit_artifact allowed/denied fixtures | Evidence, replay, remediation, rollback, and revocation gate |
| Environment validate_change v2 | sociosphere, agentplane, platform API, gateway | Re-run synthetic environment fixtures and evidence refs | No live-infra or runtime-parity claim without separate proof |
| Channel-governed runtime gate | policy/memory/channel consumers, socioprophet, eval fabric | Re-run channel fixture validation | Sink permission and repair-posture review |
| Evaluation fabric schema/API | eval consumers, dashboards, ranking/replay services | Re-run eval schema/API tests | Evaluation governance and observability review |
| `infra/k8s/` Kustomize or Argo CD appsets | Platform deployment and operators | Argo CD sync; staging validation; rollback rehearsal | Infra review and rollback plan |
| Gateway behavior | Browser clients, API services, security boundary | Full CI, smoke-health, ingress checks | Gateway must remain bridge-only; no business logic |
| Standards lock update | All platform validators and runtime bindings | Run `make validate`; drift check | Upstream standard pin review |
