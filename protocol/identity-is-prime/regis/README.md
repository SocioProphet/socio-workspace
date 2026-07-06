# Regis Entity Graph — Protocol Contracts (v1)

Graph-object schemas for the Regis Entity Graph, the materialized graph surface defined in
[`docs/architecture/identity-is-prime-regis-acr-sociosphere.md`](../../../docs/architecture/identity-is-prime-regis-acr-sociosphere.md).
These back conformance lane **`regis-graph-contracts`** and follow-on item #3 (promote graph objects to
schema-backed JSON validation).

Regis consumes Identity Is Prime (Event-IR, prime-topics, policy polytopes, congruence lanes, proof
artifacts) and HELL-ER (prime atoms, contradiction objects, release packs) as graph semantics. The graph
is a **materialized view rebuildable from the append-only decision ledger** — nothing mutates canonical
state except through a `DecisionLedgerEntry` authorized by a `ResolutionDecision`.

## Schemas

| File | Object | Role |
|---|---|---|
| `canonical-entity.v1.schema.json` | `CanonicalEntity` | Clustered identity; carries identity_state, prime mixture, scope flags, member records, ledger refs |
| `source-record.v1.schema.json` | `SourceRecord` | Immutable observed record projected from Event-IR; holds NER/EL mentions + extracted assertions |
| `edge-witness.v1.schema.json` | `EdgeWitness` | The justifying evidence for an edge — feature contributions, congruence lane, policy verdict, confidence/uncertainty. No edge without a witness. |
| `resolution-decision.v1.schema.json` | `ResolutionDecision` | Required externalized output of every material resolution op: decision + explanation + policy verdict + witness chain + confidence/uncertainty + reversibility + proof ref |
| `decision-ledger-entry.v1.schema.json` | `DecisionLedgerEntry` | Append-only, hash-chained; merge and unmerge are first-class, replayable entries |

## Fixtures

- `fixtures/edge_witness.merge_person.valid.json` — additive evidence + congruence lane for a CITIZEN_FOG person link.
- `fixtures/resolution_decision.merge_person.valid.json` — explainable, policy-vetoed, reversible merge that cites the witness above.

## Design invariants

- **Explainable, not just probabilistic.** Every `ResolutionDecision` carries `explanation.top_features` and a `witness_chain`.
- **Policy veto is structural.** `policy_verdict` can `veto` a merge regardless of score (forbidden prime-topic mixtures).
- **Uncertainty is mandatory.** `confidence.uncertainty` is required; abstention (`abstained`) is auditable.
- **Reversible by construction.** `reversibility.action_class` + the decision ledger make merge/unmerge symmetric.
- **Determinism pins.** `resolver_version` + `policy_version` (and fixture/input/result hashes) on every record, per the architecture's determinism requirements.

## Validate

```bash
python3 - <<'PY'
import json,glob
from jsonschema import Draft202012Validator
for s in glob.glob("schemas/*.json"):
    Draft202012Validator.check_schema(json.load(open(s)))
PY
```
