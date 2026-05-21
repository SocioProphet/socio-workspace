# Identity Is Prime × HELL-ER × Regis × ACR × Sociosphere Integration

Issue: https://github.com/SocioProphet/sociosphere/issues/284

## Purpose

This document defines the Sociosphere integration spine for the Identity Is Prime reference implementation, HELL-ER, Regis Entity Graph, Authority Concordance Rex (ACR), Agent Registry, Holmes, and Sherlock Search. Sociosphere is the cross-repo workspace controller: it pins repositories, executes validation, records conformance, and provides deterministic retest lanes.

The integration is not a centralized lakehouse design. The runtime target is local-first and cache-first: assertion cache, crosswalk cache, golden projection cache, delta cursors, proof artifacts, release packs, and certificate ledgers. Sociosphere coordinates the workspace and retest evidence; it does not become the data warehouse.

## Architectural hierarchy

1. Identity Is Prime is the doctrine and reference implementation. It defines prime-topic identity, Event-IR, policy polytopes, congruence lanes, non-escape semantics, proof artifacts, and fog-first deployment.
2. HELL-ER is the symbiotic hazard-governed entity-resolution and identity-release service function paired with the core prime identity substrate. It classifies hazards, resolves subjects, preserves contradictions, distinguishes query-negative from fact-absent, evaluates release, emits release packs, and controls leakage/lifecycle semantics.
3. Regis Entity Graph is the graph implementation surface. It stores canonical entities, source records, identity states, concordance links, transition edges, decision ledger entries, proof certificates, contradiction pointers, and release-pack pointers.
4. ACR is the authority concordance service profile. It owns versioned authority templates, connector schema evolution, entity resolution, crosswalks, golden projections, and point-in-time proofs.
5. Holmes is the investigative/evidence-reasoning layer for Regis and HELL-ER. It should consume Regis graph state, HELL-ER contradiction objects, proof artifacts, ledger entries, policy decisions, and contradiction/refutation events to form explainable investigative cases.
6. Sherlock Search is the retrieval and search surface for Regis/Holmes/HELL-ER evidence. It should index entities, events, assertions, certificates, source records, release packs, crosswalks, and decision-ledger entries without becoming canonical truth.
7. Agent Registry declares the agents that observe, normalize, classify, resolve, retrieve, reason, prove, redact, review, and audit. Agents submit observations, search results, decisions, proposed graph mutations, release decisions, and certificates. They do not free-write canonical truth.
8. Sociosphere coordinates and retests the full estate through its manifest, lock file, runner, workspace policy, and protocol fixtures.

## Existing upstream anchors

The Sociosphere manifest already contains the following relevant repositories:

- `identity-is-prime-reference`
- `regis-entity-graph`
- `tritrpc`
- `agentplane`
- `human_digital_twin`
- `ontogenesis`
- `socioprophet_standards_storage`
- `sourceos-spec`
- `policy-fabric`

The focused Identity Prime workspace overlay should also materialize or pin `agent-registry`, `holmes`, `sherlock-search`, and `meshrush` where absent.

## Integration contracts

### Identity Is Prime reference

The reference repo provides the normative behavior for:

- Event-IR ingestion
- fog-first scope classes
- prime-topic labeling
- policy-constrained entity resolution
- policy polytope checks
- congruence lanes for modular evidence
- proof artifact production
- zeta-style identity-state audit metrics

### HELL-ER service function

HELL-ER belongs inside Identity Is Prime while remaining a distinct service function. It is HADES-descended, Heller-derived, and entity-resolution-centered.

HELL-ER owns protocol semantics for:

- hazard envelopes
- prime atoms
- context-scoped identity release
- contradiction objects
- query-negative / fact-absent separation
- assurance vectors
- release policies
- release packs
- redress queues
- merge/split audit artifacts
- revocation and expiry semantics

Initial HELL-ER protocol material lives under:

