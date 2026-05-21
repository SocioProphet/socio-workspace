# Corpus Loop v0 Coordination Manifest

Status: v0.1 coordination manifest.

This document records the Sociosphere-owned coordination layer for the Watson/Cyc/Semantic-Web/CHRONOS deployable loop.

## Source corpus

- `SocioProphet/sociosphere#334` — governed Watson/Cyc/Semantic-Web/CHRONOS corpus substrate.

## Coordination issue

- `SocioProphet/sociosphere#335` — deployable cybernetic loop v0 coordination.

## Component carriers

| Plane | Owner repo | Merged carrier |
|---|---|---|
| Evidence | `SocioProphet/sherlock-search` | `SocioProphet/sherlock-search#58` |
| Ontology | `SocioProphet/ontogenesis` | `SocioProphet/ontogenesis#103` |
| Policy | `SocioProphet/policy-fabric` | `SocioProphet/policy-fabric#85` |
| Runtime carrier | `SocioProphet/agentplane` | `SocioProphet/agentplane#184` |
| Ledger record | `SocioProphet/model-governance-ledger` | `SocioProphet/model-governance-ledger#20` |

## Sociosphere-owned surfaces

```text
schemas/corpus-loop-v0.schema.json
registry/corpus-loop-v0/valid.watson-cyc-chronos.json
registry/corpus-loop-v0/invalid.missing-ledger-plane.json
registry/corpus-loop-v0/invalid.sociosphere-owns-downstream.json
tools/check_clv0.py
```

## Validation

Run:

```bash
make corpus-loop-v0-validate
```

The target is included in:

```bash
make validate
```

The manifest validates that the five required planes are represented and that Sociosphere remains coordination-only.

## Boundary

Sociosphere owns the cross-repo coordination manifest and topology validation.

Sociosphere does not own downstream implementation for Sherlock, Ontogenesis, Policy Fabric, Agentplane, or Model Governance Ledger.

## Remaining future work

A later integration tranche can add live cross-repo artifact fetching or pinned commit verification if the estate decides to promote this manifest from reference coordination to active multi-repo CI. This v0 tranche is intentionally coordination-only.
