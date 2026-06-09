# Exodus Migration Workroom demo runbook

Status: synthetic internal demo runbook.

Related issue: `SocioProphet/sociosphere#478`.

## Purpose

This runbook gives the local validation path for the synthetic Exodus Migration Workroom demo.

The demo links three merged repository lanes:

1. `SocioProphet/exodus` — synthetic Apple/Google/Microsoft exit-readiness run.
2. `SocioProphet/prophet-workspace` — Professional Workroom containment and Exodus bridge.
3. `SocioProphet/sociosphere` — control-plane integration record and readiness checker.

## Boundary

This is a synthetic, offline, internal demo.

It does not require or use:

- real provider credentials;
- live Apple, Google, or Microsoft API calls;
- provider-side writes;
- destructive actions;
- production migration execution;
- polished UI readiness.

## Expected checkout layout

Default paths:

```bash
~/dev/exodus
~/dev/prophet-workspace
~/dev/sociosphere
```

The checker supports path overrides, so the repos may be elsewhere.

## Quick check: artifact presence only

From `~/dev/sociosphere`:

```bash
python3 tools/check_exodus_workroom_demo.py
```

This verifies that the expected merged artifacts exist in all three repositories.

## Full local check: run validators

From `~/dev/sociosphere`:

```bash
python3 tools/check_exodus_workroom_demo.py --run-validators
```

This runs:

```bash
cd ~/dev/exodus && python3 scripts/validate_exodus_demo.py
cd ~/dev/prophet-workspace && python3 tools/validate_professional_workrooms.py
cd ~/dev/sociosphere && python3 tools/validate_workspace_dispositions.py
cd ~/dev/sociosphere && python3 tools/report_workspace_disposition_summary.py
```

## Path overrides

```bash
python3 tools/check_exodus_workroom_demo.py \
  --exodus /path/to/exodus \
  --prophet-workspace /path/to/prophet-workspace \
  --sociosphere /path/to/sociosphere \
  --run-validators
```

## JSON output

```bash
python3 tools/check_exodus_workroom_demo.py --run-validators --json
```

The output schema is:

```text
sociosphere.exodus-workroom-demo-readiness.v0
```

## Expected readiness claim

If the checker returns `ready`, the following synthetic demo claim is supported:

A synthetic Exodus exit-readiness run can be represented as a Prophet Workspace Professional Workroom and governed by Sociosphere as durable control-plane state.

## Expected artifacts checked

### Exodus

- `schemas/exodus-run.v0.schema.json`
- `examples/synthetic-tenant-a/exodus-run.json`
- `scripts/validate_exodus_demo.py`
- `.github/workflows/ci.yml`
- `docs/synthetic-workroom-demo.md`

### Prophet Workspace

- `contracts/workspace/exodus-workroom-bridge.schema.json`
- `contracts/workspace/exodus-workroom-bridge.v0.1.example.json`
- `contracts/workspace/exodus-migration-workroom.v0.1.example.json`
- `tools/validate_professional_workrooms.py`
- `docs/exodus-migration-workroom.md`

### Sociosphere

- `reports/exodus-workroom-demo.integration-v0.md`
- `reports/exodus-workroom-demo.integration-v0.json`
- `docs/workspace-session-resume.md`
- `reports/workspace-control-plane-context-integration.md`
- `reports/workspace-disposition-summary.baseline.json`
- `manifest/workspace.dispositions.json`
- `reports/workspace-manifest-cleanup.readiness-v0.md`
- `reports/workspace-manifest-cleanup.readiness-v0.json`
- `tools/validate_workspace_dispositions.py`
- `tools/report_workspace_disposition_summary.py`

## Troubleshooting

If a repository path is missing, clone or move the repo into the expected checkout layout, or use a path override.

If an artifact is missing, ensure the relevant PR has been merged and the local checkout is current.

If a validator fails, inspect the repo-local validator output first. Do not change Sociosphere integration claims until the underlying Exodus or Prophet Workspace artifact is corrected.

## Stop conditions

Stop and review before making any change that would:

- collect provider credentials;
- call provider APIs;
- write to provider accounts;
- perform destructive operations;
- edit workspace manifest membership;
- move pins or refs;
- regenerate the full workspace resolved lock;
- claim production migration readiness.

## Next step after readiness passes

Produce the final demo proof package:

- proof matrix;
- claim matrix;
- non-claim matrix;
- next-sprint backlog for real-provider readiness and UI demonstration.
