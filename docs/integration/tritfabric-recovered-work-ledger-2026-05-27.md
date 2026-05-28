# TritFabric recovered work absorption ledger — 2026-05-27

## Status

Captured in downstream implementation repo and registered for estate governance.

This ledger records that recovered Atlas / TritFabric / Community Learning / Serve Plane chat material was integrated into `SocioProphet/tritfabric` through a tranche sequence of executable contracts, validators, tests, API stubs, catalog records, and readiness documentation.

Sociosphere does not reimplement the downstream work. It records estate-level absorption status, boundaries, and follow-on planes.

## Downstream repo

- Repository: `SocioProphet/tritfabric`
- Integration range: PR #9 through PR #23, excluding duplicate PR #13
- Duplicate PR: #13 closed unmerged because #12 had already landed the StatusReply / Promote contract tranche

## Merged tranche map

| PR | Plane | Estate status |
|---:|---|---|
| #9 | Recovered framework executable contracts | Merged |
| #10 | Registry calculus promotion gates | Merged |
| #11 | HTTP Trit-visible promotion route | Merged |
| #12 | TriTRPC / proto StatusReply Promote contract | Merged |
| #13 | Duplicate StatusReply Promote PR | Closed unmerged as duplicate |
| #14 | Network Atlas framework catalog contracts | Merged |
| #15 | Network Atlas framework governance expansion | Merged |
| #16 | Third recovered framework catalog batch | Merged |
| #17 | Community Learning workflow stubs | Merged |
| #18 | Community event API stubs | Merged |
| #19 | Community event stream contracts | Merged |
| #20 | Serve p95/inflight autoscaler core | Merged |
| #21 | Serve autoscaler observability metrics | Merged |
| #22 | RouterCore / autoscaler integration tests | Merged |
| #23 | Serve runtime deployment readiness notes | Merged |

## Absorbed recovered-work planes

### 1. Framework and calculus contracts

TritFabric now has executable recovered-work contracts for:

- community-learning Avro records;
- JSON-LD contexts for community and model calculus terms;
- SHACL gates for consent, license, lineage, rubric, math type, calculus operations, ledger references, and artifact references;
- model-card promotion semantics carrying `mathType`, `calcOps`, `ledgerRef`, and `artifactRef` into JSON / JSON-LD / Turtle outputs.

### 2. Trit-visible promotion semantics

TritFabric now has:

- HTTP `POST /v1/promote/{job_id}` structured status projection;
- compatibility proto / gRPC `RegistryService.Promote(JobId) returns (StatusReply)`;
- canonical contract notes that promotion failures must be protocol-visible as TRUE / MID / FALSE rather than only transport exceptions.

### 3. Network Atlas catalog and framework governance

TritFabric now has:

- `catalog/frameworks/index.jsonl`;
- framework catalog schema;
- adapter scorecard schema;
- capability descriptor schema;
- Ray, ONNX, and Albumentations capability descriptors;
- bounded recovered-source entries for CV, runtime, conversion, language, medical-imaging, graph-learning, neurosymbolic, and accelerator-specific candidates;
- validator and tests for catalog, scorecards, and capabilities.

Catalog entries are intake records only. They do not claim validated adapters or runtime support.

### 4. Community Learning Plane

TritFabric now has:

- workflow schema;
- community distillation workflow stub;
- curriculum A/B evaluation workflow stub;
- OPA policy stub for consent / license / lineage / rubric eligibility;
- HTTP event intake stubs for feedback, curation, eval, proposals, and reputation;
- stream topic contracts and fixtures for accepted feedback, curation, curriculum evaluation, and non-economic credit;
- validators and tests.

Community credit remains explicitly non-transferable and non-economic. No workflow currently trains models, mutates models, promotes artifacts, creates token obligations, or creates payout obligations.

### 5. Serve Plane

TritFabric now has:

- dependency-light p95 / inflight router autoscaler core;
- autoscaler observability metrics for pressure and decisions;
- integration tests proving `RouterCore.status()` / `RouterCore.update()` compose with `RouterAutoscalerCore.step_from_status()` without Ray Serve deployment;
- Serve runtime deployment readiness documentation.

Serve work remains non-production-readiness unless a later opt-in runtime deployment tranche lands with rollback, report-only mode, and explicit gates.

## Estate boundaries

### Canonical implementation repo

`SocioProphet/tritfabric` owns the implementation and immediate contract surfaces for this recovered work.

### Sociosphere role

`SocioProphet/sociosphere` records estate absorption, repo-plane boundaries, propagation requirements, and follow-on coordination.

Sociosphere must not duplicate TritFabric implementation or become a second source of truth for TritFabric contracts.

### Follow-on planes

- `SocioProphet/ontogenesis`: promote stabilized community / model calculus / framework catalog semantics into ontology and SHACL vocabulary once TritFabric schemas settle.
- `SocioProphet/prophet-platform`: consume Community Learning contracts and Network Atlas catalog as product/runtime capabilities only after policy and promotion gates are explicit.
- `SocioProphet/superconscious`: consume mentor/learner/community semantics only as coordinator/advisory surfaces, not authority planes.
- SociOS / SourceOS runtime repos: consume opt-in runtime packaging only after TritFabric runtime deployment docs advance beyond readiness notes.

## Claim boundary

This ledger does not claim that all recovered chat material has been exhausted.

It does claim that the first major recovered Atlas / TritFabric / Community / Serve work package is no longer floating only in chat text and has been converted into version-controlled downstream artifacts with validators, tests, and claim boundaries.

## Remaining estate work

1. Decide when to promote stable TritFabric vocabularies into `ontogenesis`.
2. Decide which Community Learning surfaces should become `prophet-platform` product/runtime capabilities.
3. Decide which mentor/learner semantics belong in `superconscious` while preserving coordinator-vs-authority boundaries.
4. Continue recovered Model Zoo catalog expansion only in bounded batches.
5. Add explicit Sociosphere dependency/propagation entries if the manifest/lock should pin the resulting TritFabric revision.