- `protocol/identity-is-prime/hell-er/README.md`
- `protocol/identity-is-prime/hell-er/schemas/prime-atom.v1.schema.json`
- `protocol/identity-is-prime/hell-er/schemas/contradiction-object.v1.schema.json`
- `protocol/identity-is-prime/hell-er/schemas/release-pack.v1.schema.json`
- `protocol/identity-is-prime/hell-er/fixtures/release_pack.internal_operational.synthetic.valid.json`
- `protocol/identity-is-prime/hell-er/expected/release_pack.internal_operational.synthetic.valid.result.json`

Candidate HELL-ER service methods:

- `heller.classify_hazard`
- `heller.resolve_subject`
- `heller.record_contradiction`
- `heller.evaluate_release`
- `heller.emit_release_pack`
- `heller.redact_for_audience`
- `heller.register_redress`
- `heller.revoke_or_expire_atom`
- `heller.evaluate_merge`
- `heller.evaluate_split`

### Regis Entity Graph

Regis consumes Identity Is Prime and HELL-ER as graph semantics. Required graph object families:

- `CanonicalEntity`
- `SourceRecord`
- `ConcordanceLink`
- `DecisionLedgerEntry`
- `IdentityPrime`
- `ScopeFlag`
- `IdentityState`
- `IdentityMixture`
- `IdentityPolytope`
- `WorldlineEvent`
- `AdmissibleTransition`
- `TokenLane`
- `ProofCertificate`
- `TransitionCertificate`
- `NonEscapeCertificate`
- `ConcordanceDecisionCertificate`
- `ContradictionObject`
- `ReleasePackPointer`
- `SearchIndexRecord`
- `InvestigationCase`
- `EvidenceFinding`

### Holmes reasoning layer

Holmes should be the Regis-native investigative reasoning surface. Its responsibilities are:

- consume Regis graph snapshots and ledger/certificate/release-pack pointers
- assemble evidence findings into investigation cases
- explain why a linkage or release was verified, refuted, undecidable, stale, redacted, revoked, expired, or review-bound
- detect contradictions across ACR concordance, HELL-ER release decisions, identity polytope policy, token non-escape, and source assertions
- emit proposed graph annotations or case findings, not canonical truth

Holmes outputs must be reducible to Regis evidence objects and must carry policy/schema/resolver/template/release-template version pins.

### Sherlock Search retrieval layer

Sherlock Search should be the retrieval layer for evidence discovery and operator/user query. Its responsibilities are:

- index canonical entities, source records, identity states, worldline events, ledger entries, certificates, HELL-ER release packs, and Holmes findings
- provide search over proof, release, and evidence surfaces
- return cited graph pointers, source pointers, release-pack pointers, and ledger pointers
- support delta indexing for local-first/cache-first runtime
- avoid writing canonical entity truth directly

Sherlock Search should be treated as an indexing and retrieval adapter for Regis/Holmes/HELL-ER, not as the system of record.

### ACR service profile

ACR supplies mastered entity truth and proof-carrying concordance:

- authority template versions
- connector schema versions
- schema migration records
- source assertions
- source-to-canonical crosswalks
- golden record projections
- point-in-time golden record proofs
- template migration simulations

### Agent Registry

Required agent families:

- `prime-topic-agent`
- `identity-polytope-agent`
- `heller-hazard-agent`
- `heller-release-agent`
- `heller-redaction-agent`
- `heller-contradiction-agent`
- `transition-graph-agent`
- `congruence-non-escape-agent`
- `zeta-audit-agent`
- `acr-template-agent`
- `acr-connector-agent`
- `acr-concordance-agent`
- `acr-golden-projection-agent`
- `regis-proof-agent`
- `regis-policy-agent`
- `regis-steward-agent`
- `holmes-case-agent`
- `holmes-contradiction-agent`
- `sherlock-index-agent`
- `sherlock-query-agent`

Each manifest must declare input schemas, output schemas, graph write permissions, policy scopes, TRIT RPC bindings, retrieval permissions, release permissions, redaction permissions, and evidence outputs. A manifest that lacks the required policy scope or graph/search/release permission must be rejected by conformance.

## Sociosphere conformance lanes

The Sociosphere retest controller should expose these lanes:

