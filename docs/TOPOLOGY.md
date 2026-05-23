# Repo topology (canonical)

This document records the active repository topology for the SocioProphet workspace. It supersedes the earlier two-repo topology that treated `sociosphere` and `tritrpc` as the only core repos.

## Active spine

### Estate controller

- **SocioProphet/sociosphere**: workspace controller, manifest governance surface, validation fabric, and integration estate.

### Runtime platform

- **SocioProphet/prophet-platform**: canonical runtime platform and control-plane implementation surface.

### Transport and protocol standard

- **SocioProphet/TriTRPC**: canonical transport/RPC standard, schema surface, fixtures, and reference compatibility lane.

### Platform and domain standards

- **SocioProphet/prophet-platform-standards**: platform standard surface consumed by the runtime platform and workspace governance gates.
- **SocioProphet/socioprophet-standards-storage**: canonical storage standard lane.
- **SocioProphet/socioprophet-standards-knowledge**: canonical knowledge standard lane.
- **SocioProphet/socioprophet-agent-standards**: agent profile and agent behavior standard lane; promotion candidate until all consuming gates are complete.

### Product and proof-runtime candidates

- **SocioProphet/prophet-workspace**: workspace product suite and user-facing workspace surface; promotion candidate.
- **SocioProphet/hellgraph**: proof graph runtime and field-graph execution candidate; restricted promotion candidate until trust, proof, and runtime boundaries are fully validated.

### Adjacent SourceOS lane

- **SourceOS-Linux/sourceos-spec**: adjacent SourceOS schema/specification lane. This is not owned by the SocioProphet GitHub organization, but it is part of the active SourceOS adjacency and must remain explicitly represented in governance checks.

## Topology rules

1. `sociosphere` owns workspace composition, validation, and cross-repo governance. It may reference active-spine repos through manifests, overlays, registry files, and canonical-source maps.
2. Active-spine repos must not treat `sociosphere` as a runtime dependency. They may consume published schemas, releases, or governance contracts, but the estate controller must not become their embedded runtime.
3. Protocol and standard repos should remain consumable independently. Runtime/product repos may depend on standards; standards should not depend on runtime/product implementations.
4. Submodule pins are explicit and reviewed. Submodules must live under `third_party/` and be pinned through `manifest/workspace.lock.json` when materialized as submodules.
5. `manifest/workspace.toml`, committed `manifest/*.repos.toml` overlays, `registry/spine-v0.txt`, and `governance/CANONICAL_SOURCES.yaml` must remain mutually consistent.
6. `manifest/overrides.toml` is a local-only override and must remain uncommitted.
7. Promotion candidates become canonical only after registry, canonical-source, boundary, manifest/overlay, and validation coverage all agree.

## Current validation surfaces

- `tools/check_topology.py` enforces submodule path rules, self-dependency rules, and submodule pin sanity.
- `tools/check_spine_v0.py` enforces required active-spine registry coverage.
- `tools/check_active_spine_overlay.py` validates committed active-spine manifest overlay coverage.
- `tools/check_active_spine_sources.py` validates registry, overlay, and canonical-source agreement for active-spine overlay repos.
- `tools/check_spine_canonical_sources_drift.py` validates broader active-spine canonical-source coverage.
- `tools/check_runner_overlay_discovery.py` documents the current runner overlay consumption state.
- `tools/check_runner_overlay_merge_order.py` validates intended manifest merge order for `workspace.toml`, committed `*.repos.toml` overlays, and local `overrides.toml`.

## Notes / archival

- **SocioProphet/tritrpc-notes-archive**: raw historical TriTRPC drafts. This is provenance material, not an active runtime dependency.
- Curated transport narrative belongs in the canonical `TriTRPC` repo documentation.
- Legacy topology references that imply only `sociosphere` and `tritrpc` are core should be treated as stale.

## Repository hygiene requirements

- `.DS_Store`, `__MACOSX/`, and `._*` files must never be committed.
- Submodule entries in `.gitmodules` must be present and pinned to exact revisions in `manifest/workspace.lock.json` when governed as submodules.
- `.gitignore` excludes `.DS_Store` and `Thumbs.db`; CI hygiene checks remain the enforcement backstop.

## Submodule update playbook

To bump a submodule pin, for example `third_party/tritrpc`:

1. Fetch the new tag or commit SHA from the upstream repo.
2. Update `manifest/workspace.toml` or the relevant committed manifest overlay if that repo is governed through an overlay.
3. Update `manifest/workspace.lock.json`: set `rev` and `retrieved_at` for the relevant entry.
4. Run `git submodule update --init <submodule-path>` to checkout the new commit.
5. Stage and commit with a message like `chore(workspace): bump <repo> pin to <sha> (ref: #<issue>)`.
6. Open a PR linking to the upstream release/tag and the issue that motivated the bump.
7. CI topology and active-spine checks verify the pin and governance surfaces.

See also: [Naming and versioning policy](NAMING_VERSIONING.md).
