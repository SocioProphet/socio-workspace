# GBRG Causal Inference — Research / Design Track (TRACK 3)

Status: **RESEARCH — NOT IMPLEMENTED. NET-NEW. NOT-YET-REAL.**
Date: 2026-07-31
Author track: GBRG causal research
Scope: a grounded design note for *true* (Pearl-style) causal inference over the
GBRG code graph. This document is a **design study only**. No code in this
document exists, is wired, or is tested. See the Non-Claim Box (§6) — it governs
how any of this may be spoken about.

---

## 0. Why this document exists

GBRG today answers "if this cell changes, what is the blast radius?" as a
governed `ProofArtifact` (`gbrg/crates/gbrg-core/src/scoring.rs`). That is a
useful, honest *structural* answer. It is **not** a causal answer, and GBRG has
begun to accrete language ("blast radius", "what-if", "impact") that *sounds*
causal. This track exists to draw the line precisely: to say what causal
inference would actually be, why we do not have it, what it would take to get a
defensible slice of it, and — bluntly — why most of it is hard-to-impossible on
a real code graph. This is the anti-over-claim track. Its job is to keep GBRG
from ever shipping a slide that says "causal" when it means "recomputed".

### Verified ground truth (do not re-assume)

The estate has **no real causal engine**. Three artifacts get mistaken for one:

| Artifact | What it actually is | What it is NOT |
|---|---|---|
| `causal-proof.ts` (HellGraph) | A distributed-**consistency** proof — establishes a happens-before / causal-order relation over events (Lamport-style causality of *messaging*). | Cause→effect inference. "Causal" here means event ordering, not "X caused Y". |
| `pln.ts` (HellGraph) — **TRACK 1** | A shallow **forward-chainer**: probabilistic truth values propagated along edges. The only real reasoner in the estate. | Causal inference. Propagation of belief along existing edges ≠ estimating the effect of an intervention. |
| GBRG what-if recompute (`gbrg-core/whatif.rs`) — **TRACK 2** | **Recompute-and-diff**: mutate the graph, re-run blast-radius scoring, diff the two `ProofArtifact`s. | A counterfactual. Recomputing a deterministic function under a new input is not the same as `P(Y | do(X))` or `Y_{x}` in a world with unmeasured confounding.

TRACK 3 (this doc) is the entirely net-new thing: a Structural Causal Model
(SCM) over code, with **interventions** and **counterfactuals** in Pearl's
sense. It does not exist.

---

## 1. The gap — why TRACK 1 and TRACK 2 are not causal inference

The whole point of Pearl's framework is the **three-rung ladder**:

1. **Association** — `P(Y | X)`. Seeing. "Cells that change with X also tend to break."
2. **Intervention** — `P(Y | do(X))`. Doing. "If I *force* this change, what breaks?"
3. **Counterfactual** — `P(Y_x | X', Y')`. Imagining. "This test failed after this
   change; *would it still have failed had the change not been made*, holding
   everything else at the values we actually observed?"

Tracks 1 and 2 live entirely on rung 1, dressed up.

### 1.1 TRACK 1 (PLN forward-chaining) is rung-1 propagation

PLN takes edges that already exist and pushes truth values along them. Two fatal
gaps for causality:

- **It reasons over the graph as given.** The edges are `calls`/`imports`/
  `inherits` — *syntactic* dependency, asserted by the parser
  (`gbrg-parser`). PLN never asks whether those edges are the *causal* structure;
  it assumes them and propagates. That is conditioning on the observed graph, i.e.
  rung 1.
- **No `do`-operator.** PLN cannot sever incoming edges to a node and ask what
  happens. Propagating `P(break | depends-on)` is an *observational* conditional.
  It confounds "A depends on B" with "changing A causes B to break" — the
  direction and the confounders are never modelled.

### 1.2 TRACK 2 (what-if recompute) is rung-1 recomputation, not rung-3 counterfactual

