# ER/NER Resynthesis — Realignment to the Existing Identity-Prime Spine

**Status:** v0.1 — reconciles the "Updated Resynthesis, Realignment, and ER/NER Integration Plan" with the
already-built Identity Is Prime × HELL-ER × Regis × ACR × Sociosphere architecture.
**Companion:** [`identity-is-prime-regis-acr-sociosphere.md`](identity-is-prime-regis-acr-sociosphere.md),
[`../conformance/identity-prime-er-plus-conformance.md`](../conformance/identity-prime-er-plus-conformance.md),
`protocol/identity-is-prime/regis/` (new schemas).

## 1. What the plan assumed vs. what already exists

The integration plan is sound, but several items it proposed as new are already specified. Reconciling
prevents duplicate, divergent contracts.

| Plan item | Reality in-repo | Action |
|---|---|---|
| §3 "'Regis entity graph' not found publicly; treat as internal target" | Correct — Regis is internal (`regis-entity-graph` is pinned in the Sociosphere manifest; the graph object families are specified in the architecture doc) | Build to the internal spec, not a public dependency |
| §4 ER service objects (`EventIR`, `ResolutionDecision`, `EntityNode`, `EdgeWitness`, `PolicyDecision`, `ProofArtifact`, …) | `EventIR` + `ProofArtifact` schemas exist in the reference repo; `PrimeAtom`/`ContradictionObject`/`ReleasePack` exist in HELL-ER; **`CanonicalEntity`/`SourceRecord`/`EdgeWitness`/`ResolutionDecision`/`DecisionLedgerEntry` did NOT exist** | **Added this pass** (see §2) |
| §4.2 ER service APIs | HELL-ER service methods + TriTRPC method fixtures (`identityprime.v1`, `regis.proof.v1`, `acr.concordance.v1`, `holmes.case.v1`, `sherlock.search.v1`) already specified | Map plan APIs onto these (§4); add Regis graph-op fixtures next |
| §4.3 required outputs (decision, explanation, policy verdict, provenance, confidence+uncertainty, reversibility, proof ref) | No single contract enforced all seven | **Enforced** by `resolution-decision.v1` |
| §13.2 entity-graph + edge-witness schema | absent | **Added** (`canonical-entity.v1`, `source-record.v1`, `edge-witness.v1`) |
| §13.6 uncertainty fields on every resolution output | absent | **Required** field in `resolution-decision.v1` and `edge-witness.v1` |
| §13.7 reversible merge/unmerge | reference `resolve_entities` clusters; no reversible ledger | **Added** `decision-ledger-entry.v1` (append-only, hash-chained, unmerge first-class) |

## 2. What this pass added

New protocol contracts under `protocol/identity-is-prime/regis/` (all valid JSON Schema draft 2020-12,
fixtures validate):

- `canonical-entity.v1` · `source-record.v1` · `edge-witness.v1` · `resolution-decision.v1` · `decision-ledger-entry.v1`
- fixtures: a CITIZEN_FOG person `EdgeWitness` + the explainable, reversible `ResolutionDecision` that cites it.

These satisfy architecture follow-on #3 and back conformance lane `regis-graph-contracts`. Design invariants:
explainable (witness chain + top features), policy-vetoed (structural, not score-based), uncertainty
mandatory, reversible by construction, determinism-pinned.

## 3. NER / EL / ER task-placement matrix (plan §6, formalized to the fog scope model)

Phases are **separate but coupled**: NER finds spans, EL grounds them to KB entries, ER clusters
records/events/entities across time and sources. Placement follows the Event-IR `scope.realm`.

