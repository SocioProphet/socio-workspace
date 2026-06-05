# Repository Analysis — SocioProphet/hellgraph

**GitHub:** https://github.com/SocioProphet/hellgraph  
**Role in ecosystem:** Graph reasoning and semantic governance query substrate  
**Last analysed:** 2026-06-05

---

## 1. Repository Purpose & Identity

### What it does
HellGraph is the local-first graph runtime for typed atoms, append-only valuations,
proof artifacts, field-state transitions, deterministic replay, and RDF/SPARQL
interoperability. Its ecosystem role is to persist and query the semantic governance
graph that Sociosphere indexes, SocioProphet acts through, AgentPlane executes, and
Prophet Platform validates for release readiness.

HellGraph is not the vocabulary authority and is not the institutional action surface.
It is the graph persistence and query execution substrate. Ontogenesis owns vocabulary
and SHACL/JSON-LD shape authority; Sociosphere owns repo/topology governance; SocioProphet
owns the human-facing institutional-action workflow; HellGraph must make those facts
queryable, diffable, replayable, and auditable.

### Core responsibilities
- Persist semantic graph nodes, edges, provenance references, receipt references, graph
  snapshots, and graph diffs.
- Provide query surfaces for governance state: repo ownership, authority boundaries,
  policy bindings, evidence bundles, procedure templates, execution substrates, approvals,
  overrides, receipts, and release-readiness status.
- Preserve deterministic replay semantics through append-only valuations, journals,
  checkpoints, and proof-aware state transitions.
- Provide RDF/SPARQL projection compatibility without letting RDF projection become the
  native execution kernel or semantic authority.
- Support governance-query obligations for `InstitutionalAction`, `Actor`, `Role`,
  `Authority boundary`, `Policy basis`, `Evidence bundle`, `Procedure template`,
  `ApprovalEvent`, `OverrideEvent`, and `ExecutionReceipt`.
- Detect graph-level admission failures when required edges, provenance hashes, graph
  snapshots, policy bindings, or receipt references are missing.

### What systems depend on it
- `sociosphere` — consumes HellGraph query results for governance graph checks,
  integration drift detection, and release/admission reasoning.
- `socioprophet` — needs graph lookup for institutional action context, evidence,
  authority, policy, procedure, approval, override, and receipt state.
- `prophet-platform` — needs graph-backed release-readiness and product/API surfaces.
- `agentplane` — needs graph snapshot and receipt references for replayable execution
  evidence.
- `ontogenesis` — supplies vocabulary and shapes that HellGraph must persist and query.
- Search, routing, and semantic runtime consumers such as Sherlock Search, slash-topics,
  and new-hope.

### What it depends on
- Rust workspace crates in `SocioProphet/hellgraph`.
- `ontogenesis` for vocabulary, namespace, JSON-LD, and SHACL/shape definitions.
- `sociosphere` for canonical repo/topology facts and integration claims.
- `agentplane` for execution receipts and replay artifacts.
- `prophet-platform` for API/product asset envelopes and release-readiness surfaces.
- RDF/SPARQL compatibility references, including Blazegraph as a behavioral reference only.

### Key files
- `README.md` — project statement, crate inventory, alpha status, architectural position,
  and non-negotiable rules.
- `hg_core` — shared core types and value families.
- `hg_fieldpack` — provisional and canonical field-pack authoring and validation.
- `hg_proof` — bounded-state proof checking and proof artifact shaping.
- `hg_kernel` — atoms, valuations, journal, checkpoint, replay.
- `hg_runtime` — event application and field/proof commit cycles.
- `hg_read_kernel` — read-side snapshot summaries and incident-link inspection.
- `PROVENANCE.md` — repository provenance.

---

## 2. Controlled Vocabulary & Ontology

### Key terms
| Term | Definition | Source |
|---|---|---|
| **Typed atom** | Native graph identity unit with type-bearing semantics | `README.md` |
| **Append-only valuation** | State assertion that changes by appending new valuation records, not mutating old structure | `README.md` |
| **Proof artifact** | Evidence object tied to proof-aware state transitions | `README.md` |
| **Field-state transition** | Runtime state transition over graph/field structures | `README.md` |
| **Checkpoint** | Replayable graph/runtime state boundary | `hg_kernel` |
| **Journal** | Append-only event/state log supporting deterministic replay | `hg_kernel` |
| **Graph snapshot** | Queryable state image used for governance, diff, and replay lookup | Ecosystem enrichment |
| **Graph diff query** | Query comparing graph snapshots or governance states across revisions | Ecosystem enrichment |
| **Semantic governance graph** | Graph of assets, terms, policies, evidence, quality signals, execution receipts, and release/admission state | `docs/integrations/hellgraph-semantic-governance-control-loop-v0.md` |
| **Institutional-action query** | Query resolving actor, role, authority, context, evidence, policy, procedure, capability, approval, and receipt links for a governed action | Ecosystem enrichment |
| **Integration-drift query** | Query detecting a missing or stale manifest entry, pin, fixture, evidence artifact, runtime touchpoint, owner, or feedback loop | Ecosystem enrichment |
| **Release-readiness query** | Query deciding whether mandatory semantic edges, policy bindings, quality signals, and receipts exist for admission | Ecosystem enrichment |
| **RDF/SPARQL projection** | Compatibility bridge from HellGraph state into RDF/SPARQL behavior; not the native kernel | `README.md` |

