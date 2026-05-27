# Neuro-Symbolic CHRONOS Alignment

Status: v0.1 doctrine capture.

This document captures how the ASU neuro-symbolic reasoning materials and the Maria Chang / IBM neuro-symbolic research thread relate to the CHRONOS Evidence Loop already tracked in SocioSphere.

It is intentionally an integration document. It does not vendor third-party course materials, copy slide content, promote new schemas, or move authority into SocioSphere.

## Position

CHRONOS is the estate's governed neuro-symbolic evidence loop.

It turns corpus evidence, model outputs, extracted claims, symbolic parses, temporal facts, ontology deltas, learned rules, and proposed policies into governed carrier objects that preserve provenance, claim status, validation state, replay shape, and explicit non-authority boundaries.

CHRONOS is not a model family. It is the lifecycle discipline around neuro-symbolic work:

```text
source corpus / observation
  -> evidence anchor
  -> normalized claim
  -> candidate governed carrier
  -> explanation trace
  -> verification result
  -> governance decision
  -> receipt / rejection
  -> learning update
```

The ASU neuro-symbolic materials give us a method map. CHRONOS gives us the admissibility loop.

## Relationship to existing SocioSphere corpus loop

The existing corpus-loop / CHRONOS lane remains the controlling integration path:

```text
Governed Intelligence Rollout
  -> CHRONOS Evidence Loop
    -> corpus-loop v0 / v1 / v1.1
```

The neuro-symbolic integration extends this lane by naming which reasoning or learning method produced a proposed carrier and by making the authority boundary explicit.

A carrier produced by a neuro-symbolic method is never automatically canonical. It is a candidate until the owning authority plane admits it.

## Method families and CHRONOS roles

| Method family | CHRONOS role | Admissible use | Forbidden use |
|---|---|---|---|
| Logic Review / formal logic substrate | vocabulary foundation | define atoms, rules, grounding, consistency, entailment, annotated truth, fixpoint closure, and fuzzy operators | imply that every carrier has theorem-grade entailment |
| Kautz / NSR taxonomy | classification lens | label a capability as neural-to-symbolic, symbolic-to-neural, hybrid, rule-guided, embedded-symbolic, or System-1/System-2 | treat taxonomy labels as maturity or authority grades |
| LTN-style differentiable fuzzy logic | soft constraint / satisfaction scoring | report semantic satisfaction, fuzzy query value, or differentiable constraint pressure | treat fuzzy truth value as evidence, policy admission, or schema authority |
| LNN-style truth-bound propagation | advisory bound/inconsistency analysis | report lower/upper truth bounds, formula-local inconsistency, and interpretable formula structure | claim global consistency, arbitrary entailment correctness, or learned rule structure |
| NeurASP-style neural-to-ASP interface | symbolic adjudication over neural observations | let neural outputs propose atoms and let ASP constraints adjudicate candidate worlds | bypass policy admission, provenance, or execution authority because ASP returned a stable model |
| SATNet-style differentiable constraint learning | failure-mode reference and cautious candidate constraint learning | study differentiable constraint layers with anti-leakage and transduction tests | accept apparent symbol grounding without leakage checks and held-out grounding validation |
| dILP-style differentiable rule learning | candidate rule proposal | propose learned rules with provenance, template constraints, and validation state | promote learned rules to canonical schema or ontology without owning-plane review |
| Deep Ontological Networks / RRN | candidate ontology inference | propose inferred relations or ontology-delta candidates | treat embeddings as ontology authority or explanation-complete reasoning |
| DSR / DSP | symbolic expression or policy proposal | propose compact symbolic policies for routing, control, or remediation scoring | run a symbolic policy as a live controller before governance admission |

## Neuro-symbolic carrier boundary

A CHRONOS carrier that references neuro-symbolic reasoning must include at least:

- source evidence reference;
- method family;
- method output type;
- grounding status;
- validation status;
- explanation trace reference;
- owning authority plane;
- non-authority declaration;
- replay reference;
- governance decision or pending decision.

## Maria Chang / IBM thread alignment

The Maria Chang / IBM neuro-symbolic research thread is relevant because it sits in the exact product gap CHRONOS addresses: natural-language and corpus evidence must be converted into symbolic structures that can be queried, reasoned over, validated, governed, and replayed.

In our estate vocabulary:

```text
natural-language corpus / temporal QA evidence
  -> neural or hybrid extraction
  -> entity / relation / temporal normalization
  -> symbolic carrier candidate
  -> explanation / verification
  -> governance admission
  -> evidence receipt
```

The IBM-style NSQA / temporal-KBQA path is therefore a CHRONOS use case, not a separate authority plane.

## Authority boundaries

SocioSphere records workspace topology, integration doctrine, rollout manifests, and corpus-loop registration. It does not own canonical schemas, ontology promotion, policy admission, model governance, execution, evidence replay, or runtime substrate.

Authority remains distributed:

| Plane | Owner |
|---|---|
| Corpus-loop integration and workspace registration | `SocioProphet/sociosphere` |
| Evidence/action/replay surface | `SocioProphet/agentplane` |
| Semantic vocabulary draft | `SocioProphet/ontogenesis` |
| Canonical schemas | `SourceOS-Linux/sourceos-spec` |
| Policy admission and cancellation | `SocioProphet/policy-fabric` / guardrail fabric |
| Model governance, consent, personalization, promotion | `SocioProphet/model-governance-ledger` |
| Routing | `SocioProphet/model-router` |
| Visible cognition loop | `SocioProphet/superconscious` |
| Learning/canonization | `SocioProphet/alexandrian-academy` |
| World evidence/source metadata | `SocioProphet/gaia-world-model` |

## Required negative rules

The following are never valid CHRONOS promotions:

1. A fuzzy satisfaction score is promoted as truth.
2. A neural output is promoted as evidence without source anchoring.
3. A learned rule is promoted as canonical schema.
4. A symbolic derivation is treated as policy admission.
5. A carrier without provenance is treated as admissible.
6. An ontology embedding is treated as ontology authority.
7. A symbolic policy is run as a controller without governance admission.
8. Apparent grounding is accepted without leakage and transduction tests.

## Definition of done

This lane is captured when SocioSphere can point to:

- this alignment document;
- a neuro-symbolic capability taxonomy;
- at least one valid ASU-derived CHRONOS carrier fixture;
- negative fixtures for soft-score authority drift, ungrounded-symbol promotion, and label-leakage carrier promotion;
- downstream follow-on work items for Superconscious, Ontogenesis, AgentPlane, Holmes, GAIA, Alexandrian Academy, and Prophet Platform.
