#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/apps/ui-workbench"
UIKIT="$ROOT/packages/ui-kit/src/TrustBadge.vue"

fail() { echo "ERR: $*" >&2; exit 2; }
ok() { echo "OK: $*"; }

# --- structure checks
test -d "$APP" || fail "missing apps/ui-workbench"
test -f "$UIKIT" || fail "missing packages/ui-kit/src/TrustBadge.vue"

req_files=(
  "$APP/src/router/index.ts"
  "$APP/src/routes/SearchResultsPage.vue"
  "$APP/src/components/search/ResultCard.vue"
  "$APP/src/api/search.ts"
  "$APP/src/schemas/search.ts"
)

for f in "${req_files[@]}"; do
  test -f "$f" || fail "missing required file: ${f#$ROOT/}"
done
ok "required files present"

# --- toolchain checks
command -v node >/dev/null 2>&1 || fail "node not found"
command -v npm  >/dev/null 2>&1 || fail "npm not found"
ok "node+npm present"

test -f "$APP/package.json" || fail "missing apps/ui-workbench/package.json"

# Ensure deps installed
if [ ! -d "$APP/node_modules" ]; then
  fail "node_modules missing; run: (cd apps/ui-workbench && npm install)"
fi
ok "node_modules present"

# vue-tsc must exist because build script calls it
test -x "$APP/node_modules/.bin/vue-tsc" || fail "vue-tsc missing; run: (cd apps/ui-workbench && npm install -D vue-tsc typescript)"
ok "vue-tsc present"

# Zod major must be v4 because our schemas use v4 record signature
ZOD_VER="$(node -p "require('$APP/node_modules/zod/package.json').version" 2>/dev/null || true)"
test -n "${ZOD_VER:-}" || fail "zod not installed; run: (cd apps/ui-workbench && npm install zod)"
ZOD_MAJOR="${ZOD_VER%%.*}"
test "$ZOD_MAJOR" = "4" || fail "zod major mismatch (found $ZOD_VER, expected 4.x); fix deps or adjust schema code"
ok "zod major OK ($ZOD_VER)"

# Vite must be able to import from ../../packages (monorepo-style)
test -f "$APP/vite.config.ts" || fail "missing apps/ui-workbench/vite.config.ts"
grep -q "@ui-kit" "$APP/vite.config.ts" || fail "vite alias @ui-kit missing in apps/ui-workbench/vite.config.ts"
ok "vite alias @ui-kit present"

echo "OK: ui-preflight passed"
