# Network-aware workspace lock materializer v0

Status: design/contract baseline
Issue: #423

## Purpose

Sociosphere currently maintains `manifest/workspace.lock.json` using `manifest_declared_refs_only`. That lock records the refs declared in `manifest/workspace.toml` and is safe for offline validation.

This tranche defines the next lock layer: a network-aware resolver that can resolve `url + ref` entries to live commit SHAs without replacing the offline lock path.

## Non-goals

- Do not mutate `manifest/workspace.toml`.
- Do not remove or weaken `manifest/workspace.lock.json`.
- Do not run live network resolution inside default `make validate`.
- Do not redefine repo ownership, boundary, trust-zone, or capability semantics.

## Proposed artifact

The resolver should write a separate artifact first:

```text
manifest/workspace.resolved.lock.json
```

This avoids changing the semantics of the existing declared-ref lock.

## Resolution rules

1. Parse `manifest/workspace.toml` using the same repo-entry semantics as `tools/generate_workspace_lock.py`.
2. Reject duplicate repo names before any network work.
3. For entries with explicit `rev`, preserve that revision as authoritative.
4. For entries with `url + ref`, resolve the ref to a commit SHA.
5. If both `ref` and `rev` exist, verify that `ref` currently resolves to `rev`; if it does not, fail closed unless an explicit drift-ack mode is used.
6. Fail closed on unreachable repos, missing refs, ambiguous refs, malformed URLs, and duplicate repo names.
7. Emit per-repo resolution status rather than silently dropping unresolved entries.
8. Separate offline validation from live-network validation.

## Lock shape

The resolved lock should include:

- `schema_version`
- `generated_at`
- `source_manifest`
- `source_lock`
- `resolution_mode = live_ref_resolution`
- `repo_count`
- `repos[]`

Each repo should include at least:

- `name`
- `url`
- `role`
- `declared_ref`
- `declared_rev`
- `resolved_rev`
- `resolution_status`
- `local_path` when present
- `trust_zone` when present
- `required_capabilities` when present
- `required_grants` when present

## Validation modes

```bash
python3 tools/generate_workspace_resolved_lock.py --write
python3 tools/generate_workspace_resolved_lock.py --check
python3 tools/generate_workspace_resolved_lock.py --check --allow-drift
```

`--check` should fail if the resolved lock is absent or stale. `--allow-drift` should report drift without failing, for operator review.

## CI posture

- Default offline validation remains unchanged.
- A separate workflow should run the resolver only when explicitly requested or when resolver files change.
- Network-aware validation should never become a hidden dependency of unrelated documentation-only changes.

## Workspace Context Fabric acceptance slice

The first implementation must prove resolution for:

- `prophet_workspace`
- `agent_registry`
- `memory_mesh`
- `socioprophet_agent_standards`

The resolver may cover the full manifest, but these four entries are the minimum acceptance slice for issue #423.
