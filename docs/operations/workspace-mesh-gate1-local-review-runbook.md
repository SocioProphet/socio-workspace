# Gate 1 Local Generated Artifact Review Runbook

Status: `not_started`
Mesh state: `prepared-but-not-deployed`

## Purpose

This runbook reviews the four local artifacts represented by the default plan-safety command. Because `tofu plan -out` does not create `local_file` outputs, the inspector reads real generated files only if they already exist. In the normal no-apply workflow, it reads the planned `local_file` contents from `default-plan.json`.

It does not mark Gate 1 complete and does not authorize deployment.

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
source=plan_json
generated_dir=...
artifacts=4
review_performed=false
promotion_authorized=false
```

If the generated files exist because a prior local-file-only apply was deliberately performed, `source` may be `generated_files`. The normal prepared-but-not-deployed path should use `source=plan_json`.

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
