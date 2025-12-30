# Repo Layout & Workspace Composition Spec v0.1

## Purpose
Define a modular, composable *workspace* that behaves like a monorepo for builds/tests/releases, while preserving independent sub-repositories as first‑class units.

This spec is written for:
- A daily-driver macOS (Apple Silicon) dev workstation.
- Open-source–only policy.
- Cross-distro / cross-package-manager extensibility (conda-first, but not conda-only).

## Design Goals
1. **Composable workspace**: one “meta repo” assembles a reproducible workspace from many repos.
2. **Deterministic builds**: a build should be reconstructible from a manifest + lock.
3. **No single package-manager dependency**: supports conda/pixi, but also brew/nix/rpm/apt as optional adapters.
4. **Security-friendly**: supply-chain traceability; minimal hidden magic.
5. **Adapter-driven**: the same runner can target macOS, Linux distros, or containers by swapping adapters.

## Non-Goals
- Not trying to replace GitHub org structure.
- Not trying to vendor every dependency into the workspace.
- Not trying to be byte-for-byte reproducible on macOS on day 1.

## Core Idea: “Meta-repo + Manifest + Fetcher”
Rather than a traditional monorepo, we use a *meta-repo* that defines a workspace via a manifest.

### Why not classic monorepo?
- You want independent repos for ownership, history, licensing, and selective sharing.
- You also want a single build/test harness.

So we treat the monorepo as a **materialized workspace**, not a single Git history.

## Repository Types
### 1) Meta Repo (Workspace Controller)
The “one repo to rule the assembly.”
Responsibilities:
- Manifest + lock for component repos
- Runner + test harness
- Shared protocol specs + fixtures
- CI workflows orchestrating multi-repo builds

Suggested name: `socio-workspace` (or `sourceos-workspace`).

### 2) Component Repos
Independent repos that provide:
- Libraries
- CLIs
- Services
- Docs

Each component repo must implement the same minimal interface (“Task Contract”) so the workspace can build/test it consistently.

### 3) Adapter Repos
Backends implementing execution primitives:
- deps_inventory
- lock_update
- container_exec
- fs_ops
- etc.

Adapters can live as separate repos or as packages under a single adapter repo.

### 4) Third‑Party Mirrors / Forks
Tracked for reference, patching, or future integration.
Rules:
- They are **not** default workspace components.
- They may be pulled into `third_party/` only by explicit manifest opt‑in.

## Composition Method: Manifest Fetch (Preferred)
### Decision: Use a workspace manifest (not Git submodules) as the primary composition mechanism.

#### Rationale
- Submodules are easy to break, awkward in CI, and painful for partial checkouts.
- Subtree is workable but pushes you toward vendoring.
- A manifest-based fetcher gives:
  - pinned revisions
  - selective inclusion
  - workspace overlays
  - a path to cryptographic verification

## Workspace Layout (Materialized)
After `workspace fetch`, the working tree looks like:

```
/ (meta repo)
  /manifest
    workspace.toml
    workspace.lock.json
  /tools
    runner/        # CLI for orchestrating build/test
    fetcher/       # resolves manifest -> clones repos
  /protocol
    protocol.md
    error_codes.md
    fixtures/      # compatibility test vectors
  /components
    <name>/        # checked-out component repos
  /adapters
    <name>/        # adapter repos (optional separate)
  /third_party
    <name>/        # optional mirrors/forks; explicit opt-in
  /ci
    workflows/     # github actions templates
  /docs
```

### Directory invariants
- `components/` is *materialized* by the fetcher.
- The lock file is committed.
- The manifest is committed.

## Manifest + Lock
### Manifest (`workspace.toml`)
Defines desired repos and “roles”:
- component
- adapter
- third_party

Fields (minimum viable):
- `name`
- `url`
- `ref` (branch/tag) OR `rev` (commit)
- `role`
- `path` (target directory)
- `license_hint` (non-authoritative; used for policy gating)
- `required_capabilities` (for adapters)

### Lock (`workspace.lock.json`)
Resolved, exact inputs:
- `name`
- `url`
- `rev` (commit SHA)
- `tree_hash` (optional, best-effort)
- `retrieved_at`

Lock rules:
- Lock updates are explicit.
- CI verifies lock is up to date (no drift).

## Component “Task Contract”
To be buildable/testable in a uniform way, every component repo must expose tasks.

### Contract v0.1
Each component provides at least one of:
- `taskfile.yml` (Taskfile)
- `justfile` (Just)
- `Makefile`
- `scripts/` with documented entrypoints

And must implement:
- `build`
- `test`
- `lint` (optional at first)
- `fmt` (optional at first)

The runner chooses the best available task system based on capability negotiation.

## Runner Responsibilities (Workspace Orchestration)
The runner is the “conductor”:
- Reads manifest + lock
- Fetches and materializes workspace
- Runs tasks across components
- Collects structured reports
- Executes compatibility tests against adapters

Key concept: the runner never assumes brew/nix/rpm; it asks adapters what they can do.

## Test Harness Strategy
### 1) Adapter contract tests
Use JSON fixtures:
- request -> expected response shape
- expected error codes

### 2) Component unit tests
Each component runs its native tests.

### 3) Workspace integration tests
Spin up a minimal materialized workspace and run:
- `fetch`
- `build`
- `test`

### 4) Release rehearsal
A dry-run pipeline that:
- checks licensing policy
- checks lock drift
- generates SBOM-like inventory
- produces artifacts

## Definition of Done (v0.1)
- A meta repo exists with this structure and docs.
- A manifest + lock can materialize a workspace with ≥ 2 components and ≥ 1 adapter.
- `runner fetch` and `runner test` work locally and in CI.
- Compatibility fixtures are stored and executed against at least one adapter.

## Self-critique and likely improvements
- This spec leans hard toward “manifest fetcher” without yet proving ergonomics; we should implement a thin prototype before expanding scope.
- The task contract may need tightening (e.g., explicit toolchain metadata) to avoid painful edge cases.
- We should explicitly define licensing policy gates (allowed licenses, exceptions) rather than leaving it implied.
- The “security plan” is staged but not tied to concrete checks; next revision should define exact checks and failure conditions.
