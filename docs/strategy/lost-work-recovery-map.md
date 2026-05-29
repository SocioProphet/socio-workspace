# Lost Work Recovery Map

Status: active recovery index  
Coordination authority: `SocioProphet/sociosphere`  
Tracking issue: #408

## Purpose

This document records important conceptual, product, governance, and research threads that were previously developed across the estate but have fallen out of active backlog visibility.

The recovery map converts those threads into governed estate objects. A recovered thread must have an owner repo, an explicit archive status, or a frozen return condition. The map does not promote speculative claims to theorem status, implementation status, or product readiness.

## Non-goals

This document does not replace repo-local issue tracking. It does not assert that any recovered research thread is true, complete, implemented, or production-ready. It does not move authority from domain repos into Sociosphere. Sociosphere coordinates the recovery ledger; the owning repos retain doctrine, product, implementation, and claim authority.

## Status classes

- `active backlog`: should be implemented, documented, or operationalized now.
- `authority-plane doctrine`: should become a vocabulary, policy, schema, SHACL shape, or governance-control artifact in the authority repo.
- `product substrate`: should become part of a user-facing or agent-facing platform/workroom/runtime architecture.
- `research foundation`: belongs in Heller-Godel, Heller-Einstein, or a Clay-program foundation repo, with claim boundaries preserved.
- `frozen with return condition`: not active, but not discarded; may return only when named prerequisites are satisfied.
- `archive-only`: preserved for provenance and future review, with no current action.

## Recovery table

| Thread | Why it matters | Owning repo | Status | First action |
|---|---|---|---|---|
| DoNotLearn / DoNotLink privacy doctrine | Prevents latent identity reconstruction across memory, graph, fraud, and agent systems by blocking unsafe joins, graph paths, latent-space reuse, and basis-vector leakage. | `SocioProphet/ontogenesis` | authority-plane doctrine | Draft vocabulary and boundary note for non-linkability and non-learnability constraints. |
| Systems-learning-loops as institutional learning canon | Preserves how the estate learns from evidence, failure, delivery, doctrine, experiments, and postmortems. | `SocioProphet/systems-learning-loops` | active backlog | Create a learning-loop canon index and map downstream consumers. |
| Governed memory representation strata | Separates raw evidence, frames, schemas, symbolic relations, statistics, vectors, learned latent layers, governance, and actions. | `SocioProphet/ontogenesis`; `SocioProphet/prophet-platform` | authority-plane doctrine | Draft memory-representation strata and promotion boundaries. |
| Common IR kernel | Provides a shared object model for proof/governance tracks: ClaimIR, ObjectIR, ContextIR, EvidenceIR, MorphismIR, ObligationIR, VerifierIR, ReceiptIR, LedgerIR. | `SocioProphet/proof-fabric-kernel` | active backlog | Define an IR-family skeleton with non-claiming semantics. |
| Boundary geometry / spectral-boundary grammar | Bridges boundary conditions, admissible modes, symmetry, recurrence, spectral behavior, and lawful-learning grammar. | `SocioProphet/heller-godel-core`; `SocioProphet/heller-einstein` | research foundation | Create a boundary grammar note with explicit claim grades. |
| TriTRPC typed control-plane substrate | Candidate typed protocol surface for agent, workroom, memory, and control-plane communication. | `SocioProphet/TriTRPC` | product substrate | Audit repo state and define v0.1 scope. |
| slash-topics governed topic-pack membrane | Candidate semantic membrane for topic packs, Holmes/Sherlock/Search interoperability, and navigable workroom intelligence. | `SocioProphet/slash-topics` | product substrate | Define a topic-pack contract and authority boundaries. |
| workspace-inventory estate ledger | Converts repo, branch, PR, issue, CI, doctrine, and capture state into a governed estate inventory. | `SocioProphet/workspace-inventory`; `SocioProphet/sociosphere` | active backlog | Define estate inventory schema and Sociosphere registration bridge. |
| speechlab audio-first review/runtime surface | Captures spoken review, audio-friendly sectioning, dictated corpus ingestion, and human-machine channel testing. | `SocioProphet/speechlab` | product substrate | Define an audio review loop and confusability fixtures. |
| Heller-Godel calculus-invariant character paper | Preserves the invariant layer that separates calculus-relative presentation from proof-class/statistical/character data. | `SocioProphet/heller-godel-core` | research foundation | Promote to a Tier 0/Tier 1 foundation note with strict claim boundaries. |
| Heller-Godel five-predicate epistemic grammar | Separates provability, truth, projection, recognition, and descent/obstruction. | `SocioProphet/heller-godel-core` | research foundation | Add to foundation grammar backlog; prevent predicate collapse. |
| Godel 1949 time/fibration bridge | Potential disciplined bridge among S3/S2/S1 projection, causal phase, Heller-Einstein, and time theory. | `SocioProphet/heller-einstein`; `SocioProphet/heller-godel-core` | frozen with return condition | Return only as a typed bridge note with no physics claim promotion. |
| Prime Harness SPEC v0.2 | Concrete analytic-number-theory harness scope for sieve oracle, zero-table provenance, residual machinery, Li quadrature, manifests, and integration tests. | `SocioProphet/hphd-zeta-mirror-lattice` | active backlog | Reconcile with current HPHd/Zeta repo strategy before implementation. |
| Wythoff / Schwarz finite-generative syntax | Encodes finite generative syntax for symmetry, tessellation, reflection groups, and lawful object generation. | `SocioProphet/heller-godel-core` | research foundation | Add as a boundary/symmetry grammar candidate. |
| Moufang-loop holonomy after moduli construction | Advanced future target with a known prerequisite. | `SocioProphet/heller-godel-core` | frozen with return condition | Return only after moduli construction exists. |
| Operator L_phi and recognition dynamics | Future bridge between proof objects, recognition, and lawful-learning validation. | `SocioProphet/heller-godel-core` | frozen with return condition | Return only after `L_phi` is typed and defined. |
| Curry-Howard-Lambek categorical setup | Potential formal bridge across proofs, programs, categories, semantics, and proof-fabric. | `SocioProphet/heller-godel-core`; `SocioProphet/proof-fabric-kernel` | frozen with return condition | Return after common IR kernel has stabilized. |
| Lawful-learning monograph TeX source | Publication-scale canonical exposition distinct from repo-local docs. | TBD | archive-only | Locate and classify source before promotion. |
| Delivery Excellence integration target | Turns governance and doctrine into repeatable delivery quality. | TBD | active backlog | Locate authority repo and map delivery-loop consumers. |

