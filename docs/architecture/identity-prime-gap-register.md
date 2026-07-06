# Identity-Prime / Catalog / Metadata — Gap Register & Improvement Order

**Status:** v0.1 — single prioritized backlog across the contracts and design work, spanning `sociosphere`,
`exodus`, `prophet-platform`, `regis-entity-graph`, `ontogenesis`, `sherlock-search`.
Sociosphere is the cross-repo controller, so the register lives here.

## 0. What is usable *now* (done this cycle)

Contracts are conformant **and runnable** — a single gate validates them all:

```
python3 tools/conformance/validate_regis_extract_masking_fixtures.py   # 13 schemas, 7 fixtures, 2 tritrpc — PASS
```

| Family | Contracts | Runtime? |
|---|---|---|
| Regis graph | canonical-entity, source-record, edge-witness, resolution-decision, decision-ledger-entry (+2 tritrpc graph-ops) | ❌ contracts only |
| Extraction | extract-mentions, extract-events, grasp-pattern | ❌ contracts only |
| Sherlock | search-index-record | ❌ contracts only |
| Masking | tokenization-profile, masking-decision | ❌ contracts only |
| Audience | audience-tag, tag-assignment | ❌ contracts only |
| Metadata Standards (exodus) | evidence-artifact, custody-event, policy-gate, document-type-registry, forensic-bundle, serializer-spec | ⚠️ intake only |

**The headline gap class:** every contract validates, but **almost nothing has a runtime behind it**. "Usable
and accessible" now means *implementing executors*, in dependency order, not writing more schemas.

## 1. Priority tiers & order

### P0 — Foundational (unblocks the rest; do first, in this order)