The recompute-and-diff pattern *feels* like a counterfactual because it says "in
the world where I made this edit, the score is X'". But:

- **It is a deterministic re-evaluation of a scoring function**, not an estimate
  of an effect under uncertainty. `blast_radius_score` is a fixed formula over
  `dependents_count`, `test_coverage_reach`, `churn_frequency`
  (`scoring.rs`). Re-running it on a mutated graph tells you how the *formula*
  moves, not how the *system* would behave.
- **No confounder adjustment.** A true counterfactual holds background variables
  at their *observed* values and intervenes on one. Recompute-and-diff changes
  the graph and lets *everything downstream of the formula* move — there is no
  notion of "hold the confounders fixed", because there is no causal model that
  distinguishes a confounder from a mediator from a collider.
- **No identification step.** Pearl's machinery is worthless without asking "is
  this effect even *identifiable* from the data I have?" Recompute-and-diff never
  asks; it always returns a number, which is exactly the failure mode GBRG is
  built to avoid (a bare number with no warrant).

**So what would TRACK 3 add?** A causal model (a DAG that is *claimed* to be
causal, with stated assumptions), a `do`-operator that severs incoming structure,
an identification step that can **abstain** when an effect is not identifiable,
and counterfactual estimation that holds observed background fixed. None of that
is in tracks 1 or 2.

---

## 2. The model — code graph → Structural Causal Model (and why it likely breaks)

### 2.1 The tempting mapping

| Causal object | Candidate code-graph counterpart |
|---|---|
| Variable `V_i` | A `SemanticCell` (function/method/module cell), or a per-cell state such as "changed in commit C", "test T covering it passed/failed". |
| Structural equation `V_i := f_i(pa_i, U_i)` | "the behaviour of cell `i` is a function of the cells it depends on (`pa_i`) plus exogenous noise `U_i` (author intent, environment, data)". |
| Causal edge `pa_i → V_i` | A `calls` / `imports` / `inherits` edge — **candidate** structure. |
| `do(V_i = edit)` | Applying a code change to cell `i` — sever `i`'s dependence on its own past and set it to the edited value. |
| Counterfactual `Y_{do(edit)}` | "would test/behaviour `Y` have failed under this change, given everything else we actually observed?" |
| Outcome `Y` | A test result, a CI signal, an incident, a runtime error attributed to a cell. |

### 2.2 The hard assumptions — and why real code violates them

This mapping is seductive and mostly wrong out of the box. Each rung of Pearl's
ladder needs assumptions that code data does not satisfy:

1. **The dependency graph is structural, not (necessarily) causal.**
   `A calls B` is a *syntactic* fact. Causal direction of *failure* can run the
   other way ("B's contract change breaks A") or be bidirectional. The parser
   gives us structure; declaring it causal is an assumption we cannot discharge
   from the parse alone. **Likely violated: pervasively.**

2. **Acyclicity (DAG).** SCM identification (do-calculus) classically needs a
   DAG. Real call graphs have **cycles** (mutual recursion, dependency cycles,
   import cycles). GBRG already stores a general graph, not a DAG. Cyclic SCMs
   exist but the theory is far weaker and identification is largely open.
   **Likely violated: commonly.**

3. **No hidden confounders (causal sufficiency).** The classic confounder in
   code: a *refactor* or a *dependency bump* touches many cells at once and also
   flips a test. The shared cause (the refactor/the author's intent/the upstream
   version) is usually **not a node in the graph**. Co-change is riddled with
   these latent common causes. **Likely violated: almost always.** This is the
   single biggest reason honest causal inference over code is hard.

4. **Stable Unit Treatment Value (SUTVA) / no interference.** Changing cell `i`
   is assumed not to change the "treatment" of cell `j`. In code, a change to a
   shared type or interface simultaneously alters many units — massive
   interference. **Likely violated.**

5. **Positivity / overlap.** To estimate an effect you need to have observed both
   "changed" and "unchanged" instances across the confounder strata. Rare cells,
   or cells that only ever change together, give **no overlap**. **Likely
   violated for the long tail.**

