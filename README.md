# sociosphere

Platform meta-workspace controller for the SocioProphet ecosystem.

Sociosphere owns the canonical workspace manifest + lock, runner semantics,
protocol fixtures, deterministic multi-repo materialization, source-exposure
governance, adversarial hardening critique, validation lanes for platform
build and release readiness, and the estate Boundary Atlas for typed repo
jurisdictions and evidence contracts.

## Governance references

- [Repository topology and dependency rules](docs/TOPOLOGY.md) — canonical source for repo roles, directionality, and the submodule update playbook.
- [Naming and versioning policy](docs/NAMING_VERSIONING.md) — single source of truth for repo naming, SemVer discipline, and submodule pin-bump rules.
- [Boundary Atlas v0.1](docs/boundary-atlas-v0.1.md) — typed repo jurisdiction map, claim modes, evidence contracts, sufficiency labels, and boundary maturity.
- [Boundary Coverage Report](docs/boundary-coverage-report.md) — bootstrap report of boundary-governed repo coverage and hardening gaps.
- [Angel of the Lord Hardening Regime](standards/angel-of-the-lord/README.md) — adversarial CI and workspace critique regime for repository, boundary, release, and evidence hardening.
- [Source Exposure Governance Standard](standards/source-exposure/README.md) — publication-safety rules for public source, public release mirrors, inner-source development, and restricted security/operations material.

## Canonical scope

Sociosphere is responsible for:

- Declaring workspace repositories and roles in `manifest/workspace.toml`.
- Pinning exact revisions in `manifest/workspace.lock.json`.
- Materializing and validating the workspace with `tools/runner/runner.py`.
- Enforcing topology and dependency-direction policies via `tools/check_topology.py`.
- Maintaining cross-repo governance and registry metadata in `registry/` + `governance/`.
- Maintaining the Boundary Atlas in `catalog/` + `docs/boundary-atlas-v0.1.md`.
- Owning the Angel of the Lord adversarial hardening regime across workspace CI lanes.
- Validating source-exposure publication safety with `tools/check_source_exposure.py`.

Sociosphere is **not** the place for feature implementation inside downstream
component repositories.

## Canonical entry points

- Documentation index: `docs/README.md`
- Architecture baseline: `docs/architecture/overview.md`
- Upstream bindings (edge capabilities): `docs/architecture/upstream-bindings-edge-capabilities.md`
- Scope/current state/backlog: `docs/SCOPE_PURPOSE_STATUS_BACKLOG.md`
- Integration ledger: `docs/INTEGRATION_STATUS.md`
- Boundary Atlas: `docs/boundary-atlas-v0.1.md`
- Repo jurisdiction model: `docs/repo-jurisdiction-model.md`
- Boundary coverage report: `docs/boundary-coverage-report.md`
- Namespace ownership map: `governance/CANONICAL_SOURCES.yaml`
- Angel of the Lord hardening regime: `standards/angel-of-the-lord/README.md`
- Source exposure standard: `standards/source-exposure/README.md`
- Proof apparatus workspace protocol: `protocol/proof-apparatus-workspace/v0/README.md`
- Proof apparatus standard: `standards/proof-apparatus/README.md`
- Proof workspace manifest: `manifest/proof-workspace.toml`

## Repository intelligence assets

### Boundary catalog layer

| File | Description |
|---|---|
| `catalog/boundaries.yaml` | Estate typed boundary atlas: repo jurisdictions, maturity, claim modes, sufficiency labels, trust roots, and next hardening steps |
| `catalog/claim-modes.yaml` | Claim-mode registry and evidence requirements |
| `catalog/evidence-contracts.yaml` | Evidence contract catalog for proof artifacts, boundary records, governance evidence packets, boot trust, and local state integrity |

### Registry layer

| File | Description |
|---|---|
| `registry/canonical-repos.yaml` | Canonical repo inventory and metadata |
| `registry/repository-ontology.yaml` | Semantic identity, roles, and topic bindings |
| `registry/dependency-graph.yaml` | Dependency edges and impact reasoning |
| `registry/change-propagation-rules.yaml` | Change cascade and notification rules |
| `registry/devops-automation.yaml` | CI/CD automation policies |
| `registry/deduplication-map.yaml` | Duplicate consolidation tracker |
| `registry/upstream-bindings-edge-capabilities.yaml` | Machine-readable upstream baselines, dispositions, and tracked risk notes for edge-capability donor/dependency repos |

