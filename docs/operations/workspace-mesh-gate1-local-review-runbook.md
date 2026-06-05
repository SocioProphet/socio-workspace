# Gate 1 Local Generated Artifact Review Runbook

Status: `not_started`
Mesh state: `prepared-but-not-deployed`

## Purpose

This runbook reviews generated local artifacts after the default plan-safety command creates them. It does not mark Gate 1 complete and does not authorize deployment.

## Safe command sequence

```bash
cd ~/dev/sociosphere
git pull --ff-only
make workspace-mesh-topology-validate
make terraform-workspace-mesh-plan-safe
make workspace-mesh-gate1-generated-artifacts-review
```

## Expected generated-artifact review output

```text
PASS: Workspace mesh Gate 1 generated artifacts review clean
generated_dir=...
artifacts=4
review_performed=false
promotion_authorized=false
```

## What the local review checks

The local review checks four generated artifacts in the fabric repo:

```text
config.generated.json
clasp.generated.json
mesh-summary.generated.json
operator-next-steps.md
```

It verifies:

- `dryRun` remains `true`,
- `spreadsheetId` remains `TODO_GOOGLE_SHEET_ID`,
- `scriptId` remains `TODO_APPS_SCRIPT_PROJECT_ID`,
- calendar IDs remain TODO placeholders,
- project services remain disabled,
- Workspace groups remain disabled,
- required metadata fields remain present,
- expected Apps Script files are listed,
- generated instructions do not authorize deployment,
- and no obvious secret markers appear.

## Boundary

This command does not authorize:

- ID substitution,
- `tofu apply`,
- `clasp push`,
- Apps Script execution,
- scheduled triggers,
- live calendar access,
- Workspace group creation,
- dashboard creation,
- production data processing,
- or native SocioProphet migration.

Gate 1 remains `not_started` until a separate dated review proof is recorded.