6. **Consistency / well-defined intervention.** `do(edit)` is not one thing — an
   "edit" to a function is an infinite space of possible new behaviours. The
   counterfactual is only as meaningful as the intervention is precisely
   specified. **Likely ill-posed** unless the change is characterised (signature
   change vs body change vs comment).

**Honest conclusion of §2:** a *generic* SCM over the whole code graph is not
identifiable and its assumptions are violated in ways we cannot fix by being
clever. Any defensible TRACK 3 must (a) shrink the ambition to sub-problems where
the assumptions are *plausible*, (b) carry the assumptions as first-class,
stated, falsifiable objects in the `ProofArtifact`, and (c) **abstain loudly**
when identification fails, rather than emit a number.

---

## 3. Candidate approaches + LICENSE gate (MIT / Apache only)

The estate build constraint is **MIT/Apache-permissive only** — check the
license *before* wiring. Below are the real, maintained causal libraries and
their **verified** licenses. Copyleft (GPL/AGPL) options are listed explicitly so
the gate has teeth, not omitted.

### 3.1 License verdict table (web-verified 2026-07-31)

| Library | Role | License (verified) | Verdict | Source |
|---|---|---|---|---|
| **DoWhy** (`py-why/dowhy`) | End-to-end causal API: model → identify → estimate → refute. The identification + refutation step is exactly the "can I even claim this?" gate we want. | **MIT** | ✅ PASS | github.com/py-why/dowhy (LICENSE = MIT) |
| **Ananke** (`gitlab causal/ananke`) | Graphical causal inference incl. ADMGs with *latent* confounders (ID algorithm, one-line-ID). Directly targets the hidden-confounder problem from §2.3. | **Apache-2.0** | ✅ PASS | gitlab.com/causal/ananke (LICENSE = Apache-2.0) |
| **pgmpy** (`pgmpy/pgmpy`) | Bayesian networks / PGMs, structure learning, inference. Substrate for a DAG + CPDs. | **MIT** | ✅ PASS | github.com/pgmpy/pgmpy/blob/dev/LICENSE |
| **causal-learn** (`py-why/causal-learn`) | Causal **discovery** (PC, GES, FCI, LiNGAM, etc.) — learns structure from data; needed for Phase A. | **MIT** | ✅ PASS | github.com/py-why/causal-learn/blob/main/LICENSE |
| **EconML** (`py-why/EconML`) | Heterogeneous treatment effects (DML, DR-learner, causal forests) — effect *estimation* for Phase B. | **MIT AND BSD-3-Clause** (both permissive) | ✅ PASS | github.com/py-why/EconML/blob/main/LICENSE |
| **gCastle** (`huawei-noah/trustworthyAI`) | Causal discovery toolchain (gradient-based, NOTEARS-family). Optional Phase-A alternative. | **Apache-2.0** (verify per-release before wiring) | ⚠️ VERIFY-THEN-PASS | Listed as Apache-2.0; re-confirm the pinned release's LICENSE before use. |
| **pcalg** (R) | Reference PC/FCI implementation, widely cited. | **GPL-2.0+** | ❌ FAIL (copyleft) | Do **not** wire. Reference only for algorithm behaviour. |
| **bnlearn** (R) | Bayesian-network structure learning, canonical. | **GPL-2.0+ / GPL-3** | ❌ FAIL (copyleft) | Do **not** wire. Reference only. |
| **Tetrad / py-tetrad** | Deep causal-discovery suite (CMU). | Mixed; core historically **GPL/LGPL** — treat as **FAIL until proven** per pinned release | ❌ FAIL-BY-DEFAULT | Requires per-release license proof before any use; assume copyleft otherwise. |

