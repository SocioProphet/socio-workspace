# Detector migration: V1 shipped → V2 aspirational

Ruleset `1.4.0` introduced the union shape: shipped V1 detectors and proposed
V2 detectors sit in one document, tagged by `maturity`, with a `succeeded_by`
ladder naming which V2 will eventually replace which V1. This file makes the
ladder browsable and the delta between "what we ship" and "what we aim at"
concrete.

## Why both, not either

An earlier framing considered promoting V1 to canonical (V2 has no runtime) or
holding V1 back (V2 has richer signals). Neither is right in isolation:

- V2 alone is a **contract without a runtime**. Its 14 counter-tests have zero
  runners and its 20+ repair actions have zero implementations. Every clause
  beyond the id column is design-only — the exact "declared but never enforced"
  failure the epistemic-kernel work removes elsewhere.
- V1 alone is a **runtime without ambition**. It ships, it is honest about
  being surface heuristics, and the MLN reasoner already handles its noise
  correctly — but it does not tell anyone where the system is heading.

The union keeps both, distinguishes them explicitly, and lets the CTEST gate
(`Noetica/agent-machine/lib/reasoner.ts`) enforce the shipped surface while the
proposed surface remains a receipt of design intent.

## The ladder

Shipped V1 → proposed V2 successor (from `succeeded_by`):

| Shipped V1 | Succeeds into V2 | Delta the V2 will earn |
| --- | --- | --- |
| `LOGFALL.STRAWMAN.V1` | `LOGFALL.STRAWMAN.V2` | NLI contradiction/neutrality, quantifier-flip detection over regex cues |
| `LOGFALL.ADHOMINEM.V1` | `LOGFALL.ADHOM.V2` | Structural person-targeting predicate + proposition-absent check |
| `LOGFALL.APPEALEMOTION.V1` | `LOGFALL.EMOTION.V2` | Domain-thresholded evidence-scarcity index, not lexicon-only |
| `LOGFALL.FALSECAUSE.V1` | `LOGFALL.FALSECAUSE.V2` | Missing-confounder handling + counterfactual warrant check |
| `COGBIAS.ANCHOR.V1` | `COGBIAS.ANCHORING.V2` | Estimate-elasticity to counter-anchor, not salience heuristic |

Shipped V1 with no V2 successor declared (own space, not up for replacement):

`LOGFALL.APPEALAUTHORITY.V1`, `LOGFALL.BANDWAGON.V1`, `LOGFALL.CIRCULAR.V1`,
`LOGFALL.FALSEDICHOTOMY.V1`, `LOGFALL.HASTYGEN.V1`, `LOGFALL.SLIPPERYSLOPE.V1`,
`LOGFALL.SUNKCOST.V1`, `LOGFALL.TUQUOQUE.V1`, `COGBIAS.ABSOLUTECERTAINTY.V1`,
`COGBIAS.AVAILABILITY.V1`, `COGBIAS.CONFIRM.V1` (shipped AND matches the V1 id
declared in `detectors:` — the one detector where spec and code agree today).

Proposed V2/V1 detectors with no shipped counterpart yet:

`LOGFALL.GISH.V1`, `LOGFALL.SHARPSHOOT.V2`, `LOGFALL.LOADED.V1`,
`LOGFALL.BURDEN.V1`, `LOGFALL.EQUIV.V1`, `LOGFALL.MOTTEBAILEY.V1`,
`COGBIAS.OVERCONF.V1`, `COGBIAS.REACTDEV.V1`, all four `TECHCLAIM.*.V1`.

## Counter-test availability

Six CTESTs are `runnable` today (Noetica `reasoner.ts` `CTEST_ROUTING`):
`TERMS.LOCK.V1`, `ACYCLIC.PROOF.V1`, `CHAIN.PROB.V1`, `EVIDENCE-LR.V1`,
`CAUSAL.DO/COUNTERFACTUAL.V1`, `PRESUP.EXPOSE.V1`.

Ten CTESTs are `proposed`: `STEELMAN.CONFIRM.V2`, `REFOCUS.PROPOSITION.V1`,
`BASELINE.DATA.V1`, `PREREG/MTP.V2`, `BURDEN.REASSIGN.V1`,
`CRITERIA.PRE-REGISTER.V1`, `COUNTER-ANCHOR.V1`, `DEVIL-S.LIST.V1`,
`CALIBRATION-20Q.V1`, `ATTRIBUTION-BLIND.A/B.V1`.

Under the CTEST gate that lives in `reason()`, a shipped detector whose only
required counter-test is `proposed` will correctly downgrade `warn`/`block` to
`info` with `downgradedFrom` set — the missing runner is visible in the
verdict, not silently absent. That is the mechanism that turns this migration
plan into a working system today rather than a promise.

## Order of operations (proposed)

1. **Wire the six runnable CTESTs to the shipped V1 detectors that name them**
   (already done in this ruleset's `required_counter_tests`). The gate stops
   downgrading detections whose counter-tests genuinely exist.
2. **Build runners for the ten proposed CTESTs, cheapest first.**
   `REFOCUS.PROPOSITION.V1` and `BASELINE.DATA.V1` are structural and likely
   the shortest path to closing more downgrades.
3. **Author V2 detectors** by successor pair — when `LOGFALL.STRAWMAN.V2`
   ships, flip its `maturity` to `shipped` and add a `succeeds` pointer back to
   V1 so the ladder is bidirectional and V1 becomes a candidate for retirement.
4. **Retire a V1 detector only** when its V2 successor has shipped, its
   counter-tests are `runnable`, and the reasoner has run both in parallel long
   enough to show V2 is not strictly weaker. Retirement means removing the V1
   detector from `debate-detectors.ts` and marking its entry `maturity: retired`
   in the ruleset — never simply deleting it, because auditors need to know
   what changed.

The point of the ladder is that at every step the ruleset reports the truth:
what ships, what does not, what the next runnable move is.
