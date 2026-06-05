# Repository Analysis — SocioProphet/sociosphere

**GitHub:** https://github.com/SocioProphet/sociosphere  
**Role in ecosystem:** Workspace controller  
**Last analysed:** 2026-04-08

---

## 1. Repository Purpose & Identity

### What it does
The monorepo workspace controller. It defines a canonical manifest and lock file that pins
all other component repositories to exact revisions, and provides a Python runner to fetch,
build, and test them deterministically.

Sociosphere is also the ecosystem governance graph authority. It does not own every
runtime, UI, policy, storage, or agent schema, but it owns the cross-repo topology view
that lets those schemas be reasoned about as one governed system. When SocioProphet
emits an `Institutional Action`, Sociosphere must be able to locate the relevant actor,
role, authority basis, evidence bundle, procedure template, execution substrate, and
receipt-producing repo boundary.

### Core responsibilities
- Maintain `manifest/workspace.toml` + `manifest/workspace.lock.json` — the single source of
  truth for repo membership, roles, and pinned revisions.
- Orchestrate tasks via `tools/runner/runner.py` (`list`, `fetch`, `run build --all`,
  `run test --all`).
- Provide `protocol/` — shared adapter contracts and fixtures that define compatibility
  language.
- Emit normalized workspace artifacts consumed by agentplane:
  `WorkspaceInventoryArtifact`, `LockVerificationArtifact`, `TaskRunArtifact`,
  `ProtocolCompatibilityArtifact`.
- Manage version pins for third-party dependencies (e.g. TriTRPC in `third_party/`).
- Maintain the ecosystem-level governance graph: repo roles, ownership boundaries,
  authority surfaces, evidence-producing repos, execution substrates, and downstream
  validation obligations.
- Track the governed-action topology required by SocioProphet: `Actor`, `Role`,
  `Authority boundary`, `Policy basis`, `Evidence bundle`, `Procedure template`,
  `ApprovalEvent`, `OverrideEvent`, and `ExecutionReceipt`.
- Surface drift when a repo claims integration without manifest membership, pinned
  revision, protocol fixture, evidence artifact, governance owner, or replay path.
- Provide the source-of-truth repo map for `hellgraph`, `prophet-platform`, AgentOS,
  agentplane, and standards repos to reason about release readiness and institutional
  action safety.

### What systems depend on it
- **agentplane** — explicitly consumes sociosphere bundles
  (see `agentplane/docs/sociosphere-bridge.md`).
- All component repos listed in `manifest/workspace.toml` (prophet_cli,
  sourceos_a2a_mcp_bootstrap, socioprophet-web, dev-api, hdt_app, human_digital_twin,
  ontogenesis) depend on sociosphere for coordinated builds.
- **socioprophet** — depends on Sociosphere for the ecosystem topology needed to bind
  institutional actions to repo ownership, evidence, policy, execution, and replay
  boundaries.
- **hellgraph** — depends on Sociosphere as the authoritative repo/topology source for
  graph queries over governance relationships.
- **prophet-platform** — depends on Sociosphere topology and evidence posture for
  release-readiness and deployment-safety checks.

### What it depends on
- Python 3 (runner)
- Component repos via workspace manifest (local or remote)
- TriTRPC — pinned in `third_party/`, integration tracked in `docs/INTEGRATION_STATUS.md`

### Key files
- `README.md` — quickstart and layout overview
- `manifest/workspace.toml` — canonical workspace manifest
- `manifest/workspace.lock.json` — pinned revision lock
- `tools/runner/runner.py` — Python orchestration entry point
- `protocol/protocol.md` — adapter contract surface
- `docs/SCOPE_PURPOSE_STATUS_BACKLOG.md` — full scope, purpose, and backlog
- `docs/INTEGRATION_STATUS.md` — TriTRPC and third-party pin history
- `docs/TOPOLOGY.md` — canonical repo topology rules
- `docs/Repo_Layout_Workspace_Composition_Spec_v0.1.md` — workspace composition spec
- `docs/ecosystem/` — per-repository intelligence index used by agents, engineers, and
  governance systems as a machine-readable source of truth

---

## 2. Controlled Vocabulary & Ontology

