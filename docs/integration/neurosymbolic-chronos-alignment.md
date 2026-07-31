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

## Candidate row — KAIROS event-schema induction (DRAFT, pending doctrine-owner review)

**Status: DRAFT candidate row. Not yet admitted to the table above.**

This document's own rule is that a new method's carrier is a candidate until the owning-plane review admits it. That rule applies to this row itself: it is proposed here for doctrine-owner review, not presented as decided. Do not treat it as an addition to the admitted "Method families and CHRONOS roles" table above until an owning-plane reviewer accepts it (at which point it should be merged into that table and this section removed).

Grounding: `KAIROS` is not defined anywhere else in this estate's doctrine; it surfaces only as an unexplained paired label in an external deck slide ("KAIROS / CHRONOS Lessons"). The most likely real-world referent is DARPA's KAIROS program — "Knowledge-directed Artificial Intelligence Reasoning Over Schemas," run by DARPA's Information Processing Techniques Office, now complete and reference-only. KAIROS defines a *schema* as an organized unit of knowledge representing a pattern of memory used in human cognition, and targets *complex events*: multi-step sequences with participants, temporal sequencing, and causal chains. Its approach is two-stage: (1) schema induction — learn schemas automatically from large corpora rather than hand-crafting them, by detecting, classifying, and clustering sub-events; (2) schema application — apply the learned schemas to new multilingual/multimedia input to detect, link, and extract complex events and their relationships. This grounding is taken from DARPA's own program page, not guessed from the deck.

Proposed row (to be inserted into "Method families and CHRONOS roles" above, upon admission):

| Method family | CHRONOS role | Admissible use | Forbidden use |
|---|---|---|---|
| KAIROS-style complex event schema induction (DRAFT — not yet admitted) | candidate multi-step event-schema proposal | propose induced complex-event schemas (participants, subsidiary sub-events, temporal/causal structure) as candidate carriers with source-corpus provenance and induction confidence, for owning-plane review | promote an induced event schema, or any instance matched against it, to canonical ontology, evidence record, or policy trigger without owning-plane review; treat schema-match confidence as ground-truth event occurrence, causal proof, or evidentiary anchoring |

This follows the same discipline as the existing rows (e.g. dILP's "propose learned rules ... / promote learned rules to canonical schema or ontology without owning-plane review"): schema induction proposes structure, it does not settle it. The forbidden-use column has two independent failure modes worth calling out explicitly, both barred:

1. **Unreviewed promotion** — treating an induced schema (or a real-world instance matched against it) as if it were already canonical ontology, an evidence record, or a live policy trigger, without owning-plane review. This mirrors dILP's and Deep Ontological Networks' forbidden-promotion pattern.
2. **Confidence-as-truth** — treating the induction/match confidence score as ground-truth evidence that the event occurred, or as a causal claim, rather than as an advisory ranking over candidate structure. This mirrors LTN's and LNN's forbidden pattern of not treating a soft/bounded score as truth.

A negative fixture for failure mode (1) is added at `registry/corpus-loop-v0/invalid.kairos-schema-promoted-as-canonical-ontology.json` and wired into `tools/check_neurosymbolic_chronos.py`.

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
