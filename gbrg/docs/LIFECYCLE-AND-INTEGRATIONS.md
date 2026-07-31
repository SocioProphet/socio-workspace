# GBRG — Whole Lifecycle & Functional Integrations

**Governed Blast-Radius Graph.** Turns source code into a governed, provenance-bearing risk graph:
every changed function becomes a claim with a *declared* `epistemicLevel` and a written *why*, not a black-box score.

This doc is the labelled source-of-truth. It is deliberately honest about maturity so nothing is
over-claimed (the whole thesis is anti-over-claim).

## Maturity legend
- ✅ **REAL** — built **and independently re-verified** this session (tests run, artifact inspected)
- 🟡 **PARTIAL/STUB** — scaffolded, compiles, not fully wired
- ⬜ **PLANNED** — designed with a known seam, not built
- 🔬 **RESEARCH** — net-new, explicitly *not yet real*; never presented as working until it is

---

## 1. The lifecycle (end to end)

| # | Stage | What happens | Status |
|---|-------|--------------|--------|
| 1 | **Trigger** | manual CLI `gbrg-analyze <path>` | ✅ |
|   |  | git commit/PR hook → incremental re-parse (ast_hash diff) | ⬜ |
|   |  | MCP call from an agent | 🟡 |
|   |  | CI gate (prophet-platform) | ⬜ |
| 2 | **Parse** | tree-sitter (Rust/Python/TypeScript) → `SemanticCell`s + edges (`calls`/`imports`/`inherits`) | ✅ |
|   |  | test-file detection → `TESTED_BY` edges | ✅ |
|   |  | cross-file symbol resolution (ambiguous never fabricated) | ✅ |
|   |  | per-node `ast_hash` (sha256) for incremental diffing | ✅ |
|   |  | synapseiq LSP assist (TS/JS references/defs) | ⬜ |
| 3 | **Ingest** | write cells/edges into HellGraph `graphdb::Store`; `freeze()` → CSR index | ✅ |
| 4 | **Blast-radius** | `dependents_count` (in-degree, minus TESTED_BY); reverse/transitive fan-in (BFS); test-reach; churn from real `git log` | ✅ |
| 5 | **Score** | `blast_radius` ∈ [0,1]; `epistemicLevel` derivation with **overridable** `ScoringConfig` thresholds | ✅ |
| 6 | **ProofArtifact** | emit all schema fields; `epistemicLevel` enum inherited verbatim from SCOPE-D; `synthetic`≠codegen (codegen → `generated` flag); human-readable `derivation` | ✅ |
| 7 | **Govern** | agent-registry manifest gate + durable **sealed** audit sink (every include/exclude a declared decision) | ⬜ (next wave) |
|   |  | HellGraph `graphdb` receipts (sha256 + WAL) available for the sink | ✅ |
| 8 | **Serve** | MCP tools (`impact_query`/`minimal_context_query`/`graph_status`) returning ProofArtifacts | 🟡 → ⬜ |
| 9 | **Reason** | PLN risk-propagation along call edges (transitive risk + confidence decay) | ⬜ (track 1) |
|   |  | what-if recomputation (intervention/counterfactual — *not Pearl*) | ⬜ (track 2) |
|   |  | true causal inference (do-calculus / provable cause→failure) | 🔬 (track 3) |
| 10 | **Feed the fabric** | `RepoGraphAdapter` → `repo-governance-observation.v0` into the evidence plane; `nrg:CodeCell` ontology extension | ⬜ |
| 11 | **Consume** | SCOPE-D `computeRiskScore` (blast_radius 0–1 feeds it directly); neurosymbolic-repo-graph-reasoner | ⬜ |
| 12 | **NL-evidence lane** | link-grammar + IBM AMR parse docstrings/comments/commits → AtomSpace evidence | ⬜ (separate track) |

**Proven end-to-end today:** stages 1(CLI)→6. Point `gbrg-analyze` at a repo and get governed ProofArtifacts
with a real `empirical` vs `speculative` spread (verified: 10 empirical / 39 speculative on gbrg-core).

---

## 2. Functional integrations (each: what · direction · seam · status)