### Domain-specific language
- HellGraph stores and serves the governance graph; it does not author vocabulary.
- Ontogenesis names terms and shapes. Sociosphere indexes repo/topology authority. HellGraph
  makes those facts queryable and replayable.
- Query facades must not become semantic authority.
- Proof is never silently downgraded to confidence.
- Graph structure is immutable after insertion; state changes occur through append-only
  valuations.
- RDF is a projection bridge, not the native execution kernel.
- Missing mandatory governance edges are admission failures in governed namespaces, not
  warnings.

### Semantic bindings to other repos
- **← sociosphere**: canonical repo membership, pinned revisions, repo authority boundaries,
  integration claims, and governance graph obligations.
- **← ontogenesis**: vocabulary, namespace, ontology, shape, JSON-LD, and validation authority.
- **↔ socioprophet**: institutional-action workflows require graph lookup for actor, role,
  authority, policy, evidence, procedure, approval, override, and receipt state.
- **↔ agentplane**: execution and replay receipts must be linked into graph snapshots.
- **↔ prophet-platform**: release-readiness, semantic activation, semantic diff, provenance,
  and replay APIs consume graph-backed state.
- **→ search/routing/runtime consumers**: Sherlock Search, slash-topics, and new-hope consume
  graph-backed semantic state and evidence references.

---

## 3. Topic Modeling

| Topic | Keywords | Weight |
|---|---|---|
| Graph kernel | typed atoms, valuations, journal, checkpoint, replay, immutable graph | dominant |
| Proof-aware state | proof artifact, bounded-state proof checking, proof-aware transition | high |
| Semantic governance graph | represents, derivedFrom, conformsTo, governedBy, quality signal, receipt | high |
| Governance queries | authority boundary, evidence bundle, policy basis, approval, override, execution receipt | high |
| Integration drift | manifest entry, pinned revision, fixture, evidence artifact, owner, feedback loop | high |
| Release readiness | admission failure, mandatory edge, graph snapshot, policy binding, replay material | high |
| RDF/SPARQL bridge | RDF projection, SPARQL compatibility, Blazegraph reference, RDF-star | medium |
| Vector/semantic retrieval bridge | hybrid symbolic-vector stack, retrieval binding, semantic activation | medium |
| Alpha runtime gaps | conformance harness, production persistence, security review, query facade | medium |

---

## 4. Dependency Graph

### Direct dependencies
- Rust workspace crates in `SocioProphet/hellgraph`.
- Ontogenesis vocabulary/shape authority.
- Sociosphere canonical repo/topology facts.
- AgentPlane execution and replay receipts.
- Prophet Platform semantic activation and release-readiness envelopes.
- RDF/SPARQL compatibility references.

### Dependent systems
- `sociosphere` governance graph checks and admission validation.
- `socioprophet` institutional-action context and evidence lookup.
- `prophet-platform` semantic activation, release-readiness, provenance, replay, and product APIs.
- `agentplane` replay/evidence linkage consumers.
- Sherlock Search, slash-topics, and new-hope graph-backed semantic consumers.

### Cross-repo impact when HellGraph changes
- Query model change → Sociosphere, Prophet Platform, and SocioProphet must update graph
  queries and release/admission checks.
- Snapshot or diff schema change → AgentPlane replay references and Prophet Platform APIs
  must update.
- RDF/SPARQL projection change → external compatibility tests and query facade consumers
  must re-validate.
- Proof/checkpoint/journal change → replay determinism, evidence validation, and governance
  audit trails must re-run.
- Governance edge vocabulary support change → Ontogenesis shape alignment and Sociosphere
  governance graph checks must update.

---

## 5. Change Impact Rules

| What changed | Downstream repos affected | DevOps actions | Governance gates |
|---|---|---|---|
| Graph node/edge model | sociosphere, ontogenesis, prophet-platform, socioprophet | Regenerate shape bindings and query fixtures | Ontology + governance review |
| Snapshot or diff schema | agentplane, prophet-platform, sociosphere | Re-run replay and graph-diff fixtures | Evidence-chain review |
| Query facade | sociosphere, prophet-platform, search/routing consumers | Re-run governance-query and API contract tests | Query facade must not become semantic authority |
| RDF/SPARQL projection | external RDF/SPARQL consumers, compatibility references | Re-run RDF/SPARQL compatibility tests | Projection cannot override native kernel semantics |
| Proof/checkpoint/journal semantics | agentplane, sociosphere, prophet-platform | Re-run deterministic replay tests | Proof must not be downgraded to confidence |
| Governance edge requirements | socioprophet, sociosphere, ontogenesis, prophet-platform | Re-run admission and release-readiness checks | Missing required edge remains fail-closed |
| Institutional-action query support | socioprophet, sociosphere, prophet-platform | Validate actor/role/policy/evidence/procedure/receipt query fixtures | Human-in-command and authority-boundary gate |
