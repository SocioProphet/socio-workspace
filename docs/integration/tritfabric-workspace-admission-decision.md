# TritFabric workspace admission decision

## Decision

Admit TritFabric as a Sociosphere-tracked workspace component in a follow-on manifest tranche.

Do not hand-edit the workspace lock in this tranche.

## Basis

TritFabric has absorbed the recovered Atlas, Community Learning, Network Atlas, and Serve work through the downstream tranche sequence already registered in Sociosphere.

Review of the current Sociosphere workspace files shows that TritFabric is not yet a workspace dependency. Therefore there is no existing lock entry to bump.

## Correct sequence

1. Add TritFabric to the workspace manifest.
2. Add TritFabric to the canonical repository registry.
3. Regenerate the workspace lock with the Sociosphere runner.
4. Verify the generated lock and policy checks.
5. Commit the generated lock only after runner validation.

## Boundary

This document records the admission decision only. It does not materialize TritFabric, regenerate the lock, or claim runner validation.
