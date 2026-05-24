# Repo Graph Reasoner Platform Requirements

Date: 2026-05-24

## Decision

The Sociosphere neurosymbolic repo-graph lane must not grow into a one-off local governance engine. Sociosphere may keep deterministic bootstrap validators, but the durable infrastructure for typed observations, RDF named graphs, rule findings, policy handoff, runtime handoff, and ledger audit must be supplied by Prophet Platform.

Upstream requirement: SocioProphet/prophet-platform#476.

## Local boundary

Sociosphere owns:

- active-spine repo selection;
- local bootstrap validation;
- repo-governance observation fixtures;
- local CI parity checks;
- no-dependency fallback adapters for bootstrap validation;
- Sociosphere-specific governance rule fixtures and expected findings.

Sociosphere does not own:

- the durable observation substrate;
- the general RDF lift service;
- the general rule-evaluation runtime;
- policy authorization semantics;
- bounded action-loop execution semantics;
- governance ledger record semantics.

## Required platform support

Prophet Platform must provide reusable support for:

1. typed repo-governance observations with source path, blob SHA, parser version, extraction method, source span where available, confidence, and temporal validity;
2. RDF named-graph generation with provenance metadata and deterministic digesting;
3. named rule evaluation with rule IDs, versions, antecedents, consequents, blockers, and replayable result packets;
4. policy-fabric handoff where findings become policy-decision requests, not action authorization;
5. bounded runtime/action handoff after policy approval;
6. ledger-ready audit records for findings, denials, approvals, action candidates, and executed actions;
7. bootstrap compatibility so Sociosphere can keep no-dependency CI checks while preferring platform-backed RDF adapters.

## Design guardrail

Evaluator findings are advisory until policy-fabric returns an explicit allow decision. No Sociosphere repo-graph finding may be treated as direct permission to mutate a repository.

## Migration path

Current local files remain valid bootstrap scaffolding:

- `tools/generate_active_spine_repo_graph.py`
- `tools/evaluate_active_spine_repo_graph.py`
- `tools/check_active_spine_repo_graph_evaluator.py`
- `registry/neurosymbolic-repo-graph-reasoner/*`

Next migration step: introduce typed repo-governance observations and a local adapter boundary that can later delegate to Prophet Platform without changing Sociosphere rule fixtures.