1. `identity-prime-schema`: validates Identity Is Prime fixtures and schemas.
2. `identity-prime-policy`: evaluates polytope membership and forbidden mixtures.
3. `identity-prime-transition`: validates admissible transition and no-path cases.
4. `identity-prime-token`: validates congruence and token non-escape cases.
5. `identity-prime-audit`: validates zeta-style identity audit summaries.
6. `hell-er-release`: validates hazard envelopes, contradiction objects, release packs, redaction, and query-negative/fact-absent separation.
7. `regis-graph-contracts`: validates Regis graph objects and proof certificate pointers.
8. `holmes-case-contracts`: validates Holmes case/finding outputs against Regis and HELL-ER evidence semantics.
9. `sherlock-index-contracts`: validates Sherlock index records, search result pointers, release-pack pointers, and delta indexing receipts.
10. `agent-registry-identity`: validates agent manifests and policy scopes.
11. `acr-concordance-profile`: validates source assertion, crosswalk, golden projection, and proof fixtures.
12. `tritrpc-wire`: verifies deterministic request/response fixture encoding.
13. `workspace-identity-conformance`: runs the clean end-to-end lane across pinned repos.

## Required fixture families

Fixtures live under `protocol/identity-is-prime/` and should be portable across repos.

- polytope valid and invalid examples
- forbidden mixture examples
- admissible transition examples
- no-admissible-path refutations
- token non-escape valid examples
- token non-escape violation examples
- zeta audit windows
- HELL-ER release-pack examples
- HELL-ER query-negative / not-absent examples
- HELL-ER contradiction flattening rejection examples
- HELL-ER silent merge/split rejection examples
- HELL-ER external unredacted-release rejection examples
- ACR concordance and golden record proof examples
- Holmes case and contradiction examples
- Sherlock search index and query-result pointer examples

## Determinism requirements

Every conformance result must pin:

- `schema_version`
- `policy_version`
- `resolver_version`
- `template_version`, when ACR participates
- `release_template_version`, when HELL-ER participates
- `hazard_classifier_version`, when HELL-ER participates
- `index_version`, when Sherlock Search participates
- `case_model_version`, when Holmes participates
- `fixture_version`
- `input_hash`
- `result_hash`
- `certificate_hash`, when a proof is emitted
- `release_pack_hash`, when a release pack is emitted

A repeated clean checkout with the same pins must produce equivalent results.

## Acceptance criteria

- Sociosphere can fetch the pinned repos and execute the Identity Is Prime / HELL-ER / Regis / Holmes / Sherlock / ACR / Agent Registry conformance suite.
- Identity polytope fixtures return deterministic `VERIFIED` or `REFUTED` results.
- Token non-escape violations produce structural refutations rather than probabilistic scores.
- HELL-ER release-pack fixtures preserve context, hazard profile, contradiction ledger, assurance vector, lifecycle, release policy, and machine annex.
- HELL-ER fixtures refuse to convert query-negative into fact-absent.
- HELL-ER fixtures reject silent merge, silent split, and external unredacted direct-identifier release.
- ACR golden record proof fixtures include shared ledger and certificate pointers.
- Holmes findings cite Regis graph, HELL-ER release pack, ledger, certificate, or source pointers.
- Sherlock search results cite indexed Regis/Holmes/HELL-ER pointers and never claim canonical truth without graph/ledger backing.
- Agent manifests without required policy scopes, graph permissions, search permissions, release permissions, or redaction permissions are rejected.
- The integration remains local-first and cache-first; no central lakehouse dependency is introduced.

## Follow-on work

1. Materialize `agent-registry`, `holmes`, and `sherlock-search` in `manifest/workspace.toml` or the focused Identity Prime workspace overlay if absent.
2. Add executable validators under `tools/conformance/` for HELL-ER schema and fixture validation.
3. Promote the HELL-ER fixture skeleton into schema-backed JSON validation.
4. Add TRIT RPC fixtures for `identityprime.v1`, `heller.identity.v1`, `regis.proof.v1`, `holmes.case.v1`, `sherlock.search.v1`, and `acr.concordance.v1`.
5. Wire conformance outputs into the Sociosphere registry/evidence pattern.
6. Decide whether HELL-ER release packs are signed independently or through Regis proof certificates.
