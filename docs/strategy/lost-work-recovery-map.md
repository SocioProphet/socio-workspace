# Lost Work Recovery Map

Status: active recovery ledger; top-ten recovery tranche closed  
Coordination authority: `SocioProphet/sociosphere`  
Tracking issue: #408  
Last tranche review: 2026-05-30

## Purpose

This document records important conceptual, product, governance, and research threads that were previously developed across the estate but fell out of active backlog visibility.

The recovery map converts those threads into governed estate objects. A recovered thread must have an owner repo, an explicit archive status, a frozen return condition, or an intentional non-pursuit rationale. The map does not promote speculative claims to theorem status, implementation status, or product readiness.

## Non-goals

This document does not replace repo-local issue tracking. It does not assert that any recovered research thread is true, complete, implemented, or production-ready. It does not move authority from domain repos into Sociosphere. Sociosphere coordinates the recovery ledger; the owning repos retain doctrine, product, implementation, and claim authority.

## Status classes

- `active backlog`: should be implemented, documented, or operationalized now.
- `authority-plane doctrine`: should become a vocabulary, policy, schema, SHACL shape, or governance-control artifact in the authority repo.
- `product substrate`: should become part of a user-facing or agent-facing platform/workroom/runtime architecture.
- `research foundation`: belongs in Heller-Godel, Heller-Einstein, or a Clay-program foundation repo, with claim boundaries preserved.
- `frozen with return condition`: not active, but not discarded; may return only when named prerequisites are satisfied.
- `archive-only`: preserved for provenance and future review, with no current action.
- `recovered`: durable owner and control artifact exist.
- `corrected`: prior recovery assumption was wrong and has been replaced by a verified authority surface.
- `already captured`: the thread already had a durable authority surface before this recovery tranche.

## Top-ten recovery disposition table

| # | Thread | Owning repo / authority surface | Disposition | Recovery artifacts |
|---|---|---|---|---|
| 1 | DoNotLearn / DoNotLink privacy doctrine | `SocioProphet/ontogenesis` | recovered | `docs/specs/privacy-nonlinkability-doctrine-v0.md`; `Platform/GovernedIntelligence/privacy-nonlinkability.ttl`; `contexts/governed-intelligence.context.jsonld`; `shapes/privacy_nonlinkability.shacl.ttl`; `examples/privacy-nonlinkability/`; `scripts/validate_privacy_nonlinkability_examples.py`; `Makefile` validation target. |
| 2 | Systems-learning-loops as institutional learning canon | `SocioProphet/systems-learning-loops` | recovered | `docs/institutional-learning-canon-v0.md`; `kb/topics/institutional-learning.yaml`; `kb/patterns/pattern-template.md`; `kb/patterns/institutional-amnesia.md`; `kb/receipts/README.md`; `kb/receipts/lost-work-recovery-map.receipt.yaml`. |
| 3 | Governed memory representation strata | `SocioProphet/ontogenesis` | recovered | `docs/specs/governed-memory-representation-strata-v0.md`; `Platform/GovernedIntelligence/memory-representation-strata.ttl`; `contexts/governed-intelligence.context.jsonld`; `examples/memory-representation-strata/`; `shapes/memory_representation_strata.shacl.ttl`; `scripts/validate_memory_representation_strata_examples.py`; `Makefile` validation target. |
| 4 | Common IR kernel / proof-fabric kernel | `SocioProphet/Heller-Godel/proof_fabric_kernel/` | corrected | Prior standalone `SocioProphet/proof-fabric-kernel` assumption superseded. Active PFK lives in Heller-Godel. Added `proof_fabric_kernel/docs/ClayProgram_PFK_ConsumerContract_v0.md`; corrected and closed #416. |
| 5 | Boundary geometry / spectral-boundary grammar | `SocioProphet/Heller-Godel` | recovered | `docs/framework-core/boundary-spectral-grammar-v0.md`; indexed in `docs/framework-core/README.md`. |
| 6 | workspace-inventory estate ledger | `SocioProphet/workspace-inventory` | recovered | `docs/estate-ledger-v0.md`; optional estate/recovery/adoption/validation/drift fields in `inventory/schema.json`; initial annotations in `inventory/repos.yaml`; enum hardening in `tools/validate_inventory.py`. |
| 7 | TriTRPC typed control-plane substrate | `SocioProphet/TriTRPC` | recovered | `docs/vnext/control-plane-substrate-recovery-v0.md`; indexed in `docs/vnext/README.md`; no v1/vNext normative protocol changes. |
| 8 | slash-topics governed topic-pack membrane | `SocioProphet/slash-topics` | recovered | `docs/governed-topic-pack-membrane-v0.md`; indexed in `README.md`; no schema/runtime changes. |
| 9 | speechlab audio-first review/runtime surface | `SocioProphet/speechlab` | recovered | `README.md`; `docs/audio-first-review-runtime-v0.md`; no runtime/model/ingestion changes. |
| 10 | Heller-Godel calculus-invariant character paper | `SocioProphet/Heller-Godel` | already captured | Existing `docs/manuscripts/calculus_invariant_characters_v2_1_3.md`; canonical Paper I / D1 rewrite at `docs/manuscripts/paper_i_deligne_cohomological_phase_characters.md`; framework-core README already describes active proof-character core. No new artifact required. |

