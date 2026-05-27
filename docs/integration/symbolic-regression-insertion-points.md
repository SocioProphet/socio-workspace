# Symbolic Regression Insertion Points

Status: v0.1 doctrine capture.

This document captures the symbolic-regression / equation-discovery field map as a CHRONOS sublane. It extends the neuro-symbolic reasoning work already captured in SocioSphere, but it is not the same lane. The controlling object here is an equation or program candidate that must move through evidence, replay, semantic review, and governance before it can become a law, ontology assertion, policy, controller, or pedagogical answer.

This document does not vendor papers, install tools, promote schemas, or assign runtime authority.

## Position

Symbolic regression and scientific-law discovery are CHRONOS carrier sources, not authorities.

```text
data / telemetry / graph / notebook / experiment
  -> SR method run
  -> equation candidate
  -> evidence + metrics + complexity + operator library
  -> SRAssertion proposal
  -> ontology / policy / replay review
  -> admitted law, rejected candidate, or learning update
```

The output of PySR, SINDy, TPSR, SNIP, LLM-SR, FunSearch-style program search, KAN-based extraction, or Hamiltonian-learning workflows is an `EquationCandidate` or `ProgramCandidate`. It is not a law by itself.

## Field map

| Track | Example methods | CHRONOS role | Forbidden promotion |
|---|---|---|---|
| GP / evolutionary SR | PySR, SymbolicRegression.jl, InceptionSR | equation candidate generation and baseline tooling | equation as ontology truth |
| Sparse regression / system identification | SINDy, SINDy-SI | telemetry or physical-dynamics model candidate | telemetry model as policy authority |
| Transformer pretraining | NeSymReS, E2E SR Transformer, SymFormer | pretrained expression generator | one-pass equation as admitted law |
| MCTS decoding | Symbolic Physics Learner, TPSR | feedback-aware search over expressions | search score as proof |
| Cross-modal pretraining | SNIP | symbolic-numeric bridge and latent candidate retrieval | latent similarity as validation |
| LLM evolutionary SR | LLM-SR, LaSR, ICSR, SR-LLM | domain-prior-assisted hypothesis search | LLM equation as evidence |
| LLM program search | FunSearch-style search, AlphaTensor-style precedent | program candidate search with evaluator | generated program as policy/controller without admission |
| KAN-based SR | KAN, KAN-SR, KAN-LEx | interpretable function decomposition and formula extraction | spline/plot/extraction as hard truth |
| Physics-constrained SR | units-guided SR, SINDy-SI, materials SR | constrained equation proposal | dimensional consistency as sufficient validation |
| Benchmarking | SRBench, Feynman, LLM-SRBench | evaluation surface and regression corpus | benchmark score as production admission |

## Seven insertion points

### 1. memory-mesh: symbolic-numeric bridge

`SocioProphet/memory-mesh` is the natural home for a symbolic-numeric bridge service. A SNIP-style bridge may align symbolic expressions, graph concepts, and numeric observations in a shared latent space.

Candidate service name:

```text
symbolic-numeric-bridge
```

Allowed outputs:

- latent-neighbor suggestions;
- candidate symbolic expressions;
- graph relation candidates;
- cluster-to-symbol hypotheses;
- equation search seeds.

Forbidden outputs:

- canonical ontology assertions;
- graph truth;
- memory promotion;
- evidence admission.

Required handoff:

```text
memory-mesh candidate
  -> CHRONOS carrier
  -> AgentPlane evidence/replay
  -> Ontogenesis / WebProtégé review
```

### 2. prophet-platform telemetry: SINDy platform dynamics

`SocioProphet/prophet-platform` telemetry can feed SINDy-style sparse-regression system identification. This produces candidate closed-form dynamics for agent throughput, memory load, mesh traffic, RPC convergence, queue pressure, and learning-loop behavior.

Allowed outputs:

- `PlatformDynamicsCandidate`;
- discovered ODE candidate;
- feature library report;
- residual and sparsity metrics;
- stability or side-information report.

Forbidden outputs:

- direct autoscaling policy;
- direct routing policy;
- SRE action without policy admission;
- controller use without AgentPlane replay and policy review.

### 3. JupyterHub / notebook layer: PySR and KAN primitives

