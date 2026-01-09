# Sociosphere scope, purpose, current state, and backlog

## Purpose
Sociosphere is the workspace controller repo that keeps multi-repo development reproducible. It defines the canonical workspace manifest and lock, provides a runner to fetch/build/test components, and hosts the protocol/fixtures that define adapter compatibility. The goal is deterministic orchestration of component repositories rather than feature work inside those repositories.

## Scope
### In scope
- **Workspace orchestration**: the manifest + lock format, plus tools to list/fetch/run components deterministically.
- **Execution primitives**: repeatable build/test tasks, inventory reports, and compatibility fixtures.
- **Protocol + fixtures**: shared adapter contracts and fixtures used across components.
- **Dependency pins**: submodule pins for core dependencies (for example TritRPC) and policies for updating them.

### Out of scope
- **Product features** that live inside component repos (application logic, UI, APIs).
- **Long-lived forks** of dependencies (we only pin versions and surface integration notes here).
- **CI implementations** owned by downstream repos (Sociosphere only provides the primitives and checks needed for workspace determinism).

## Current state (v0.1)
- **Workspace controller is operational** with a canonical manifest and lock, plus the runner entry point in `tools/runner`.
- **Protocol + fixtures exist** in `protocol/` as the shared compatibility surface.
- **Integration status is tracked** in `docs/INTEGRATION_STATUS.md`, including TritRPC pinning.
- **Execution priorities are documented** in `docs/Priorities_E.md` to keep the minimum spine visible.
- **Repo role ontology is defined in spec** via manifest roles (component/adapter/third_party) and task contracts in `docs/Repo_Layout_Workspace_Composition_Spec_v0.1.md`.

## Ontology integration (broader repos)
Sociosphere treats the manifest as the source of truth for repo roles and relationships. This section clarifies what is **functional today** versus what is **self-describing on paper** so the integration story stays explicit.

### Functional state (what exists today)
- **Role taxonomy is documented**: component, adapter, and third_party roles are defined in the workspace composition spec.
- **Materialization paths are specified**: components are expected under `components/`, adapters under `adapters/`, and third_party under `third_party/`.
- **Runner expectations are described**: the runner reads manifest + lock and orchestrates tasks across materialized repos.

### Self-describing state (what should be encoded in metadata)
- **Manifest fields describe intent**: `name`, `url`, `ref`/`rev`, `role`, `path`, and `license_hint` (plus `required_capabilities` for adapters) define how each repo should be interpreted.
- **Task contracts are explicit**: component repos expose build/test tasks via Makefile/justfile/Taskfile/scripts, allowing the runner to reason about execution without bespoke glue.
- **Protocol + fixtures define compatibility language**: adapter fixtures and error codes provide the vocabulary for reasoning about integration outcomes.

### Integration and reasoning model
- **Integration is role-driven**: the manifest role determines where a repo is materialized and which execution primitives apply.
- **Reasoning is deterministic**: the lock file pins exact revisions so compatibility assertions (fixtures, task contracts) are evaluated against known inputs.
- **Status is traceable**: updates to pins and integration notes are recorded in `docs/INTEGRATION_STATUS.md`.

## Backlog (rolling, v0.1)
This backlog is intentionally scoped to Sociosphere’s responsibilities. Each item should link to an issue/PR when created.

### P0 — Must-have to preserve determinism
1. **Manifest/lock verification in CI**
   - Add a lock drift check for `manifest/workspace.lock.json`.
   - Add a minimal runner smoke test (`list`, `fetch`, `run build --all`).
2. **Version pin policy clarity**
   - Document how to bump submodule pins and how to annotate compatibility in `docs/INTEGRATION_STATUS.md`.

### P1 — Standardize execution contracts
1. **Task discovery normalization**
   - Define how `tools/runner` discovers tasks from Makefile/justfile/Taskfile/scripts.
   - Add fixture tasks under `protocol/fixtures` and wire to runner.
2. **Structured failure reporting**
   - Emit consistent error metadata from runner for downstream CI usage.
3. **Ontology enforcement**
   - Validate manifest `role` and `path` conventions during `runner fetch`.
   - Emit a structured report mapping repos to roles and capabilities.

### P2 — Supply-chain visibility
1. **Inventory report**
   - Generate a report of repos, revisions, and license hints.
2. **SBOM stub**
   - Start emitting CycloneDX JSON for build artifacts.

### P3 — Adapter portability
1. **Contract tests**
   - Run adapter contract tests locally and in CI using the same fixtures.
2. **macOS/Linux parity**
   - Document portable adapter expectations and edge cases.

## How to keep this current
- Update the **Current state** section when a capability lands in `manifest/`, `tools/runner`, or `protocol/`.
- Add or re-prioritize backlog items as new gaps are discovered in integration work.
