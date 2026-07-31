# Boundary Calculus Standard

This standard converts the Boundary Calculus Program into a cross-repo governance surface for mathematical, physical, engineering, and security claims.

The governing form is:

```text
local model + explicit interface + claim status + non-claims + validation gate
```

A claim may be useful without being a theorem. A metaphor may organize work without carrying proof authority. A heuristic may guide design without authorizing promotion. This standard exists to keep those distinctions machine-visible.

## Claim status vocabulary

| Status | Meaning | Promotion rule |
|---|---|---|
| `theorem` | proven result with cited theorem/proof dependency | may support downstream load-bearing claims |
| `established` | accepted engineering or scientific practice in the relevant domain | may support operational design within stated limits |
| `heuristic` | plausible design rule not proven in this setting | requires validation gate before operational promotion |
| `conjectural` | speculative or research-stage claim | cannot authorize production action |
| `metaphor` | organizing analogy only | must have `load_bearing: false` |
| `dropped` | prior claim intentionally removed or demoted | retained for provenance only |

## Required claim envelope

Every Boundary Calculus claim ledger entry must identify:

- stable `claim_id`;
- owning repository and source reference;
- domain and chapter anchor;
- local model;
- boundary or interface law;
- claim status;
- whether the claim is load-bearing;
- non-claims;
- evidence references;
- validation gates;
- promotion criteria;
- known limits;
- controller and policy result.

## Promotion discipline

No claim may be promoted by prose alone.

Promotion requires a previous state, target state, named gate, artifact digest or source reference, explicit non-claim preservation, and a controller-visible decision.

The standard is deliberately stricter for `metaphor`, `heuristic`, `conjectural`, and security-decision claims.

## Metaphor rule

A metaphor may be registered, but it must not be load-bearing.

```text
claim_status = metaphor  =>  load_bearing = false
```

Examples:

- `adelic product` as an engineering product of local factors may be a metaphor;
- `adelic theorem proves global engineering control law` is not allowed;
- `Langlands as design grammar` may be informal vocabulary;
- `Langlands theorem transfers to engineered systems` requires an actual theorem or is blocked.

## Security-decision rule

Security and coordinated-compromise claims must not default to escalation.

A security-decision claim must include complete hypothesis space, calibrated or explicitly bounded denominators, dependency model, discriminating evidence, loss matrix, and decision threshold.

Dominant-strategy mitigations are allowed under uncertainty, but attribution and escalation require discriminating evidence.

## Relationship to existing SocioSphere standards

This standard complements the Proof Apparatus Standard. The Proof Apparatus Standard governs mathematical proof programs with substrate, shell, projection, and evidence coordinates. Boundary Calculus adds a broader discipline for multi-domain design claims, interface laws, engineering metaphors, and adversarial decision claims.

SocioSphere owns the canonical standard and promotion/demotion controller. Domain repositories own their local evidence.
