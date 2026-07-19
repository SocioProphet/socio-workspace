#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

die(){ echo "ERR: $*" 1>&2; exit 2; }
ok(){ echo "OK: $*"; }

# We assume we are inside sociosphere repo.
[ -f "manifest/workspace.toml" ] || die "run from sociosphere repo root (manifest/workspace.toml missing)"
[ -f "tools/runner/runner.py" ] || die "tools/runner/runner.py missing"

# Spine repo locations (materialized by fetcher)
SOURCEOS="components/sourceos"
TRITRPC="components/tritrpc"
STD_STORAGE="components/standards/storage"
STD_KNOWLEDGE="components/standards/knowledge"
AGENTPLANE="components/agentplane"
TRITFABRIC="components/tritfabric"
AI4IT="components/global-devsecops-intelligence"

missing=0
for p in "$SOURCEOS" "$TRITRPC" "$STD_STORAGE" "$STD_KNOWLEDGE" "$AGENTPLANE" "$TRITFABRIC" "$AI4IT"; do
  if [ ! -d "$p" ]; then
    echo "WARN: missing component path: $p (materialize with runner fetch or manual clone)"
    missing=1
  fi
done

run_task(){
  local path="$1"
  local task="$2"
  if [ -f "$path/Makefile" ]; then
    (cd "$path" && make "$task") || return 1
    return 0
  fi
  if [ -f "$path/scripts/$task.sh" ]; then
    (cd "$path" && bash "scripts/$task.sh") || return 1
    return 0
  fi
  echo "WARN: no task contract for $path ($task)"
  return 0
}

rc=0

[ -d "$SOURCEOS" ] && run_task "$SOURCEOS" validate || rc=2
[ -d "$STD_STORAGE" ] && run_task "$STD_STORAGE" validate || rc=2
[ -d "$STD_KNOWLEDGE" ] && run_task "$STD_KNOWLEDGE" validate || rc=2

if [ -d "$TRITRPC" ]; then
  if [ -f "$TRITRPC/Makefile" ] && grep -q "^verify:" "$TRITRPC/Makefile"; then
    run_task "$TRITRPC" verify || rc=2
  else
    run_task "$TRITRPC" validate || rc=2
  fi
fi

[ -d "$AGENTPLANE" ] && run_task "$AGENTPLANE" validate || rc=2
[ -d "$TRITFABRIC" ] && run_task "$TRITFABRIC" test || true
[ -d "$AI4IT" ] && run_task "$AI4IT" validate || rc=2

if [ -d "$STD_KNOWLEDGE" ] && [ -d "$TRITRPC" ] && [ -d "$TRITRPC/.git" ]; then
  pinned="$(grep -RIn "Pinned commit:" "$STD_KNOWLEDGE/docs/standards" 2>/dev/null | head -n 1 | sed -E 's/.*Pinned commit: *([0-9a-f]{7,40}).*/\1/')"
  if [ -n "$pinned" ] && [ -d "$TRITRPC/.git" ]; then
    headrev="$(cd "$TRITRPC" && git rev-parse HEAD)"
    if [ "$headrev" != "$pinned" ]; then
      echo "ERR: standards pin mismatch: knowledge standard pins TriTRPC=$pinned but workspace has $headrev"
      echo "     Fix by updating the pin in standards OR pinning workspace.lock.json to the referenced commit."
      rc=2
    else
      ok "TriTRPC pin matches standards ($pinned)"
    fi
  else
    echo "WARN: could not find 'Pinned commit:' line in knowledge standards, skipping pin check"
  fi
fi

if [ -d "$SOURCEOS/caps/semantic-search-bi" ] && [ -d "caps/semantic-search-bi" ]; then
  diff -ru "$SOURCEOS/caps/semantic-search-bi" "caps/semantic-search-bi" >/dev/null || {
    echo "ERR: semantic-search-bi contract drift between SourceOS and sociosphere caps/"
    echo "     Policy: pick one canonical contract package and mirror/generate the other."
    rc=2
  }
fi

if [ "$missing" = "1" ]; then
  echo "WARN: one or more spine repos missing; validate was partial."
fi

if [ "$rc" != "0" ]; then
  exit "$rc"
fi

ok "spine validate passed"