Notes on the passes:
- **DoWhy + Ananke + causal-learn + EconML are all under the `py-why` / permissive
  umbrella and all pass the MIT/Apache gate.** This is a genuinely lucky
  ecosystem: the strongest tooling (identify → estimate → refute; latent-confounder
  ID; discovery; effect estimation) is permissively licensed.
- **Language boundary is a real cost, not a license problem.** Every green library
  above is **Python**; GBRG's load-bearing core is **Rust** (`gbrg-core`), and its
  agent surface is a **TS MCP** server. TRACK 3 would run as a *separate Python
  analysis service* consumed over a boundary (e.g. the MCP layer or a batch job
  emitting `ProofArtifact` JSON), **not** linked into `gbrg-core`. Do not
  contaminate the Rust core with a Python causal dep.
- **The `⚠️ VERIFY` and `❌ FAIL` rows are the point.** GPL/AGPL causal libraries
  (pcalg, bnlearn, and Tetrad-by-default) must never be wired into the estate.
  They may be *read* for algorithm understanding, never vendored or imported.

---

## 4. What is honestly achievable vs research-grade — phased plan

Each phase is labelled with a **confidence** and is **NOT-YET-REAL** until it
passes a real test on real repo history. Confidence describes *how likely the
approach is to yield a defensible result*, not how likely we are to build it.

### Phase A — Causal **discovery** over the churn / co-change graph
**Confidence: MEDIUM. NOT-YET-REAL.**

- **Idea:** Do not assume the parser's `calls` edges are causal. Instead *learn*
  candidate causal structure from **version-control history**: co-change,
  churn, and "change in cell `i` at commit C → test `T` flips at C or C+k".
  Feed this to a discovery algorithm (PC / FCI via `causal-learn`; FCI because it
  tolerates latent confounders and returns a PAG, not a false-confidence DAG).
- **Why it might work:** History gives repeated observations; FCI's output
  *explicitly marks* where a latent confounder is possible instead of pretending
  none exist. That honesty aligns with GBRG's ethos.
- **Why it is only MEDIUM:** co-change is dominated by the §2.3 shared-cause
  confounder (one refactor moves 40 files). Discovery will often return "cannot
  orient / latent common cause" — which is the *correct* answer but a weak
  product. Output must be a **PAG with abstention**, never a clean DAG.
- **Real-test gate:** on a repo with known refactors, does FCI *refuse* to assert
  a direct causal edge where we know a shared refactor was the true cause? If it
  confidently asserts a spurious edge, Phase A fails.

### Phase B — Intervention **effect estimates** on blast radius
**Confidence: LOW–MEDIUM. NOT-YET-REAL.**

- **Idea:** Given a (claimed) causal structure, estimate `P(test-breaks | do(change cell i))`
  using DoWhy's identify→estimate→refute loop, or EconML for heterogeneous effects
  ("this change is high-risk *for cells with low test reach*").
- **Why it is LOW–MEDIUM:** identification will frequently **fail** (no
  back-door/front-door admissible set because the confounders are latent, §2.3).
  DoWhy's *refutation* tests (placebo treatment, random common cause, subset
  refuter) are the load-bearing part here — an estimate that fails refutation must
  be **discarded**, not shipped. The value of Phase B is as much "we can prove we
  *cannot* claim this effect" as "here is the effect".
- **Real-test gate:** every emitted effect must survive ≥2 DoWhy refuters; every
  non-identifiable effect must abstain. A Phase-B `ProofArtifact` that carries an
  effect *without* a passed refutation is a bug.

### Phase C — Counterfactual "would this change have caused the failure?"
**Confidence: LOW / RESEARCH-GRADE. NOT-YET-REAL.**