## Priority recovery order

1. DoNotLearn / DoNotLink privacy doctrine.
2. Systems-learning-loops as institutional learning canon.
3. Governed memory representation strata.
4. Common IR kernel.
5. Boundary geometry / spectral-boundary grammar.
6. workspace-inventory estate ledger.
7. TriTRPC typed control-plane substrate.
8. slash-topics governed topic-pack membrane.
9. speechlab audio-first review/runtime surface.
10. Heller-Godel calculus-invariant character paper.

## Do-not-lose-again rule

A recovered thread may not remain as unowned memory. It must resolve into exactly one of these dispositions:

1. assigned owner repo with an issue or committed control artifact;
2. explicit archive-only status with provenance notes;
3. frozen-with-return-condition status with named prerequisites;
4. closed as intentionally not pursued, with rationale.

## Immediate follow-on issues

The first follow-on tranche should open or update repo-local issues for the top five active targets:

- `SocioProphet/ontogenesis`: DoNotLearn / DoNotLink and governed memory strata.
- `SocioProphet/systems-learning-loops`: learning-loop canon index.
- `SocioProphet/proof-fabric-kernel`: common IR-family skeleton.
- `SocioProphet/heller-godel-core`: boundary geometry / spectral-boundary grammar and invariant-character foundation note.
- `SocioProphet/workspace-inventory`: estate-ledger schema and Sociosphere registration bridge.

## Claim boundary

Recovery is not endorsement. Recovery means the estate has enough prior signal that the thread deserves explicit disposition. Research items retain their prior epistemic grade until promoted by repo-local evidence, review, and acceptance criteria.
