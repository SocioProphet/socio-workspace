#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-$HOME/dev}"
cd "$BASE"

ROOT="$(
  (ls -d sociosphere-main 2>/dev/null || true
   ls -d sociosphere 2>/dev/null || true
   ls -d sociosphere-* 2>/dev/null || true) | head -n 1
)"
test -n "${ROOT:-}" || { echo "ERR: no sociosphere* directory found under $BASE" >&2; exit 2; }
echo "$BASE/$ROOT"
