# Sociosphere Documentation

## Start here
- [Quickstart](quickstart.md)
- [Repo map](repo-map.md)
- [Commands (paste-safe rules)](commands.md)

## Architecture
- [Agentic workbench protocol v0](../protocol/agentic-workbench/v0/README.md)
- [EMVI operator shell architecture](architecture/emvi/README.md)
- [EMVI proof slice protocol v0](../protocol/emvi-proof-slice/v0/README.md)
- [Proof apparatus workspace protocol v0](../protocol/proof-apparatus-workspace/v0/README.md)
- [Proof apparatus workspace controller](architecture/proof-apparatus-workspace-controller.md)
- [UI workbench app README](../apps/ui-workbench/README.md)
- [Overview](architecture/overview.md)
- [Governed DevSecOps as the first hypergraph use case](architecture/governed-devsecops-first-usecase.md)
- [Authority dependency graph](architecture/authority-dependency-graph.md)
- [Sovereign civic computation estate alignment](architecture/sovereign-civic-computation-alignment.md)
- [Estate control graph](architecture/estate-control-graph.md)
- [Runtime, content, and orchestration placement](architecture/runtime-content-placement.md)
- [Upstream bindings — edge capabilities](architecture/upstream-bindings-edge-capabilities.md)
- [Validation contract](architecture/validation-contract.md)
- [Standards: adaptation v1](architecture/standards-adaptation.md)
- [UI workbench](architecture/ui-workbench.md)

## Runbooks
- [CI](runbooks/ci.md)
- [Makefile debugging](runbooks/makefile-debugging.md)
- [UI debugging](runbooks/ui-debugging.md)

## Standards
- [QES (Quality Evidence Standard)](../standards/qes/README.md)
- [Angel of the Lord Hardening Regime](../standards/angel-of-the-lord/README.md)
- [Source Exposure Governance Standard](../standards/source-exposure/README.md)
- [Proof Apparatus Standard](../standards/proof-apparatus/README.md)
- [Adaptation README](standards/adaptation/README.md)

## Governance
- [Glossary](GLOSSARY.md) — controlled vocabulary for all workspace concepts
- [Topology](TOPOLOGY.md) — repo roles, dependency directionality, submodule update playbook
- [Naming & versioning policy](NAMING_VERSIONING.md) — repo naming, SemVer, pin-bump rules
- [Workspace / OS / agent boundary](WORKSPACE_OS_AGENT_BOUNDARY.md) — explicit split between product doctrine and cross-repo orchestration doctrine

## Ecosystem intelligence
- [Ecosystem index](ecosystem/README.md) — per-repo analysis (purpose, vocabulary, topics, dependency graph, change impact rules) for all 8 core SocioProphet repos

## Upstream tracking
- [Upstream bindings — edge capabilities](architecture/upstream-bindings-edge-capabilities.md) — narrative binding/disposition doc for current edge-capability donor/dependency repos
- `registry/upstream-bindings-edge-capabilities.yaml` — machine-readable upstream baseline map for tracked edge-capability repos
- `tools/check_upstream_edge_capabilities.py` — drift check script for the recorded upstream baselines

## Canonical-document policy
- **Current workspace behavior**: `../README.md`, `architecture/overview.md`, `SCOPE_PURPOSE_STATUS_BACKLOG.md`
- **Current proof workspace behavior**: `../manifest/proof-workspace.toml`, `../protocol/proof-apparatus-workspace/v0/README.md`, `architecture/proof-apparatus-workspace-controller.md`
- **Current governed DevSecOps use case**: `architecture/governed-devsecops-first-usecase.md`
- **Current authority-dependency graph**: `architecture/authority-dependency-graph.md`
- **Current integration facts**: `INTEGRATION_STATUS.md`
- **Archival history only**: `ECOSYSTEM-BRIEF.md`

When two docs disagree, prefer canonical current-state docs over archival summaries.
