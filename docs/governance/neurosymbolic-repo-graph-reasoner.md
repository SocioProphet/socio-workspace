# Neurosymbolic repository graph reasoner

## Purpose

The repository graph reasoner turns repository RDF graphs into governed evidence, inference, policy, action, and audit records. It must follow the existing `watson-cyc-semantic-web-chronos-v1` corpus-loop model rather than a standalone OWL-only reasoner model.

This design treats repository graphs as temporal governed state/event graphs. RDF and OWL are representation layers; SHACL is a promotion gate; external RDF engines may be adapters. The control model is neurosymbolic: Chronos-style transition reasoning, Watson/Cyc-style ontology and rule semantics, evidence qualification, policy admissibility, bounded runtime action, and ledgered audit.

## Existing pinned substrate

The governing corpus loop is `registry/corpus-loop-v1/valid.watson-cyc-chronos.pinned.json`.

It defines five required planes:

1. Evidence plane: `SocioProphet/sherlock-search`
   - artifact family: `source-quality-answer-trace.v0`
   - role: source attribution, evidence quality, and answer trace support.

2. Ontology plane: `SocioProphet/ontogenesis`
   - artifacts: `Platform/corpus-event-semantics.ttl`, `shapes/corpus-event-semantics.shacl.ttl`, and `scripts/validate_corpus_event_semantics.py`
   - role: event, evidence, provenance, causal candidate, semantic table, and diagnostic finding semantics.

3. Policy plane: `SocioProphet/policy-fabric`
   - artifact family: `governed-action-policy-decision.v0`
   - role: admissibility decision before any recommended governance action.

4. Runtime plane: `SocioProphet/agentplane`
   - artifact family: `bounded-action-loop.v0`
   - role: scoped action execution with boundary, risk, stop condition, and artifact capture.

5. Ledger plane: `SocioProphet/model-governance-ledger`
   - artifact family: `governance-audit-record.v0`
   - role: audit record for inference, decision, action, and evidence linkage.

## Repository graph inputs

The initial graph inputs are the active-spine governance surfaces already protected in `make validate`:

- `registry/spine-v0.txt`
- `manifest/active-spine.repos.toml`
- `governance/CANONICAL_SOURCES.yaml`
- `catalog/boundaries.yaml`
- `docs/TOPOLOGY.md`
- `reports/corpus-loop-v1-resolution-report.json`

These are lifted into RDF repository graph facts such as:

- repository identity
- canonical source ownership
- boundary class
- manifest/overlay membership
- topology role
- validation target coverage
- pinned corpus-loop component
- issue and pull-request state
- promotion candidate state
- stale or missing artifact state

## Inference model

### Chronos-style transition reasoning

Chronos-style reasoning governs state over time. It should infer:

- a repository moved from candidate to canonical only if registry, manifest, canonical-source, topology, and boundary surfaces agree;
- a pinned artifact is stale when the repo has advanced past the pinned commit and no freshness waiver is recorded;
- a promotion candidate is blocked when a required boundary, policy, fixture, or ledger artifact is missing;
- an issue is actionable only when its dependent evidence and policy decision are present;
- a validation failure is a state transition, not merely a static error.

### Watson/Cyc-style semantic reasoning

Watson/Cyc-style reasoning governs concepts, roles, rules, and commonsense constraints. It should infer:

- `sociosphere` owns coordination but not downstream implementation;
- standards repos define normative contracts and should not depend on runtime implementations;
- runtime/product repos may depend on standards, but standards should remain independently consumable;
- SHACL-conformant evidence is eligible for promotion review but is not automatically admissible for action;
- low-confidence causal candidates can produce diagnostic findings but not execution actions;
- every action recommendation requires evidence, policy admissibility, runtime scope, and ledger capture.

### SHACL as promotion gate

SHACL validates shape conformance for RDF graph artifacts. It is necessary but insufficient. A SHACL-pass result means a graph can enter the policy and reasoning loop; it does not itself authorize governance action.

## Governed action loop

The reasoner output must be expressed as a bounded governance action candidate:

1. Evidence qualification from `sherlock-search` source-quality traces.
2. Ontology classification from `ontogenesis` corpus event semantics.
3. Temporal/state inference from the Chronos transition layer.
4. Rule/semantic inference from the Watson/Cyc layer.
5. Policy admissibility through `policy-fabric` governed action decisions.
6. Runtime scoping through `agentplane` bounded action loops.
7. Audit capture through `model-governance-ledger` governance audit records.

No generated action should bypass the policy, bounded runtime, or ledger planes.

## Initial fixture requirements

The first fixture set should include:

- one valid active-spine graph where all governance surfaces agree;
- one invalid graph where a repo appears in `registry/spine-v0.txt` but lacks boundary coverage;
- one invalid graph where a repo is a promotion candidate but lacks required policy/runtime/ledger evidence;
- one non-actionable graph where SHACL passes but policy admissibility fails;
- one stale-pin graph where the Chronos transition layer emits a diagnostic finding rather than an automatic action.

## Explicit non-goals

- Do not implement this as generic Pellet-only reasoning.
- Do not treat OWL class inference as sufficient for governance action.
- Do not bypass the existing `watson-cyc-semantic-web-chronos-v1` corpus loop.
- Do not let an RDF engine directly create repo changes without policy-fabric, agentplane, and ledger mediation.
