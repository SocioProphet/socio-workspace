# Runner overlay integration status — 2026-05-23

## Status

The committed manifest overlay merge helper exists in `tools/runner/manifest_layers.py` and the merge-order validator is wired into `make validate`.

Operational integration into `tools/runner/runner.py` is still pending.

## Current behavior

`tools/runner/runner.py` still loads `manifest/workspace.toml` and optional local `manifest/overrides.toml` through its legacy loader path.

`manifest/active-spine.repos.toml` is validated as a committed overlay, but it is not yet consumed by the operational runner.

## Blocker observed in this tranche

The GitHub connector blocked the full-file `tools/runner/runner.py` contents update before the update reached GitHub. Because the connector exposes no patch-level edit primitive for this repository path, the safe decision was not to force a long full-file replacement.

## Required next patch

Patch only the runner loader surface when a patch-safe edit path is available:

1. Import `load_layered_manifest` from `tools/runner/manifest_layers.py`.
2. Change `load_manifest_raw()` so it returns `load_layered_manifest(include_overrides=False)`.
3. Preserve `load_overrides_raw()` and `merge_manifest_and_overrides()` so local `manifest/overrides.toml` remains the final override layer.
4. Update `tools/check_runner_overlay_discovery.py` after the operational runner consumes the overlay.

## Guardrails

Do not rewrite `tools/runner/runner.py` from a partial fetch. Only patch from a complete file view or a patch-level API.
