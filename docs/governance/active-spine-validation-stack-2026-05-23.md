# Active spine validation stack — 2026-05-23

## Purpose

This document records the active-spine governance gates now enforced in SocioProphet/sociosphere. It is a review surface for the current consolidation sprint and a handoff map for future GitOps work.

## Active-spine source surfaces

The active spine is represented across these governance surfaces:

- `registry/spine-v0.txt`
- `manifest/active-spine.repos.toml`
- `governance/CANONICAL_SOURCES.yaml`
- `catalog/boundaries.yaml`
- `docs/TOPOLOGY.md`

These surfaces are intentionally redundant. The redundancy is a governance feature: drift between registry, manifest overlay, canonical source ownership, topology narrative, and boundary jurisdiction should fail validation.

## Validation gates wired into `make validate`

### Spine registry

- Target: `spine-v0-validate`
- Tool: `tools/check_spine_v0.py`
- Function: verifies required active-spine registry coverage.

### Manifest overlay

- Target: `active-spine-overlay-validate`
- Tool: `tools/check_active_spine_overlay.py`
- Function: verifies committed active-spine manifest overlay coverage.

### Source coverage

- Target: `active-spine-sources-validate`
- Tool: `tools/check_active_spine_sources.py`
- Function: verifies agreement between the registry, committed overlay, and canonical-source map for active-spine overlay repos.

### Canonical-source drift

- Target: `spine-canonical-sources-drift-validate`
- Tool: `tools/check_spine_canonical_sources_drift.py`
- Function: verifies broader active-spine coverage in `governance/CANONICAL_SOURCES.yaml`.

### Topology narrative

- Target: `topology-doc-active-spine-validate`
- Tool: `tools/check_topology_doc_active_spine.py`
- Function: verifies `docs/TOPOLOGY.md` reflects the active-spine model and does not regress to the stale two-repo topology.

### Boundary coverage

- Target: `active-spine-boundaries-validate`
- Tool: `tools/check_active_spine_boundaries.py`
- Function: verifies active-spine repo and boundary-class coverage in `catalog/boundaries.yaml`.

### Runner overlay discovery

- Target: `runner-overlay-discovery-validate`
- Tool: `tools/check_runner_overlay_discovery.py`
- Function: records the current operational state: manifest overlay support exists as a helper and merge-order validator, while direct `tools/runner/runner.py` consumption remains pending.

### Runner overlay merge order

- Target: `runner-overlay-merge-order-validate`
- Tool: `tools/check_runner_overlay_merge_order.py`
- Function: validates intended manifest merge order: `workspace.toml`, committed `*.repos.toml` overlays, then local `overrides.toml`.

## Hygiene gates

### Final newline guard

- Target: `hygiene-check`
- Tool: `tools/check_final_newlines.py`
- Function: verifies final-newline hygiene for active-spine governance files, runner overlay helper files, and boundary coverage files.

## Open implementation debt

### Issue #364: patch-safe runner overlay integration

`tools/runner/manifest_layers.py` and `tools/check_runner_overlay_merge_order.py` are merged, but `tools/runner/runner.py` has not yet been patched to consume `manifest/active-spine.repos.toml` operationally.

Required patch when a patch-safe edit route is available:

1. Import `load_layered_manifest` from `tools/runner/manifest_layers.py`.
2. Change the runner manifest loader so committed overlays are included before local overrides.
3. Preserve `manifest/overrides.toml` as the final local-only override layer.
4. Update `tools/check_runner_overlay_discovery.py` so it requires runner overlay consumption instead of documenting the pending state.

## Current risk posture

Strong controls now exist for registry, manifest overlay, canonical-source, topology, and boundary drift. The primary remaining gap is operational runner consumption of committed overlays. Until Issue #364 is resolved, validation recognizes the overlay and merge order but the legacy runner commands still use the old loader path.
