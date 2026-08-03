# ADR-003 — Supply-chain operational-risk scoring over the governed blast-radius graph

Status: Accepted
Date: 2026-08-03
Scope: `gbrg/contracts/supply-chain-*` + `gbrg/governance/supply_chain_risk.py`
Cross-ref: prophet-workspace#108 (item 2)

## Context

The estate needs a software supply-chain operational-risk scoring capability on the
GBRG risk plane. A framework already exists as a workbook
(`software_supply_chain_operational_risk_framework_v0_2_bian_fico.xlsx`,
sheets: Ontology, Weights, Node/Path/Cluster_Assessment, Controls_Evidence,
KRI_KCI, BIAN_Crosswalk, FICO_Crosswalk). The task is to **consume, not fork** it:
bind its taxonomy and thresholds into GBRG's existing governance spine rather than
build a parallel scorer.

## Decisions

### 1. Weights and thresholds are DECLARED DATA, never magic numbers
`contracts/supply-chain-risk-weights.v0.json` transcribes the workbook verbatim:
the six inherent factors (K,P,E,O,C,V; Σ=1.0), the six control-efficacy families
(Σ=1.0), the four cluster common-mode components (Σ=1.0), the rating thresholds
(Low/Moderate/High/Critical), the controls-evidence tier-0 minimums, and the 12
KRI/KCI bands. `supply_chain_risk.py` loads this file; changing a weight is a data
change, reviewable in isolation.

### 2. Scored verdict, never a bare number — extends the canonical ProofArtifact
`contracts/supply-chain-risk-proof-artifact.schema.json` binds via `allOf` to the
estate-canonical ProofArtifact v1 (`$ref` to its `epistemicLevel` enum from
`$defs`; no copy-paste). Every assessment (node | path | cluster) carries its
inherent/control/residual scores, rating, controls-evidence, KRI evaluations, the
crosswalk bindings, and an Assay-style verdict.

- **Node residual** = inherent × (1 − control_efficacy).
- **Path risk** = 1 − Π(1 − residual_i) (noisy-OR: any node on the service chain
  failing breaks the service).
- **Cluster residual** = common-mode inherent × (1 − resilience_control), with
  normalized HHI computed from provider shares.

### 3. Teeth reuse the Assay verdict + the receipt spine
The ok/sad/bad projection follows the estate **Assay** model (`method=computed`
over declared weights) and projects at assessment time to **VERIFIES** (ok) /
**FLAGGED** (sad) / **REJECTED** (bad). Each assessment is sealed as a
hash-chained event on the existing `gbrg.governance.ledger` (sha256 = FIPS-180-4)
and is verified, unchanged, by `ledger.verify_ledger` — the same durable,
tamper-evident receipt spine used by the context-inclusion gate and the MCP
surface. No new ledger machinery was introduced.

**Teeth, both ways (fail-closed on missing evidence):**
- Evidenced controls + all KRIs within threshold → **VERIFIES** (PROVED / empirical).
- Control efficacy claimed with no evidence ref, or a tier-0 subject with no
  controls-evidence at all → **REJECTED** (FAILED / rejected). An unverifiable
  control claim is not evidence of low risk; unevidenced families also earn zero
  efficacy in the score.
- A KRI/KCI in the RED band (threshold breach) → **FLAGGED** (BLOCKED / speculative).
- A crosswalk term absent from the governed ontology → **REJECTED**.

### 4. The crosswalk binds control taxonomy to the GOVERNED ontology
`contracts/supply-chain-bian-fico-crosswalk.v0.json` carries the single
`governed_ontology` allow-list (node/edge/event/service types + control families +
risk objects, from the workbook Ontology/Controls_Evidence sheets) and maps each
BIAN service domain / FICO capability to those governed terms. A crosswalk entry
that binds a term outside the allow-list is rejected
(`validate_crosswalk_term` / `validate_crosswalk`) — a crosswalk cannot smuggle an
ungoverned control term into the estate vocabulary.

## Consequences

- Verified by `gbrg/governance/test_supply_chain_risk.py` (41 checks, all four
  teeth + weight-consistency + ledger tamper-evidence).
- **Follow-up (@mdheller):** a live scoring pipeline that pulls real node/path/
  cluster topology off the HellGraph blast-radius graph (via `gbrg-analyze` /
  the RepoGraphAdapter) instead of caller-supplied factors, and emits these
  artifacts onto the evidence plane. This ADR ships the contract + scorer + teeth;
  the live wiring is deliberately out of scope for a small reviewable PR.
