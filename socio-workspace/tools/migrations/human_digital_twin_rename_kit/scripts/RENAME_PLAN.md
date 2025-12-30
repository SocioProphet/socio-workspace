# Human Digital Twin — Rename Plan

This kit supports two modes.

## A) Slug-only rename (fast, safe)
- Rename the Git repo to **human-digital-twin** on your hosting platform.
- No code changes required. Keep internal folders as-is (e.g., `hdt_app_v1_0/`).
- Update documentation badges and container image names at your convenience.

## B) Full de-acronymization (folders & identifiers)
**Goal:** Replace `hdt` with `human digital twin` across the project.

**Directory renames (examples):**
- `HDT App v1.0/` → `human-digital-twin/` (top-level folder name)
- `hdt_app_v1_0/` → `human_digital_twin/` (code folder)

**Identifiers and text (recommend staged):**
- Human-readable: `HDT` → `Human Digital Twin`
- Python imports: `hdt_app_v1_0` → `human_digital_twin`
- K8s/labels: `app: hdt-api` → `app: human-digital-twin`
- Env vars (backward compatible): keep `HDT_*` working; add `HUMAN_DIGITAL_TWIN_*` aliases.

**Suggested order:**
1. Commit/branch.
2. Rename folders on disk.
3. Drop in the contents of this kit.
4. Run the dry-run script to preview replacements.
5. Apply replacements; run tests/pathflows.
6. Switch TritRPC shim to your hardened runtime.

## Dry-run & apply (search/replace)
```bash
python3 scripts/rename_dry_run.py /path/to/repo > RENAME_REPORT.txt
# review, then:
python3 scripts/rename_dry_run.py /path/to/repo --apply
```