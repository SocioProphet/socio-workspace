# Identity Prime — Extraction/Resolution Benchmark Lane

**Status:** v0.1 — extends the `workspace-identity-conformance` lane defined in
[`../architecture/identity-is-prime-regis-acr-sociosphere.md`](../architecture/identity-is-prime-regis-acr-sociosphere.md).
**Purpose:** measure local-only vs. citizen-cloud-assisted NER/EL/ER on the golden fixtures, and prove the
result is **sequence-neutral** (replay-invariant) so cloud assistance never changes the verified outcome,
only its cost/latency.

## 1. Lane id

`identity-prime-extraction-benchmark` (lane #14, additive to the 13 lanes in the architecture doc).

## 2. What it compares

Two execution profiles run over the **same** Event-IR golden inputs:

| Profile | Placement (per the fog-scope task matrix) |
|---|---|
| `local_only` | NER + EL + ER all on `CITIZEN_FOG` (lightweight/dictionary NER, local KB, local ER). No data leaves the device. |
| `cloud_assisted` | `CITIZEN_FOG` does typing/PII-minimization/prime-hinting; `CITIZEN_CLOUD` does statistical NER + SpanCategorizer, KB grounding, heavy ER clustering. |

Both profiles consume `extract.mentions.v1` / `extract.events.v1` and emit `regis.resolution-decision.v1`.

## 3. Metrics (per profile, per fixture family)

- **Quality:** mention F1 (NER), linking accuracy (EL), pairwise ER precision/recall/F1 against the golden
  clustering, abstention rate, policy-veto agreement.
- **Calibration:** mean `confidence.uncertainty` vs. observed error; over/under-confidence.
- **Cost/latency:** wall time + bytes-egressed (must be 0 for `local_only`).
- **Decision agreement:** fraction of `ResolutionDecision.decision` values identical across profiles.

## 4. Sequence-neutrality (the hard gate)

For each fixture, run the input event stream in **N permutations** (and a reversed order). The lane passes
sequence-neutrality only if, for every permutation:

- final `CanonicalEntity` clustering is identical (set-equal member records);
- every `ResolutionDecision.decision` is identical;
- the `DecisionLedgerEntry` chain replays to the same terminal state (hash-equal after canonicalization),
  even though intermediate ledger order may differ.

This operationalizes the Identity Is Prime "sequence neutrality and self-correction" property (FORMAL_SPEC §5).

## 5. Acceptance criteria

1. `cloud_assisted` must **not** change any verified `decision` vs `local_only`; it may only improve
   confidence/uncertainty or reduce abstention. A flipped verified decision is a **failure**, not a win.
2. `local_only` egress bytes == 0.
3. Sequence-neutrality holds for both profiles on all golden fixtures.
4. Policy vetoes are identical across profiles (policy is placement-independent).
5. Every result pins `resolver_version`, `policy_version`, `extractor_version`, `index_version` (if Sherlock
   participates), `fixture_version`, `input_hash`, `result_hash` — per the architecture determinism rules.

## 6. Required fixture families

Reuse the architecture's fixture families plus extraction goldens:
- `extract.mentions` golden (text → expected mentions, incl. overlapping spans).
- `extract.events` golden (mentions → expected events/relations).
- ER clustering golden (records → expected `CanonicalEntity` membership).
- permutation manifests (ordered event-id lists) for sequence-neutrality.

## 7. Output

A benchmark result record wired into the Sociosphere registry/evidence pattern (follow-on #5), carrying the
metrics table, the sequence-neutrality verdict, and the determinism pins. The lane is **measurement, not
promotion**: a model/profile is promoted into the product only after it wins here *and* passes the policy
regression checks (consistent with board discipline — keep all arms, promote only winners).
