# Decision Plane Integration Review v0.2

Date: 2026-04-11  
Scope: live public repo sample + live product-surface source + sampled open PR queue

## Purpose

This note records the delta between the earlier v0.1 governance pack and the live repo/doc state reviewed in this pass.

## Concrete corrections adopted

### 1. Product-surface source of truth

The rendered Surface Inventory is generated from `config/surfaces.json` by `scripts/build_surface_inventory.py`. The governance pack must treat that JSON source as the product-surface input for reconciliation.

### 2. Newly elevated portfolio anchors

The following repositories are now treated as portfolio-significant anchors:

- `policy-fabric`
- `cloudshell-fog`
- `memory-mesh`
- `ontogenesis`

### 3. Digital Trust status correction

Digital / Trust is an active named surface in the product-surface source and rendered inventory. It remains a stub in packaging status, but not an imaginary or future-only category.

## Merge-risk summary

### `SocioProphet/sociosphere`

Sampled open PRs:
- PR #70 changes `patches/workspace-manifest-cleanup-2026-04-09.md`
- PR #71 changes `manifest/workspace.toml`

Assessment:
- direct path collision risk with the decision-plane pack is low
- semantic coupling to manifest naming and workspace authority remains medium

### `SocioProphet/socioprophet`

Sampled open PRs:
- PR #259 adds public trust/assurance guide pages
- PR #261 adds governance and visual-review workflows
- PR #272 hardens embedded `agentplane/`
- PR #275 adds `semantic/repo.jsonld`

Assessment:
- direct path collision risk with `docs/strategy/*` is low
- semantic overlap with trust, governance, repo-identity, and embedded control-plane positioning is medium

## Packaging consequence

The existing repo-drop pack should be treated as superseded by the corrected v0.2 strategy and registry inputs. Regenerate the repo-drop layer after incorporating the corrected anchors.

## Updated recommendation

1. update registry and matrix from v0.2 artifacts
2. preserve strategy files under `docs/strategy/`
3. add a later automation step that reconciles registry expectations against `config/surfaces.json`
4. only then regenerate PR/drop-pack assets
