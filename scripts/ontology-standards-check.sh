#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-.}"

# Policy package must exist (vendored or linked)
if [[ ! -f "$REPO_ROOT/standards/ontology/obo/CHECKS.md" ]]; then
  echo "[FAIL] Missing standards/ontology/obo/CHECKS.md in $REPO_ROOT"
  exit 1
fi

echo "[OK] OBO policy package present in $REPO_ROOT"