## Additional recovered / deferred threads

| Thread | Owning repo | Status | Disposition / return condition |
|---|---|---|---|
| Heller-Godel five-predicate epistemic grammar | `SocioProphet/Heller-Godel` | research foundation | Still deferred. Needs separate framework-core note only after checking existing coverage. |
| Godel 1949 time/fibration bridge | `SocioProphet/Heller-Godel`; possible future Heller-Einstein surface | frozen with return condition | Return only as a typed bridge note with no physics claim promotion. |
| Prime Harness SPEC v0.2 | `SocioProphet/hphd-zeta-mirror-lattice` | active backlog | Still requires repo-specific reconciliation before implementation. |
| Wythoff / Schwarz finite-generative syntax | `SocioProphet/Heller-Godel` | partially recovered | Captured as part of `docs/framework-core/boundary-spectral-grammar-v0.md`; stronger use requires proof-bearing domain artifact. |
| Moufang-loop holonomy after moduli construction | `SocioProphet/Heller-Godel` | frozen with return condition | Return only after moduli construction exists. |
| Operator L_phi and recognition dynamics | `SocioProphet/Heller-Godel` | frozen with return condition | Return only after `L_phi` is typed and defined. |
| Curry-Howard-Lambek categorical setup | `SocioProphet/Heller-Godel`; PFK-adjacent only if needed | frozen with return condition | Return after proof-fabric / framework IR usage stabilizes. |
| Lawful-learning monograph TeX source | TBD | archive-only | Locate and classify source before promotion. |
| Delivery Excellence integration target | TBD | active backlog | Locate authority repo and map delivery-loop consumers. |

## Do-not-lose-again rule

A recovered thread may not remain as unowned memory. It must resolve into exactly one of these dispositions:

1. assigned owner repo with committed control artifact;
2. explicit archive-only status with provenance notes;
3. frozen-with-return-condition status with named prerequisites;
4. blocked with blocker reference;
5. superseded by a verified authority surface;
6. closed as intentionally not pursued, with rationale.

## Consolidation follow-ons

The top-ten recovery tranche is closed. Remaining consolidation work should be limited and explicit:

1. Add or update estate-ledger annotations in `SocioProphet/workspace-inventory` for all newly touched authority repos.
2. Add learning receipts in `SocioProphet/systems-learning-loops` for the main recovered doctrines, not every individual file.
3. Resume product/research execution from the recovered authority surfaces instead of continuing generic recovery.

## Claim boundary

Recovery is not endorsement. Recovery means the estate has enough prior signal that the thread deserves explicit disposition. Research items retain their prior epistemic grade until promoted by repo-local evidence, review, and acceptance criteria.