- **Idea:** The headline ask — an incident happened after change `X`; estimate
  whether it *would still have happened* absent `X`, holding observed background
  fixed. This is rung 3 and needs a *fully specified* SCM with functional forms
  and exogenous-noise abduction (Pearl's abduction-action-prediction).
- **Why it is RESEARCH-GRADE:** requires (a) a trusted causal DAG (Phase A is
  only a PAG), (b) estimated structural equations, (c) the intervention precisely
  characterised (§2.6). All three are shaky on code. This is a research bet, not a
  roadmap item.
- **Real-test gate:** back-testing against *known* root-cause post-mortems — does
  the counterfactual agree with the human root-cause verdict at a rate beating a
  co-change baseline? Until that back-test exists and passes, Phase C is a
  hypothesis, full stop.

### Sequencing / dependency

```
Phase A (discovery, PAG+abstain)  ──►  Phase B (effect + refutation)  ──►  Phase C (counterfactual)
   MEDIUM                                 LOW–MEDIUM                          LOW / research
   ↑ prerequisite for everything          ↑ needs a defensible structure     ↑ needs a trusted SCM
```

Do **not** start B before A yields structure that survives its abstention test;
do **not** start C at all until B routinely passes refutation. Skipping forward
is precisely how a track like this turns into over-claim.

---

## 5. How a causal result would stay GBRG-native (if it ever became real)

So that TRACK 3, *if built*, cannot regress into a bare number:

- **Assumptions are first-class.** A causal `ProofArtifact` must carry: the
  claimed DAG/PAG, the identification result (identified / **not identifiable /
  abstained**), the estimator, and the **refutation outcomes**. No assumption →
  no artifact.
- **Abstention is a valid, expected verdict.** The most common honest output on
  real code is "not identifiable — latent confounder". That must render as a clean
  abstain, never a fallback number.
- **Causal claims carry a distinct `epistemicLevel`** and must never silently
  overwrite the structural blast-radius artifact. A causal artifact *annotates*;
  it does not replace `scoring.rs` output.
- **Rust core stays causal-free.** The Python causal service is consumed over a
  boundary; `gbrg-core` never gains a causal dependency.

---

## 6. NON-CLAIM BOX (governing statement — read this)

> **Nothing in this document is implemented.** There is no causal engine in
> GBRG, no SCM over the code graph, no `do`-operator, no counterfactual
> estimator, and no code corresponding to Phases A, B, or C. This is a design
> study.
>
> GBRG's only real reasoners today are the structural blast-radius scorer
> (`gbrg-core/scoring.rs`), the PLN forward-chainer (TRACK 1, *propagation, not
> causation*), and what-if recompute-and-diff (TRACK 2, *recomputation, not
> counterfactual*). **None of these is causal inference.**
>
> GBRG must **never** present TRACK-3 capabilities — causal discovery,
> intervention effects, or counterfactual "would-have-caused" claims — as
> working, in any UI, artifact, slide, demo, or API response, **until each
> specific capability passes a real test on real data** (the per-phase real-test
> gates in §4) and that test is reproducible in CI. Until then the only honest
> statement is: *"causal inference over the code graph is a research direction,
> not a feature."*
>
> If a downstream artifact ever emits a causal claim without a passed
> identification + refutation record, that is a **defect**, not a feature.

---

## Appendix — sources (license verification, 2026-07-31)

- DoWhy — MIT: <https://github.com/py-why/dowhy>
- Ananke — Apache-2.0: <https://gitlab.com/causal/ananke>
- pgmpy — MIT: <https://github.com/pgmpy/pgmpy/blob/dev/LICENSE>
- causal-learn — MIT: <https://github.com/py-why/causal-learn/blob/main/LICENSE>
- EconML — MIT AND BSD-3-Clause: <https://github.com/py-why/EconML/blob/main/LICENSE>
- pcalg (R) — GPL (copyleft, FAIL): CRAN package `pcalg` DESCRIPTION.
- bnlearn (R) — GPL (copyleft, FAIL): CRAN package `bnlearn` DESCRIPTION.
- Tetrad — treat as copyleft/FAIL until the pinned release's LICENSE is proven permissive.

Pearl, J. — *Causality* (2009) and *The Book of Why* (2018) for the ladder,
do-calculus, and abduction-action-prediction referenced throughout.
