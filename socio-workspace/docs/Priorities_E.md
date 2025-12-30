# Priorities “E” (Execution) — v0.1

We keep “E” as our execution spine: the minimum set of primitives that makes everything else real, testable, and repeatable.

## E0 — Workspace determinism (must-have)
- Manifest + lock format is canonical (`manifest/workspace.toml`, `manifest/workspace.lock.json`).
- Runner supports: `list`, `fetch`, `run`, `lock-verify`.
- CI enforces: lock drift check + basic runner smoke test.

## E1 — Task contract normalization
- Each component exposes build/test tasks via one of: Makefile / justfile / Taskfile / scripts.
- Runner detects tasks deterministically and reports structured failures.
- Add minimal compatibility fixtures in `protocol/fixtures` and run them in CI.

## E2 — Supply-chain visibility
- Inventory report: repo + rev + license hint.
- Optional commit signature verification (when available).
- SBOM stub generation for build artifacts (start with CycloneDX/JSON output).

## E3 — Adapter portability
- Adapter contract tests run locally and in CI.
- macOS adapter (dev workstation) + Linux/container adapter (CI/servers) share the same protocol fixtures.

### Why this exists
The fastest way to lose the plot is to build features without an execution spine. “E” is the spine.