### Key terms
| Term | Definition | Source |
|---|---|---|
| **Workspace manifest** | `workspace.toml` declaring all repos, their roles, and materialization paths | `manifest/workspace.toml` |
| **Workspace lock** | `workspace.lock.json` pinning exact revisions for determinism | `manifest/workspace.lock.json` |
| **Runner** | Python orchestration tool at `tools/runner/runner.py` | `README.md` |
| **Role** | Taxonomy entry for a repo: `component`, `adapter`, `third_party`, or `docs` | `manifest/workspace.toml` |
| **Required capabilities** | Adapter-level contract declarations (e.g. `container_exec`, `fs_ops`, `deps_inventory`, `policy`, `defaults`) | `manifest/workspace.toml` |
| **Protocol + fixtures** | Shared compatibility contracts in `protocol/` | `protocol/protocol.md` |
| **Materialization** | Act of fetching/placing repos at their defined local paths via the runner | `docs/Repo_Layout_Workspace_Composition_Spec_v0.1.md` |
| **Lock drift** | State where the lock file diverges from materialized state | `docs/SCOPE_PURPOSE_STATUS_BACKLOG.md` |
| **SBOM** | Software Bill of Materials; planned CycloneDX JSON output | `docs/SCOPE_PURPOSE_STATUS_BACKLOG.md` |
| **WorkspaceInventoryArtifact** | Artifact emitted by sociosphere describing repo membership | `agentplane/docs/sociosphere-bridge.md` |
| **LockVerificationArtifact** | Artifact asserting lock file is valid | `agentplane/docs/sociosphere-bridge.md` |
| **TaskRunArtifact** | Artifact recording build/test run results | `agentplane/docs/sociosphere-bridge.md` |
| **ProtocolCompatibilityArtifact** | Artifact asserting adapter protocol fixture compatibility | `agentplane/docs/sociosphere-bridge.md` |
| **Governance graph** | Cross-repo topology of ownership, role, authority, policy, evidence, execution, and replay relationships | Ecosystem enrichment |
| **Repo authority boundary** | The responsibilities a repo may own and the responsibilities it must not duplicate | Ecosystem enrichment |
| **Evidence-producing repo** | Repo that emits artifacts, receipts, logs, validations, or attestations consumed by institutional action workflows | Ecosystem enrichment |
| **Execution substrate** | Repo or runtime layer that performs bounded tool, agent, workflow, build, deploy, or validation actions | Ecosystem enrichment |
| **Integration claim** | Assertion that one repo is functionally connected to another through manifest entry, protocol fixture, runtime touchpoint, evidence output, or governance ownership | Ecosystem enrichment |
| **Integration drift** | State where an integration claim lacks a matching contract, pin, fixture, evidence artifact, validation path, owner, or feedback loop | Ecosystem enrichment |
| **Institutional-action topology** | Sociosphere view linking SocioProphet actions to actors, roles, policies, evidence bundles, procedure templates, execution receipts, and owning repos | Ecosystem enrichment |

### Domain-specific language
- Repos are **materialized** into a workspace, not cloned arbitrarily.
- Compatibility is asserted through **fixtures** (test vectors), not integration stubs.
- The runner uses **role-driven** execution: the manifest role determines which tasks apply.
- **Deterministic** reasoning: lock file pins exact revisions so all assertions evaluate
  against known inputs.
- Governance reasoning is **topology-bound**: an institutional action is only safe to
  execute when Sociosphere can identify the responsible repos, pinned revisions,
  authority boundaries, evidence artifacts, and replay path.
- Repo membership is not enough. Integration requires a manifest entry, runtime or
  validation touchpoint, governance owner, evidence output or reference, and feedback
  path.
- Sociosphere should prevent ownership duplication between platform, workspace, agent,
  policy, contract, storage, model, and delivery repos.

### Semantic bindings to other repos
- **→ agentplane**: sociosphere is upstream; generates bundles agentplane executes.
- **→ prophet-platform / socioprophet-web / etc.**: sociosphere orchestrates those repos as
  "components".
- **→ TriTRPC**: pins TriTRPC as a `third_party` dependency.
- **↔ socioprophet**: socioprophet is the institutional action surface; sociosphere is the
  repo/topology authority that lets those actions be traced to ownership, evidence, and
  execution boundaries.
- **→ hellgraph**: sociosphere provides the repo and topology facts that HellGraph should
  query for governance, release readiness, integration drift, and institutional-action
  safety.
- **→ prophet-platform**: sociosphere supplies topology and evidence-posture signals for
  platform deployment gates and release-readiness scoring.

---

## 3. Topic Modeling

