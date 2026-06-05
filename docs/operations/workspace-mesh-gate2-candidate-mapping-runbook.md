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

The repository also contains a validator:

```text
tools/validate_workspace_mesh_gate2_candidate_template.py
```

## Local-only file path

If a future operator needs to prepare candidate values for review, copy the template to:

```text
.workspace-mesh/gate2-candidate-mapping.local.json
```

That local path is ignored by Git.

## Validation commands

Because the standalone make fragment may not always be included by the root wrapper, either command is acceptable:

```bash
make -f workspace-mesh-gate2-candidate.mk workspace-mesh-gate2-candidate-template-validate
```

or:

```bash
python3 tools/validate_workspace_mesh_gate2_candidate_template.py
```

Expected output:

```text
PASS: Workspace mesh Gate 2 candidate mapping template is placeholder-only
placeholders=4
local_mapping_paths_ignored=true
```

## Local copy command

```bash
mkdir -p .workspace-mesh
cp templates/workspace-mesh/gate2-candidate-mapping.template.json .workspace-mesh/gate2-candidate-mapping.local.json
```

Do not commit `.workspace-mesh/gate2-candidate-mapping.local.json`.

## Boundary

The template does not substitute identifiers, write repository configuration, execute scripts, schedule automation, or promote the mesh beyond planning.
