# PFK Stack Integration Map v0

Status: controller contract map  
Authority: `SocioProphet/sociosphere` for workspace orchestration  
PFK authority: `SocioProphet/Heller-Godel/proof_fabric_kernel/` at the commit pinned in `manifest/proof-workspace.toml`

## Control sentence

Heller-Godel owns the proof fabric. Sociosphere orchestrates it. AgentPlane runs it. Holmes and Sherlock reason over it. Memory Mesh remembers proposals about it. Guardrail Fabric and Policy Fabric govern it. Prophet Workspace makes it usable. No repository may turn receipts into truth by itself.

## Non-promotion rule

Schema validity is envelope validity, not mathematical truth. A valid PFK claim-ledger row, Event-IR trace, ProofArtifact envelope, calibration bundle, validator result, or CI result is a precondition for review. It is not theorem evidence by itself and it does not promote a claim.

## Authority split

| Surface | Repo | Authority |
| --- | --- | --- |
| PFK schema authority | `SocioProphet/Heller-Godel` | Owns `PFK-SCHEMA-001..004`, Schema Catalog, anti-seed, claim grammar, and framework-core dependency pins. |
| Proof workspace controller | `SocioProphet/sociosphere` | Owns manifest membership, proof-slice routing, gate execution semantics, evidence-event shape, promotion/demotion/quarantine/archive decisions, and workspace snapshots. |
| Domain proof engines | Heller-Winters, Heller-Einstein, Heller-Dirac, BSD, NP, NS, Hodge, Yang-Mills, HPHD, identity-prime | Own mathematics, fixtures, notebooks, scripts, papers, repo-local tests, non-claims, and obstruction walls. |
| Execution control plane | `SocioProphet/agentplane` | Runs bounded proof gates and emits validation, placement, run, replay, receipt, and PFK-compatible evidence artifacts. |
| Cognition and discovery | `SocioProphet/holmes`, `SocioProphet/sherlock-search` | Sherlock anchors evidence; Holmes proposes, explains, verifies, and reports contradictions. They do not make admission decisions. |
| Memory and learning | `SocioProphet/memory-mesh`, optional memU sidecar | Produces review-only memory/context proposals. Durable writeback and claim promotion remain gated. |
| Governance | `SocioProphet/guardrail-fabric`, `SocioProphet/policy-fabric`, `SocioProphet/mcp-a2a-zero-trust`, `SocioProphet/agent-registry` | Enforce action admission, policy, grants, tool/provider/agent authority, revocation, and human approval gates. |
| Semantics | `SocioProphet/semantic-serdes`, `SocioProphet/ontogenesis` | Preserve plane, truth class, time model, merge model, provenance, governance status, replayability, RDF/JSON-LD/SHACL promotion, and ontology lifecycle. |
| Product surface | `SocioProphet/prophet-workspace`, `SocioProphet/prophet-platform` | Presents Proof Workroom surfaces and deploys runtime services after contracts stabilize. |

## Canonical PFK surfaces

| Identifier | Required interpretation in Sociosphere |
| --- | --- |
| `PFK-SCHEMA-001` | Claim-ledger row envelope. Claim grade, distance tier, citation pins, review state, and truth interpretation remain domain/controller responsibilities. |
| `PFK-SCHEMA-002` | Event-IR trace for operator invocation, structured computation, model/tool call, source import, validation run, or proof-gate execution. |
| `PFK-SCHEMA-003` | ProofArtifact envelope for proof steps, computation steps, normalized source imports, finite checks, and transformation artifacts. |
| `PFK-SCHEMA-004` | CalibrationBundle envelope for model/tool comparisons, numerical baselines, sanity checks, finite arithmetic runs, and harness results. |

## Required loop

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
  -> Promote / Quarantine / Archive
```

Mapped to the estate:

1. `Lampstand`, `Sherlock`, `GAIA`, `Orion`, source imports, and repo-local test fixtures observe.
2. `Sherlock`, `GAIA`, `Ontogenesis`, and PFK references anchor.
3. `Semantic SerDes`, `Ontogenesis`, and PFK adapter manifests normalize.
4. Domain repos and Holmes propose claims, proof steps, contradiction reports, and non-claims.
5. Holmes explains and reports contradictions without policy admission.
6. Repo-local gates, PFK validators, AgentPlane runs, and calibration bundles verify.
7. Guardrail Fabric, Policy Fabric, MCP/A2A Zero Trust, and Agent Registry govern.
8. AgentPlane executes only bounded bundles.
9. PFK Event-IR, ProofArtifact, CalibrationBundle, and AgentPlane ReplayArtifact record.
10. Memory Mesh receives review-only learning/context proposals.
11. Sociosphere records promotion, demotion, quarantine, archive, obstruction, and workspace snapshot events.

## Proof adapter duties

Every proof-facing repository that claims Sociosphere proof-apparatus compatibility must publish or be able to synthesize a `proof-adapter.json` compatible with `standards/proof-apparatus/proof-adapter.schema.json`.

The adapter must identify:

- repository and domain;
- controller protocol;
- PFK authority pin when the repo claims PFK compatibility;
- claim records;
- gate records;
- non-claim records;
- obstruction walls;
- PFK output references when emitted.

The adapter must not mark a claim as `promoted`. Promotion is controller-visible only.

## PFK maturity levels

| Level | Meaning |
| --- | --- |
| `M0` | Compatibility target identified. No native PFK artifacts required. |
| `M1` | Pinned Heller-Godel PFK dependency declared. |
| `M2` | Example PFK artifacts validate. |
| `M3` | Native PFK-compatible receipt emission is part of normal workflow. |
| `M4` | Mature consumer: pinned dependency, CI validation, migration notes, anti-seed compliance, replay/revalidation behavior. |
| `authority` | Only Heller-Godel PFK may use this level in the proof workspace manifest. |

## Sidecar rule for Odysseus and memU-style imports

Self-hosted workbench or proactive memory systems may be used as sidecars only. They can help capture context, compare models, draft documents, or propose memory. They cannot become claim authority, schema authority, proof authority, policy authority, or durable memory authority.

Sidecar outputs must enter the estate as one of:

```text
sidecar observation
  -> Memory Mesh review-only proposal
  -> Holmes/Sherlock evidence or explanation candidate
  -> AgentPlane bounded run
  -> PFK-compatible receipt
  -> Sociosphere controller decision
```

## Forbidden inferences

- PFK envelope validates, therefore the claim is true.
- Event-IR trace exists, therefore the mathematical step is correct.
- ProofArtifact validates, therefore the proof step is correct.
- CalibrationBundle validates, therefore a numerical observation is theorem evidence.
- CI is green, therefore audit is complete.
- Memory retrieval exists, therefore it is durable truth.
- Model output is coherent, therefore it is admitted truth.
- Cross-repo analogy exists, therefore a theorem transfers.

## First implementation target

The first implementation target is a controller-side proof adapter bridge:

```text
manifest/proof-workspace.toml
  -> catalog/proof-repo-roles.yaml
  -> repo-local proof-adapter.json
  -> AgentPlane gate bundle
  -> PFK Event-IR / ProofArtifact / CalibrationBundle
  -> Sociosphere PromotionDecision or PreimageObstruction
  -> workspace snapshot
```

The immediate deliverable is a contract and validation lane, not a theorem claim and not a production runtime.