The notebook layer should make PySR and KAN-style workflows first-class computational verbs. Notebook output should become a CHRONOS carrier, not an untracked markdown result.

Allowed outputs:

- `NotebookEquationCandidate`;
- LaTeX equation string;
- operator library;
- fit metric;
- complexity metric;
- dataset reference;
- reproducibility metadata.

Forbidden outputs:

- direct WebProtégé mutation;
- ontology assertion without review;
- untracked notebook equation as curriculum truth.

### 4. Ontogenesis / WebProtégé: SRAssertion

`SocioProphet/ontogenesis` should draft the semantic vocabulary for `SRAssertion`. WebProtégé becomes the editor/surface for reviewed assertions, not the first place raw SR output lands.

Proposed object:

```text
SRAssertion
  hasDataset
  hasFeatureSet
  hasEquation
  hasOperatorLibrary
  hasComplexity
  hasFitMetric
  hasUnitsConstraint
  hasDimensionalStatus
  discoveredBy
  discoveredAt
  hasEvidenceReplay
  hasPromotionStatus
```

Forbidden outputs:

- raw equation as OWL axiom;
- SR fit metric as truth;
- notebook result as semantic promotion.

### 5. AgentPlane: SR discovery agents

`SocioProphet/agentplane` should own the evidence/replay surface for SR agents.

Candidate agent types:

- `SRDiscoveryAgent` for PySR / TPSR-style search;
- `SRHypothesisAgent` for LLM-SR-style domain-prior search;
- `SINDyDynamicsAgent` for telemetry and physical-dynamics system identification;
- `ProgramSearchAgent` for FunSearch-style program candidates.

Each agent emits replayable artifacts, not authority.

### 6. Alexandrian / OVAL: Feynman curriculum and Socratic SR

`SocioProphet/alexandrian-academy` should own curriculum/canonization. OVAL-style tutoring should treat SR as a pedagogy engine: student hypothesis, operator choice, dimensional check, complexity discussion, and guided convergence.

Allowed outputs:

- curriculum exercise;
- student hypothesis trace;
- hint policy;
- SR scoring trace;
- admitted educational explanation.

Forbidden outputs:

- model reveals target equation prematurely;
- benchmark answer treated as child-facing truth without pedagogy policy;
- unreviewed generated explanation as canon.

### 7. Quantum / Hamiltonian-learning lane

The quantum lane is longer-run. PySR / KAN / SINDy-like workflows may propose Hamiltonian forms from measurement data. The immediate role is source capture and interface design, not implementation.

Allowed outputs:

- `HamiltonianCandidate`;
- measurement dataset reference;
- operator basis;
- fit metric;
- uncertainty / identifiability report.

Forbidden outputs:

- quantum experiment truth without replay;
- Hamiltonian candidate as canonical physics law;
- runtime control without policy and safety review.

## Required CHRONOS carrier fields

A symbolic-regression carrier should include:

- method family;
- implementation reference;
- dataset URI or telemetry source;
- feature set;
- target variable;
- operator library;
- equation or program candidate;
- constants and units;
- dimensional status;
- fit metric;
- complexity metric;
- baseline comparison;
- replay artifact reference;
- semantic promotion status;
- policy / runtime admission status;
- non-authority declaration.

## Failure modes

The symbolic-regression lane introduces these failure modes:

```text
equation_as_authority
telemetry_model_as_policy
notebook_equation_as_ontology
latent_similarity_as_validation
benchmark_score_as_admission
program_candidate_as_controller
units_check_as_full_validation
```

## Priority order

```text
P0 — SocioSphere SR insertion map and negative fixtures
P1 — Ontogenesis SRAssertion vocabulary draft
P1 — AgentPlane SR evidence/replay schemas
P2 — memory-mesh symbolic-numeric-bridge service contract
P2 — JupyterHub PySR/KAN notebook primitive spec
P2 — prophet-platform telemetry/SINDy lane
P3 — Alexandrian/OVAL Feynman curriculum
P3 — Quantum/Hamiltonian-learning lane
```

## Non-goals

This document does not claim any SR method is correct for all domains.

This document does not promote equations into ontology or policy.

This document does not choose PySR, SINDy, TPSR, SNIP, LLM-SR, KAN, or FunSearch as an exclusive implementation.

This document creates an estate alignment map and identifies follow-on work.
