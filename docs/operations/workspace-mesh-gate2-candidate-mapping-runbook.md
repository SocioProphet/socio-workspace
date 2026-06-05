# Workspace Mesh Gate 2 Candidate Mapping Template Runbook

Mesh state: `prepared-but-not-deployed`
Gate 2 state: `planning_only`

## Purpose

This runbook defines the local-only candidate mapping workflow for Gate 2. It keeps the versioned repository free of real identifier values.

## Versioned files

The repository contains only a placeholder template:

```text
templates/workspace-mesh/gate2-candidate-mapping.template.json
```

The repository also contains validators and a local-file helper:

```text
tools/validate_workspace_mesh_gate2_candidate_template.py
tools/create_workspace_mesh_gate2_local_candidate_mapping.py
```

## Local-only file path

If a future operator needs to prepare candidate values for review, the helper creates:

```text
.workspace-mesh/gate2-candidate-mapping.local.json
```

That local path is ignored by Git.

## Validation command

```bash
make -f workspace-mesh-gate2-candidate.mk workspace-mesh-gate2-candidate-template-validate
```

Expected output:

```text
PASS: Workspace mesh Gate 2 candidate mapping template is placeholder-only
placeholders=4
local_mapping_paths_ignored=true
```

## Local helper command

```bash
make -f workspace-mesh-gate2-candidate.mk workspace-mesh-gate2-local-candidate-create
```

Expected output:

```text
PASS: Workspace mesh Gate 2 local candidate mapping file created
local_file=.workspace-mesh/gate2-candidate-mapping.local.json
placeholder_copy=true
git_ignored=true
ids_substituted=false
```

If the local file already exists and should be reset to the placeholder template:

```bash
make -f workspace-mesh-gate2-candidate.mk workspace-mesh-gate2-local-candidate-create-force
```

Do not commit `.workspace-mesh/gate2-candidate-mapping.local.json`.

## Boundary

The template and helper do not substitute identifiers, write repository configuration, execute scripts, schedule automation, or promote the mesh beyond planning.
