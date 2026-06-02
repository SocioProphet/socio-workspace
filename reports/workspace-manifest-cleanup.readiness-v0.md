# Workspace manifest cleanup readiness report v0

Source umbrella issue: #439

Related disposition issues:

- #451 — pins, aliases, and stale refs
- #452 — connector and service manifest entries
- #453 — documentation and support manifest entries

Status: readiness report only. This file does not change `manifest/workspace.toml`.

## Current conclusion

The full-estate resolved lock work exposed inventory drift rather than a simple SHA-resolution problem.

The resolver, coverage reporter, baseline reports, batch reports, and disposition reports are now in place. What remains is not more blind lookup. What remains is a controlled manifest reconciliation pass.

## Do not touch yet

These entries require explicit owner or architecture confirmation before any manifest mutation.

### Pinned protocol / component dependencies

- `tritfabric`
- `tritrpc`

Reason: both are intentionally pinned in the manifest and drift from current `main`. Pins should remain frozen unless a dedicated pin-bump review approves a target revision.

### Alias / canonicalization candidates

- `hdt_app`
- `human_digital_twin`

Reason: `human_digital_twin` resolves and appears canonical. `hdt_app` does not resolve, but it must not be removed until confirmed as stale, private, planned, or merged.

### Ref anomaly

- `knowledge-graph`

Reason: the lookup reached a ref-level error rather than a simple repository 404. The correct branch/ref needs verification before changing the manifest.

### Connector/service planned stubs

- `connector-github`
- `connector-gitlab`
- `connector-jira`
- `connector-kafka`
- `connector-slack`
- `configs`
- `dev_api`
- `asr-service`
- `embeddings-service`
- `event-bus`
- `data-pipeline`

Reason: these may be planned repos, stale placeholders, private repos, or merged surfaces. `data-pipeline` has adjacent but unconfirmed candidates, including `datakit` and `argo-dataflow`.

### Documentation/support stale candidates

- `socioprophet_integration`
- `runbooks`
- `onboarding-docs`
- `architecture-docs`
- `api-specs`

Reason: these appear stale or uncreated, but cleanup requires inbound-reference checks and confirmation of canonical documentation location.

## Candidate cleanup PR sequence

### PR 1 — Add inventory disposition metadata only

Purpose:

- Add machine-readable disposition metadata without removing manifest entries.
- Mark unresolved entries as one of: planned, stale, private, merged, renamed, archival, pending_confirmation.

Risk: low.

Required validation:

- existing manifest parser still passes;
- coverage report still shows current state;
- no resolved-lock claims are upgraded.

### PR 2 — Resolve confirmed aliases and stale docs

Purpose:

- Remove or replace only entries whose disposition has been confirmed.
- Likely candidates: docs/support entries that are proven consolidated into active documentation surfaces.

Risk: medium.

Required validation:

- inbound-reference scan;
- manifest diff rationale per entry;
- regenerated coverage report;
- regenerated resolved lock.

### PR 3 — Ref and pin reconciliation

Purpose:

- Handle `knowledge-graph` branch/ref correction.
- Handle any approved `tritfabric` or `tritrpc` pin movement.

Risk: high.

Required validation:

- explicit pin/ref review;
- compatibility notes;
- regenerated resolved lock;
- #451 updated with final disposition.

### PR 4 — Full-estate resolved lock regeneration

Purpose:

- Regenerate `manifest/workspace.resolved.lock.json` against the reconciled manifest.
- Update coverage from partial to the correct final status.

Risk: medium.

Required validation:

- every declared repo has a resolution status;
- unresolved/skipped entries include explicit disposition metadata;
- no silent drops.

## Exit criteria for #439

#439 can close only when:

1. #451, #452, and #453 have final dispositions.
2. Approved manifest cleanup PRs are merged.
3. `manifest/workspace.resolved.lock.json` is regenerated from the reconciled manifest.
4. Coverage report reflects the final estate state.
5. Remaining unresolved entries, if any, are explicitly intentional and documented.

## Current recommended next action

Open PR 1: add inventory disposition metadata only.

Do not delete, rename, or repin manifest entries in PR 1. The first cleanup PR should establish durable metadata and validation posture before changing inventory semantics.
