# Exodus Migration Workroom demo integration v0

Related issue: #478

Status: report-only integration artifact. This file does not change workspace manifest membership, pins, refs, resolved-lock state, provider credentials, or runtime behavior.

## Purpose

This report records the first cross-repo proof path for the governed Exodus Migration Workroom demo.

The demo connects three repositories:

- `SocioProphet/exodus`
- `SocioProphet/prophet-workspace`
- `SocioProphet/sociosphere`

The purpose is to show that Exodus, Prophet Workspace, and Sociosphere now have a durable synthetic demo chain:

1. Exodus supplies a synthetic Apple/Google/Microsoft exit-readiness run.
2. Prophet Workspace carries that run inside a Professional Workroom through a thin bridge.
3. Sociosphere records the integration as control-plane state and keeps the proof boundary explicit.

## Current merged artifacts

### Exodus

Repository: `SocioProphet/exodus`

Merged PR: `SocioProphet/exodus#18`

Merge commit: `65215b83ed7fd67d210acaecae125baace0866af`

Artifacts:

- `schemas/exodus-run.v0.schema.json`
- `examples/synthetic-tenant-a/exodus-run.json`
- `scripts/validate_exodus_demo.py`
- `.github/workflows/ci.yml`
- `docs/synthetic-workroom-demo.md`

Exodus proves that a deterministic synthetic run can represent:

- Apple, Google, and Microsoft provider topology;
- account and root inventory;
- asset census by provider and domain;
- export ledger and evidence references;
- ERI score;
- PCS-by-provider scores;
- blockers;
- recommendations;
- Phase 2 budget proposal.

### Prophet Workspace

Repository: `SocioProphet/prophet-workspace`

Merged PR: `SocioProphet/prophet-workspace#20`

Merge commit: `9869c0932358ad0502b2b83f21479d050455f7de`

Artifacts:

- `contracts/workspace/exodus-workroom-bridge.schema.json`
- `contracts/workspace/exodus-workroom-bridge.v0.1.example.json`
- `contracts/workspace/exodus-migration-workroom.v0.1.example.json`
- `tools/validate_professional_workrooms.py`
- `docs/exodus-migration-workroom.md`

Prophet Workspace proves that a `ProfessionalWorkroom` can carry the Exodus run without forking the core workroom model.

The bridge binds:

- Exodus run ref;
- provider topology refs;
- account root refs;
- asset census refs;
- export ledger refs;
- score refs;
- blocker refs;
- recommendation refs;
- budget proposal ref;
- office artifact refs;
- evidence refs;
- policy refs;
- Sociosphere control-plane refs.

### Sociosphere

Repository: `SocioProphet/sociosphere`

Current integration artifact:

- `reports/exodus-workroom-demo.integration-v0.md`

Existing control-plane artifacts that this report relies on:

- `docs/workspace-session-resume.md`
- `reports/workspace-control-plane-context-integration.md`
- `reports/workspace-disposition-summary.baseline.json`
- `manifest/workspace.dispositions.json`
- `reports/workspace-manifest-cleanup.readiness-v0.md`
- `reports/workspace-manifest-cleanup.readiness-v0.json`

Sociosphere proves the governance wrapper:

- durable state first;
- no reliance on conversation memory;
- explicit separation between declared, observed, disposition, summary, and integration state;
- branch-first GitOps;
- no full-estate or production-readiness overclaim.

## Control-plane mapping

| Layer | Demo artifact | Repository | Status |
|---|---|---|---|
| Domain run | `examples/synthetic-tenant-a/exodus-run.json` | `exodus` | merged |
| Domain schema | `schemas/exodus-run.v0.schema.json` | `exodus` | merged |
| Domain validator | `scripts/validate_exodus_demo.py` | `exodus` | merged |
| Workspace containment | `contracts/workspace/exodus-migration-workroom.v0.1.example.json` | `prophet-workspace` | merged |
| Workspace bridge | `contracts/workspace/exodus-workroom-bridge.v0.1.example.json` | `prophet-workspace` | merged |
| Workspace validator | `tools/validate_professional_workrooms.py` | `prophet-workspace` | merged |
| Control-plane integration | `reports/exodus-workroom-demo.integration-v0.md` | `sociosphere` | this PR |

## Demo claim now supported

The following claim is supported after this report lands:

A synthetic Exodus exit-readiness run can be represented as a Prophet Workspace Professional Workroom and governed by Sociosphere as durable control-plane state.

This is an internal synthetic demo claim only.

## Explicit non-claims

This demo does not prove:

- real Apple, Google, or Microsoft credential ingestion;
- live provider API operation;
- provider-side writes;
- destructive migration behavior;
- production migration readiness;
- polished UI readiness;
- full-estate workspace resolved-lock completion.

## Validation commands

Run in `SocioProphet/exodus`:

```bash
python3 scripts/validate_exodus_demo.py
```

Run in `SocioProphet/prophet-workspace`:

```bash
python3 tools/validate_professional_workrooms.py
```

Run in `SocioProphet/sociosphere`:

```bash
python3 tools/validate_workspace_dispositions.py
python3 tools/report_workspace_disposition_summary.py
```

## Next required work

The demo is not yet a one-command cross-repo validation. The next tranche should add one of:

1. A documented cross-repo runbook with expected checkout paths.
2. A Sociosphere cross-repo readiness script that checks the known merged artifact paths in sibling repositories.
3. A workspace profile that declares the three-repo demo bundle.

Recommended next step: add a Sociosphere cross-repo readiness script with path overrides and default `~/dev/<repo>` assumptions.

## Risk boundary

This report is safe to merge if it remains report-only.

It must not be combined with:

- workspace manifest membership edits;
- pin or ref movement;
- resolved-lock regeneration;
- provider credential collection;
- runtime connector activation;
- production migration claims.
