# ADR-0002 — Strategic Decision Plane Registry, Product-Surface Reconciliation, and Release Gates

Status: draft  
Date: 2026-04-11

## Context

The portfolio now has:
- a canonical narrative strategy
- a machine-readable decision-plane registry
- an ownership matrix
- a validator and CI workflow
- a product-surface source file in `SocioProphet/socioprophet/config/surfaces.json`

The earlier governance pack correctly split narrative and registry ownership, but it did not fully incorporate the product-surface source of truth or the newly elevated anchor repos.

## Decision

We keep the original source-of-truth split and extend it:

1. **Narrative source of truth**
   - `SocioProphet/socioprophet/docs/strategy/CANONICAL_TECH_STRATEGY.md`

2. **Machine-readable source of truth**
   - `SocioProphet/sociosphere/registry/decision-planes.yaml`
   - `SocioProphet/sociosphere/registry/decision-plane-ownership-matrix.csv`

3. **Product-surface reconciliation input**
   - `SocioProphet/socioprophet/config/surfaces.json`

4. **Validation**
   - Registry changes must validate schema + matrix consistency.
   - Reconciliation against `config/surfaces.json` is a required follow-on automation path, even if not fully enforced in the first CI tranche.

## Implications

- The registry is the canonical portfolio control vocabulary.
- The surface config is the canonical product-surface inventory input.
- The rendered `surface-inventory.md` is informative, not primary.
- Anchor repos may implement local plane gates, but they must not redefine plane semantics.

## Newly elevated anchors

This revision explicitly recognizes the following as portfolio-significant anchors:
- `policy-fabric`
- `cloudshell-fog`
- `memory-mesh`
- `ontogenesis`

## Follow-on decisions

1. Add an automated reconciliation check between the plane registry and `config/surfaces.json`.
2. Decide whether `policy-fabric` remains cross-plane or later becomes a named control-fabric layer.
3. Decide how Cloud Suite packaging should relate to `cloudshell-fog` and broader managed-platform scope.