| Integration | Role | Seam | Status |
|-------------|------|------|--------|
| **HellGraph** (`hg_analytics::graphdb`) | graph substrate | Rust crate dep (consume-only, never edit); write/BFS/receipts | ✅ |
| **SCOPE-D** | epistemicLevel + ProofArtifact schema owner; risk-score consumer | inherit `proof-artifact.schema.json`; feed `computeRiskScore` | ✅ inherit / ⬜ feed |
| **agent-registry** | manifest gate + zero-trust authority | subprocess `authorize.py`; emit `TrustOpsAgentAuthorityDecision` | ⬜ |
| **mcp-a2a-zero-trust** (spec repo) | zero-trust contract for the MCP surface | SPIFFE id, capability registry, per-call Grant, ledger events | ⬜ |
| **noetica-mcp** (`Noetica/lib/a2a`) | grant-check / trust pattern to copy | `checkToolGrant` + `emitToolGrantCheck` pattern | ⬜ |
| **neurosymbolic-repo-graph-reasoner** | governance corpus loop over repo RDF | implement `RepoGraphAdapter`; emit evidence-plane observations | ⬜ |
| **synapseiq** | TS/JS LSP assist (NOT tree-sitter — that was a myth) | subprocess HTTP / stdio LSP | ⬜ |
| **link-grammar / IBM AMR** | NL-evidence parsers | link-grammar=LGPL (blessed subprocess exception); AMR=Apache | ⬜ |
| **prophet-platform CI** | ship / enforce | check-style gate | ⬜ |
| **sovereign gitea** (`code.socioprophet.ai`) | durable private upstream | in-cluster push; repo `socioprophet/gbrg` (private) | ✅ |

---

## 3. Autonomy — how it runs without a human

Target loop: **git commit → hook → incremental parse of changed files → ingest delta → re-score →
emit ProofArtifacts → gate + seal to ledger → MCP surface updated → agents query impact.**

Today: the analyze step (`analyze_path`) is real; the hook, the gate/ledger, and the MCP serving are the
work remaining to close the loop into a hands-off system. The recommended build order below closes it.

## 4. Language / runtime map
- **Rust** — `gbrg-core`, `gbrg-parser`, `gbrg-analyze` (bin/lib), `gbrg-napi` (bridge). Graph + parse + score. ✅
- **TypeScript** — `gbrg/mcp` (MCP surface) + PLN risk-propagation (reasoning is TS-only in HellGraph). 🟡/⬜
- **Python** — governance wiring: `RepoGraphAdapter`, agent-registry gate calls. ⬜
- **JSON-Schema** — the contracts (SemanticCell, GraphEdge, BlastRadiusProofArtifact). ✅

## 5. Recommended build order (in progress)
1. **Shared agent-registry gate foundation** — one module serving governance-teeth **and** MCP zero-trust (same seam). ← in flight
2. **MCP surface** — a2a-zero-trust conformant, returns ProofArtifacts.
3. **RepoGraphAdapter evidence-producer** + `nrg:CodeCell` ontology extension.
4. **Causal track 1** (PLN risk-propagation), **track 2** (what-if), **track 3** (research).
5. **Benchmark** vs code-review-graph + **Phase 6.2 pitch-deck** (honest maturity labels).

## 6. Artifact & backup inventory
- Branches (stacked, each independently green): `feat/gbrg-spine` → `-parser` → `-scoring` → `-integration` → `-spectrum`.
- Durable upstream: **`socioprophet/gbrg`** (private) on sovereign gitea `code.socioprophet.ai`; commits verified.
- Local: verified git bundle in `~/dev/_gbrg_backups/`.

## 7. Open items / debts
- Revoke bootstrap token **`gbrg-boot`** on gitea `estate-mirror` (no CLI revoke in gitea 1.27 → UI).
- **Estate-wide unified SSO** (DEFERRED — design session after GBRG build): every `socioprophet.ai` service (`code.socioprophet.ai` gitea, `registry.socioprophet.ai` zot, etc.) should authenticate with the **same login as socioprophet.com** (shared IdP; gitea `ENABLE_OPENID_SIGNIN` already set). Auth change across live services → design + confirm first, do NOT apply blindly.
- Parser: cross-file resolution excludes Rust macro-body calls (tree-sitter limit) → coverage under-counted (safe direction).