| Task | `CITIZEN_FOG` (on-device, sync) | `CITIZEN_CLOUD` (regional, async) | `INSTITUTION` (contracted) | Federated / `ADTECH` / `HSM` |
|---|---|---|---|---|
| Source typing, scope capture, deterministic id parsing | ✅ required | — | — | — |
| PII minimization / hashing / secret handling | ✅ required (before anything leaves device) | — | — | — |
| Lightweight NER + dictionary matching (high-value types) | ✅ | ✅ refine | — | — |
| Prime-topic hinting, consent/preference lookup | ✅ | ✅ | — | — |
| Statistical NER + SpanCategorizer (overlapping spans) | best-effort | ✅ primary | — | — |
| Entity linking to local KB | best-effort | ✅ | — | — |
| Event/relation extraction, candidate block generation | best-effort | ✅ | — | — |
| Feature-atom typing (stability/exclusivity/frequency) | — | ✅ | — | — |
| Heavy ER clustering, graph-wide consistency, unmerge/replay analysis | — | ✅ | — | — |
| Ontology alignment + term-suggestion mining; embedding/index refresh | — | ✅ | — | — |
| Cross-party candidate exchange, identity-proof exchange, federated train/eval | — | — | ✅ under contract | ✅ only under explicit policy contract |
| Tracking-identifier / nonce-stream analysis | observe + minimize | congruence lane | — | ADTECH/HSM: non-escape proof only |

Rule: **overlapping/multi-labeled spans are expected** (a phrase can be a named entity *and* a prime-topic
marker *and* a policy-sensitive cue), so the span pipeline must support overlap + later disambiguation —
captured in `source-record.v1.mentions[].overlapping`.

## 4. Plan §4 service surface → contract mapping

| Plan object/API | Backing contract / method |
|---|---|
| `EventIR`, `POST /event-ir/ingest` | `identity_is_prime_reference/schemas/event_ir.schema.json` |
| `Mention`, `POST /extract/mentions` | `source-record.v1.mentions[]` (NER/EL output) |
| `Candidate`, `POST /resolve/candidates` | EdgeWitness (pre-decision) + blocking features |
| `ResolutionDecision`, `POST /resolve/entities` | `resolution-decision.v1` |
| `EntityNode`, `GET /graph/entity/{id}` | `canonical-entity.v1` |
| `EdgeWitness`, `GET /graph/path|network` | `edge-witness.v1` |
| `POST /graph/upsert`, `POST /graph/unmerge` | `decision-ledger-entry.v1` (op = upsert_* / unmerge) |
| `PolicyDecision`, `POST /policy/check` | `policy_verdict` block + policy-fabric decision schema |
| `ProofArtifact`, `GET /proof/{id}` | reference `proof_artifact.schema.json` + Regis proof certificates |
| `POST /search/query` | Sherlock `sherlock.search.v1` TriTRPC method |
| `Preference`, `OntologyTerm`, `POST /ontology/propose` | ontogenesis (ontology) + glossary versioning (§5) |

## 5. Remaining gaps → next executable steps (multi-hour, not multi-month)

1. **Regis graph-op TriTRPC fixtures** — add `regis.graph.v1.upsert` / `regis.graph.v1.unmerge` request/response fixtures (mirrors the existing `regis.proof.v1` style) so graph mutations are wire-deterministic.
2. **NER/EL service contracts** — `extract.mentions.v1` / `extract.events.v1` request/response schemas emitting `source-record.v1.mentions`; place per §3 matrix.
3. **Glossary/ontology versioning** — three-layer (vocabulary → glossary → ontology) release process bound to `ontogenesis`, with SHACL validation and provenance; glossary deltas fast, ontology classes compatibility-gated.
4. **Search index schema** — local-first `SearchIndexRecord` for Sherlock (entities + witnesses + certificates + release-pack pointers), explanation-first result cards, policy-filtered + time-sliced.
5. **Review + learning loops** — supervision capture from accept/reject/correct → train/eval splits; ER model promotion gated on benchmark + policy-regression checks (reuse the board discipline).
6. **Benchmark lane** — `workspace-identity-conformance` extension comparing local-only vs citizen-cloud-assisted extraction/resolution on the golden fixtures, with sequence-neutrality (replay) checks.

## 6. Concrete realignment decisions (confirmed)

Event-IR is canonical ingestion; the entity graph is a materialized view over Event-IR + review signals;
NER/EL/ER are distinct but share ontology + provenance contracts; merge **and** unmerge are first-class;
search is local-first and ontology-aware; preferences/policy live in the same loop as extraction/retrieval;
retraining is driven by review artifacts and proof outcomes; Linux-first/local-first is primary and cloud is
bounded; "Regis entity graph" is an internal target, not a public dependency.
