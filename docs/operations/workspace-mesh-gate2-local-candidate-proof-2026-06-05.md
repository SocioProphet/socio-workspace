# Workspace Mesh Gate 2 Local Candidate Helper Proof — 2026-06-05

Mesh state: `prepared-but-not-deployed`
Gate 2 state: `planning_only`
Local candidate state: `placeholder_copy`

## Commands proven

```bash
cd ~/dev/sociosphere
git pull --ff-only
make -f workspace-mesh-gate2-candidate.mk workspace-mesh-gate2-candidate-template-validate
make -f workspace-mesh-gate2-candidate.mk workspace-mesh-gate2-local-candidate-create
make -f workspace-mesh-gate2-candidate.mk workspace-mesh-gate2-local-candidate-create-force
```

## Observed behavior

The template validator passed:

```text
PASS: Workspace mesh Gate 2 candidate mapping template is placeholder-only
placeholders=4
local_mapping_paths_ignored=true
```

The non-force create command correctly refused to overwrite an existing local candidate file:

```text
FAIL: local candidate mapping already exists: .workspace-mesh/gate2-candidate-mapping.local.json; rerun with --force to replace it
```

The force create command then reset the local file to the placeholder template and verified that it remains ignored by Git:

```text
PASS: Workspace mesh Gate 2 local candidate mapping file created
local_file=.workspace-mesh/gate2-candidate-mapping.local.json
placeholder_copy=true
git_ignored=true
ids_substituted=false
```

## Local file

```text
.workspace-mesh/gate2-candidate-mapping.local.json
```

This file is local-only and intentionally ignored by Git.

## Safety interpretation

The helper behaved correctly in both cases:

1. It refused accidental overwrite without `--force`.
2. It allowed an intentional reset with `--force`.
3. It preserved placeholder-only values.
4. It confirmed the file is ignored by Git.
5. It confirmed no identifiers were substituted.

## Boundary

This proof does not start ID substitution, does not start Gate 3, does not execute Workspace automation, and does not change the prepared-but-not-deployed mesh state.