| # | Gap | Repo | Why first | Usable when |
|---|---|---|---|---|
| 1 | ✅ **DONE** — aggregate runner `tools/conformance/run_identity_prime_conformance.sh` + `validate_regis_extract_masking_fixtures.py` (13 schemas / 7 fixtures / 2 tritrpc, deep jsonschema). Remaining: add a CI step that invokes the runner. | sociosphere | Cheapest accessibility win; turns files into an enforced gate | ✅ one command validates the whole lane |
| 2 | ✅ **MERGED to exodus `main`** (PR #22, `703001d`) — `scripts/exodus_gate.py` (CHK-01..10, `GateContext`, fail-closed) + `test_exodus_gate.py` + `examples/gate-policies/`. Landed by a parallel session; my duplicate branch was dropped. | exodus | "Catalog is control plane" keystone | ✅ an artifact cannot illegally cross a zone boundary |
| 3 | ✅ **SHIPPED** as `CANON-v0.1 = json-canonical` (sorted-key, whitespace-free UTF-8 JSON) in `scripts/exodus_seal.py` (PR #20). **Not CBOR** — my CBOR branch contradicted the shipped spec and was dropped. CBOR is a documented *future* evolution of the serializer-spec, not current. | exodus | Deterministic, independently-reproducible hash input | ✅ hashes are independently replayable |

### P1 — Differentiators (the moat; after P0)

| # | Gap | Repo | Depends on | Usable when |
|---|---|---|---|---|
| 4 | ✅ **DONE (reference engine)** — `scripts/exodus_tokenize.py` (Chameleon pseudonyms + homomorphic re-keying + key-evolving epochs + FPE + re-id lookup) + `test_exodus_tokenize.py` (8 tests incl. homomorphic identity). Committed `911f3b3` on `feat/exodus-tokenization-engine`. Productionization = >=2048-bit/EC group + HSM + FF1 (own crate). | exodus | domain-scoped, cross-domain-unlinkable, epoch-rotatable tokens | ✅ a field can be tokenized with the moat properties |
| 5 | **Masking PDP wired into the Catalog Gateway read path** (emits `masking-decision` + BEACON_COMMIT) ← **next** | prophet-platform | 4 (done) | read/export/activate returns masked data + a verifiable receipt — **WKC parity+** |
| 6 | **Catalog Gateway (read/search/resolve/lineage)** + DCAT↔Crystal-Atlas bridge | prophet-platform | — | one logical catalog API; the GMS-equivalent CKAN/DataHub assume |
| 7 | **GrASP adoption behind `extract.mentions.v1`** (open-source; claim/evidence/compliance + `policy_trigger` mining) | sociosphere/new | — | explainable extraction emits real mentions + edge-witness features |
| 8 | **Regis graph runtime** behind the 5 contracts (store + resolve/merge/unmerge + ledger replay) | regis-entity-graph | 2 | resolution decisions actually mutate a graph; unmerge replays |

### P2 — Reach & breadth (after P1)

| # | Gap | Repo | Notes |
|---|---|---|---|
| 9 | Interop emitters: DataHub MCP, CKAN DCAT feed, **CK.org** Zenodo-deposit + DataCite DOI | prophet-platform | depends on 6 |
| 10 | ✅ **MERGED** (PR #20, `3dd12bb`): BEACON_COMMIT sealing (`exodus_seal.py`), ForensicBundle export (`exodus_bundle.py`), account registry (`account_registry.py`), BSM adapter (`bsm_intake.py`). **Still open:** HellGraph ForensicArtifact/CustodyEvent atoms (net-new kernel work). | exodus + hellgraph | Ed25519 + BLAKE3 sealing shipped; graph-atom mapping remains |
| 11 | Full 14-event custody lifecycle (currently 4/14) + content-artifact-catalog ↔ canonical-model field mapping (add exhibit_id, owning_zone, evidence_grade, blake3) | exodus + evidence-intake-kernel | depends on 2,3 |
| 12 | Sherlock indexing runtime (index Regis/Holmes/HELL-ER pointers, delta indexing, policy-filtered retrieval) | sherlock-search | depends on 8 |
| 13 | Operationalize glossary/ontology process: register audience-tag + prime-topic terms in ontogenesis `registry.ttl` + SHACL shapes | ontogenesis | makes tags versioned/provenanced |
| 14 | Benchmark lane golden fixtures + runner (local-vs-cloud + sequence-neutrality) | sociosphere | depends on 7,8 |
| 15 | Audience tagging → MeshRush Omni event family + activation wiring | sociosphere/prophet-platform | depends on 4,7 |

## 2. Complete-gap callouts (things with *zero* runtime today)

- ~~No tokenization engine~~ ✅ reference engine now shipped (`exodus_tokenize.py`); remaining: production crypto (HSM/FF1/large group) + wire into the masking PDP (P1 #5).
- **No Regis graph store** — `resolution-decision`/`edge-witness` have nowhere to land (P1 #8).
- **No GrASP integration** — `grasp-pattern` is a schema with no extractor (P1 #7).
- **No zone enforcement** — `policy-gate` + CHK-01..10 are enums with no executor (P0 #2).
- ~~No canonicalizer~~ ✅ `CANON-v0.1 = json-canonical` shipped in `exodus_seal.py`; BLAKE3-preferred/SHA-256-fallback hashing in place. (CBOR remains a future serializer-spec evolution, not current.)
- **No Catalog Gateway** — catalog metadata is still fragmented; no unified API, no external interop (P1 #6, P2 #9).
- **No HellGraph forensic atoms** — the evidence corpus is not yet a first-class graph citizen (P2 #10).
- **Two pre-existing red conformance lanes** (surfaced by the new aggregate runner, *not* caused by this cycle):
  `validate_hell_er_negative_fixtures.py` expects `hell-er/fixtures/release_pack.external_unredacted_identifier.invalid.json`
  and `validate_er_plus_workspace.py` expects `components/identity_is_prime_reference/docs/70_ER_PLUS_INTRINSIC_GEOMETRY.md`
  — both absent. P2 repo-hygiene: either author the missing fixtures/components or relax the validators. (Left
  untouched here: fabricating them blind would bastardize the negative-test intent.)

## 3. Recommended next action

**Upstream reconciliation (checked this cycle):** the exodus gate engine (PR #22), forensic sealing +
ForensicBundle + account registry + BSM (PR #20) all **merged to `main`** by a parallel session; `CANON-v0.1`
shipped as json-canonical. P0 is therefore complete on `main` (not on my branches — those were dropped to avoid
duplication/contradiction). The **tokenization reference engine (P1 #4)** is now built (`911f3b3`).

Next: **P1 #5** — wire the masking PDP into the Catalog Gateway read path (consume `tokenization-profile` +
`exodus_tokenize`, emit `masking-decision` + BEACON_COMMIT via the shipped `exodus_seal`). That is the visible
WKC-parity-and-beyond win and it now has all its dependencies on `main`. Then **P1 #6** (Catalog Gateway + DCAT),
**#7** (GrASP), **#8** (Regis runtime); P2 = interop emitters, HellGraph atoms, Sherlock runtime, glossary.