| Topic | Keywords | Weight |
|---|---|---|
| Workspace orchestration | manifest, lock, runner, fetch, build, test, determinism | dominant |
| Repo role taxonomy | component, adapter, third_party, required_capabilities, ontology | high |
| Protocol / fixtures / contracts | protocol, fixtures, adapter, compatibility | high |
| Supply-chain traceability | SBOM, CycloneDX, inventory, license_hint, revision pins | medium |
| CI / automation | lock-drift check, smoke test, structured failure reporting | medium |
| Agent execution hand-off | WorkspaceInventoryArtifact, bundle, agentplane bridge | medium |
| FIPS / security compliance | GLOSSARY-FIPS, policy defaults | low |
| Governance graph | ownership, authority boundary, policy basis, evidence repo, execution substrate, replay | high |
| Integration drift detection | manifest claim, runtime touchpoint, fixture, evidence artifact, governance owner, feedback loop | high |
| Institutional-action topology | Actor, Role, Evidence bundle, Procedure template, ApprovalEvent, ExecutionReceipt, owning repo | high |
| Release-readiness reasoning | topology signal, evidence posture, validation obligation, platform gate, readiness score | medium-high |

---

## 4. Dependency Graph

### Direct dependencies
- Python 3 runtime
- `third_party/` submodule pins (TriTRPC confirmed by `docs/INTEGRATION_STATUS.md`)
- Component repos in `manifest/workspace.toml`:
  prophet_cli (Go), sourceos_a2a_mcp_bootstrap, socioprophet-web, dev-api,
  hdt_app, human_digital_twin, ontogenesis, plus adapters `cc` and `configs`

### Dependent systems
- **agentplane** (explicitly; bridge document declares sociosphere as upstream)
- Any CI pipeline that runs `tools/runner/runner.py` workspace-wide
- **socioprophet** regulated-domain workflows that need repo/topology authority for
  institutional actions
- **hellgraph** governance and release-readiness queries over repo topology
- **prophet-platform** deployment gates and platform-readiness scoring that consume
  topology, evidence, and validation posture

### Governance graph relationships
```text
socioprophet  -- emits/records --> InstitutionalAction
InstitutionalAction -- requires --> Actor + Role + Authority + Context + Evidence + Policy + Procedure + Capability + Approval + ExecutionReceipt
sociosphere  -- indexes --> repo ownership + role taxonomy + pinned revision + integration claim + evidence source + execution substrate
hellgraph    -- queries --> governance graph + integration drift + release readiness
agentplane   -- executes --> bounded tool/agent actions + replay artifacts
prophet-platform -- validates/deploys --> release-ready governed surfaces
```

### Cross-repo impact when sociosphere changes
- Manifest schema change → all components must update how they declare tasks.
- Lock file change → every component is re-pinned; agentplane must re-validate bundles.
- Protocol/fixtures change → adapter contract compatibility must be re-verified across all
  adapters.
- Governance graph vocabulary change → socioprophet, hellgraph, prophet-platform,
  standards repos, and agentplane must update related query, validation, and evidence
  expectations.
- Repo authority boundary change → ownership and duplication assumptions must be reviewed
  across platform, workspace, policy, storage, agent, and delivery repos.

---

## 5. Change Impact Rules

| What changed | Downstream repos affected | DevOps actions | Governance gates |
|---|---|---|---|
| `manifest/workspace.toml` schema | All components | Re-run `runner list`, `runner fetch` | Manifest version bump; ADR if role taxonomy changes |
| `manifest/workspace.lock.json` update | All pinned repos + agentplane | Full `runner run build --all` + `run test --all` | Lock review; parity check with `INTEGRATION_STATUS.md` |
| `protocol/` fixtures | All adapters | Adapter contract tests | Protocol version bump; fixture regression gate |
| `tools/runner/runner.py` | All CI using runner | CI smoke test | Smoke test must pass before merge |
| `third_party/` submodule pin (e.g. TriTRPC) | Downstream integration assumptions | Rebuild dependent components | Integration note in `docs/INTEGRATION_STATUS.md` |
| Governance graph vocabulary | socioprophet, hellgraph, prophet-platform, standards repos, agentplane | Regenerate repo-intelligence graph; validate ontology/query consumers | Governance vocabulary review mandatory |
| Repo authority boundary | Platform, workspace, policy, storage, model, agent, and delivery repos | Review ownership map and duplicate responsibility claims | Architecture review mandatory |
| Integration claim or integration-drift rule | All repos named by the claim | Verify manifest membership, pin, fixture, runtime touchpoint, evidence output, and owner | Integration evidence required |
| Evidence-producing repo classification | socioprophet, agentplane, standards-storage, hellgraph, prophet-platform | Validate artifact schema, retention posture, hashing, and graph ingestion | Evidence-chain review mandatory |
| Execution substrate classification | agentplane, prophet-platform, AgentOS consumers | Re-run bounded execution and replay checks | Human-in-command and replay gate required for high-stakes actions |