### Engine layer

| Module | Description |
|---|---|
| `engines/ontology_engine.py` | Controlled vocabulary and topic extraction |
| `engines/propagation_engine.py` | Cascading update computation |
| `engines/devops_orchestrator.py` | Build/test/deploy orchestration |
| `engines/metrics_collector.py` | Runtime and coverage metrics |

### Standards and policy layer

| File | Description |
|---|---|
| `standards/qes/README.md` | Quality Evidence Standard |
| `standards/angel-of-the-lord/README.md` | Angel of the Lord adversarial hardening regime |
| `standards/source-exposure/README.md` | Source Exposure Governance Standard |
| `standards/source-exposure/policy.v0.json` | Machine-readable source-exposure policy |
| `standards/source-exposure/schemas/source_exposure_report.v1.json` | Source exposure report schema |
| `standards/proof-apparatus/README.md` | Proof apparatus claim, gate, evidence, and promotion standard |
| `standards/proof-apparatus/claim-ledger.schema.json` | Proof apparatus claim ledger event schema |
| `standards/proof-apparatus/proof-adapter.schema.json` | Proof apparatus repository adapter manifest schema |
| `standards/personal-intelligence-cell/social-environment-snapshot.schema.json` | Personal Intelligence Cell social-environment snapshot schema |
| `standards/personal-intelligence-cell/reputation-delta.schema.json` | Personal Intelligence Cell contextual reputation delta schema |

### Personal Intelligence Cell social standards

SocioSphere now owns the governance-level schemas for cell social-environment assessment and anti-manipulation-aware reputation deltas:

- `standards/personal-intelligence-cell/social-environment-snapshot.schema.json`
- `standards/personal-intelligence-cell/social-environment-snapshot.example.json`
- `standards/personal-intelligence-cell/reputation-delta.schema.json`
- `standards/personal-intelligence-cell/reputation-delta.example.json`
- `tools/validate_personal_intelligence_cell_social_environment.py`

Validate locally:

```bash
python3 tools/validate_personal_intelligence_cell_social_environment.py
```

These standards map `prophet-platform` Personal Intelligence Cell outputs into SocioSphere governance concepts: temporal social-environment snapshots, stale ties, emerging communities, attention sinks, coordinated amplification flags, relationship hygiene recommendations, contextual reputation deltas, confidence intervals, and anti-manipulation flags.

### CLI tools

```bash
# Registry and ontology maintenance
python cli/rebuild-registry.py
python cli/analyze-ontology.py [repo-name ...]
python cli/validate-deps.py

# Upstream drift checks
python3 tools/check_upstream_edge_capabilities.py

# Personal Intelligence Cell social standards
python3 tools/validate_personal_intelligence_cell_social_environment.py

# Source exposure publication safety
python3 tools/check_source_exposure.py
make source-exposure-check

# Proof apparatus workspace
cat manifest/proof-workspace.toml
python3 tools/validate_proof_apparatus.py

# Success and dedup reporting
python cli/measure-success.py
python cli/dedup-report.py
```

### Webhook entrypoint

```bash
WEBHOOK_SECRET=<shared-secret> python webhooks/github_handler.py --port 8080
```

## Quickstart (workspace runner)

```bash
python3 tools/runner/runner.py list
python3 tools/runner/runner.py fetch
python3 tools/runner/runner.py lock-verify
python3 tools/runner/runner.py validate-policy
python3 tools/runner/runner.py validate-trust
python3 tools/runner/runner.py trust-report
python3 tools/runner/runner.py run test --all
```

## Local overrides

The runner supports `manifest/overrides.toml` for local development overrides.
The file is optional and should remain gitignored.

A minimal example:

```toml
[[repos]]
name = "agentplane"
local_path = "components/agentplane-local"

[[repos]]
name = "mcp-a2a-zero-trust"
local_path = "components/mcp_a2a_zero_trust_local"
```

At runtime, `runner.py` merges override repo entries by `name` on top of the canonical
workspace manifest. Source fields like `local_path`, `url`, `ref`, and `rev` may be
overridden locally without editing the committed manifest.

## Documentation de-duplication policy

To avoid conflicting documentation:

1. Keep exactly **one canonical source per active topic**.
2. Keep historical branch/PR narratives for provenance, but mark them archival.
3. If docs disagree, canonical current-state docs win over archival summaries.
