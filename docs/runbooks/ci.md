# CI runbook

## Workflows

| File | Trigger | What it does |
|------|---------|-------------|
| `.github/workflows/validate.yml` | push, PR | Runner smoke + lock-verify + topology + UI + standards |
| `.github/workflows/ui-check.yml` | push, PR | UI install + build only |
| `.github/workflows/personal-intelligence-cell-social-standards.yml` | push, PR (path-filtered) | Validates Personal Intelligence Cell social-environment and reputation standards examples/schemas |

## Steps in `validate.yml`

### Runner smoke test
```bash
python3 tools/runner/runner.py list
```
Reads `manifest/workspace.toml` and `manifest/workspace.lock.json`. Prints every repo with its
materialization status. Fails if either file is malformed.

### Lock verify
```bash
python3 tools/runner/runner.py lock-verify
# or: make lock-verify
```
Checks structural consistency between manifest and lock. Fails if:
- Any manifest repo is missing from the lock.
- Any remote repo has a null `rev` in the lock.
- Any stale entry exists in the lock.
- Any materialized git repo has drifted from its locked revision.

### Topology check
```bash
python3 tools/check_topology.py
# or: make topology-check
```
Enforces dependency-direction rules. See `docs/architecture/validation-contract.md`.

### UI check
```bash
make ui-check
```
Runs TypeScript compilation and Vite production build for `apps/ui-workbench`.

### Standards validation
```bash
make validate-standards
```
Validates adaptation program JSON and QES schemas.

### Personal Intelligence Cell social/reputation standards
```bash
python3 tools/validate_personal_intelligence_cell_social_environment.py
```
Validates the snapshot and reputation schemas/examples, including confidence interval and anti-manipulation constraints.

## How to fix common failures

### `MISSING-FROM-LOCK <repo>`
A repo was added to `manifest/workspace.toml` without updating the lock.
Fix: materialize the repo with `make lock-update` (requires `runner fetch` first),
or manually add the entry to `manifest/workspace.lock.json`.

### `UNPINNED <repo>`
A repo has a GitHub URL in the manifest but `rev` is null in the lock.
Fix: run `python3 tools/runner/runner.py lock-update` after `runner fetch`.

### `DRIFT <repo>: HEAD=X lock=Y`
A materialized repo has been advanced past its locked revision locally.
Fix: either update the lock with `lock-update`, or check out the locked rev with
`git checkout <lock-rev>` inside the component directory.

### `STALE <repo>`
An entry exists in the lock that is no longer in the manifest.
Fix: remove the stale entry from `manifest/workspace.lock.json`.

### `SUBMODULE-PATH <name>`
A submodule is registered outside `third_party/`. Fix: move the submodule path.

### `UNPINNED-THIRD-PARTY <name>`
A `role=third_party` entry has no `rev` in the lock. Fix: add an explicit rev.

## Bumping a pinned revision

1. Update the `rev` field in `manifest/workspace.lock.json` with the new SHA.
2. If the repo is also a git submodule, update the submodule:
   ```bash
   git -C third_party/<name> checkout <new-sha>
   git add third_party/<name>
   ```
3. Commit both changes together with a short rationale and a link to the relevant issue.
4. Push; CI will re-run `lock-verify` to confirm the update is consistent.
