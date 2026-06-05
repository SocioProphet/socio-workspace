# Workspace Mesh Operator Checkpoint

Purpose: run the full safe local proof path and print a compact final status block.

## Command

```bash
cd ~/dev/sociosphere
git pull --ff-only
make workspace-mesh-operator-checkpoint
```

## What it runs

The target runs:

1. `workspace-mesh-topology-validate`
2. `terraform-workspace-mesh-plan-safe`
3. `workspace-mesh-gate1-generated-artifacts-review`
4. `tools/workspace_mesh_operator_checkpoint.py`

## Expected final block

```text
Workspace Mesh Operator Checkpoint
==================================
mesh_state=prepared-but-not-deployed
gate_0=complete
gate_1=reviewed_no_promotion
gate_2=planning_only
gate_2_disposition=not_started
plan_safety=passed
gate1_artifact_review=passed
artifact_review_source=plan_json
placeholders=4
ids_substituted=false
live_execution=false
next_allowed_action=gate_2_planning_record_only
```

## Boundary

This command is a validation and summary command. It does not write identifiers, apply infrastructure, push Apps Script, or execute Workspace automation.
