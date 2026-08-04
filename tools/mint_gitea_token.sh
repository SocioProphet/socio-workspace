#!/usr/bin/env bash
# Mint a short-lived Gitea access token, in CI, without storing one anywhere.
#
# There is no Gitea credential to hand out and none should exist. Gitea's admin lives in
# its own SQLite database on a PVC; `kubectl get secrets -n scm` is EMPTY. So the token
# is not fetched, it is GENERATED on demand inside the cluster and revoked when the job
# ends. Nothing is at rest, so nothing can leak from rest.
#
# Verified 2026-08-04 against gitea 1.27.1 in scm/gitea:
#
#   gitea admin user generate-access-token --username estate-mirror --raw
#
# Two constraints discovered the hard way, both of which shape this script:
#
#   1. The container refuses to run gitea as root ("Gitea is not supposed to be run as
#      root"), so every CLI call must go through `su git -c`.
#   2. Gitea's CLI has NO token-delete command, and the REST token endpoints require
#      BASIC auth -- a token cannot revoke itself or any other token (401 "auth
#      required"). Revocation therefore goes through the database, which is what the
#      API would do anyway. Deleting the access_token row IS revocation.
#
# Because revocation is awkward, the trap is unconditional. A run that dies between mint
# and revoke would otherwise leave a live admin-scoped credential on a service account
# with nobody aware it exists -- which is exactly what happened while working this out,
# and took a DB delete to clean up.

set -euo pipefail

NS="${GITEA_NAMESPACE:-scm}"
USER="${GITEA_CI_USER:-estate-mirror}"
SCOPES="${GITEA_SCOPES:-read:repository,read:issue,write:issue}"
NAME="ci-$(date +%s)-${RANDOM}"

pod() {
  kubectl get pod -n "$NS" -l app=gitea -o name 2>/dev/null | head -1 | sed 's|pod/||' \
    || kubectl get pod -n "$NS" -o name | head -1 | sed 's|pod/||'
}

POD="$(pod)"
if [ -z "$POD" ]; then
  echo "no gitea pod in namespace '$NS'" >&2
  exit 1
fi

revoke() {
  # Never conditional on success of the work. See the header.
  kubectl exec -n "$NS" "$POD" -- su git -c \
    "sqlite3 /data/gitea/gitea.db \"delete from access_token where name = '${NAME}';\"" \
    >/dev/null 2>&1 || echo "WARNING: could not revoke ${NAME} — revoke it by hand" >&2
}
trap revoke EXIT INT TERM

TOKEN="$(kubectl exec -n "$NS" "$POD" -- su git -c \
  "gitea admin user generate-access-token --username ${USER} --token-name ${NAME} --scopes ${SCOPES} --raw" \
  2>/dev/null | tr -d '\r\n')"

if [ -z "$TOKEN" ]; then
  echo "mint failed for user '${USER}' in ${NS}/${POD}" >&2
  exit 1
fi

# Mask before anything can echo it into a log.
echo "::add-mask::${TOKEN}"

kubectl port-forward -n "$NS" svc/gitea "${GITEA_PORT:-3111}:3000" >/dev/null 2>&1 &
PF=$!
trap 'kill $PF 2>/dev/null || true; revoke' EXIT INT TERM
sleep 5

export GITEA_URL="http://localhost:${GITEA_PORT:-3111}"
export GITEA_TOKEN="$TOKEN"
export SCM_BACKEND=gitea

# Whatever the caller wants done with the token, done while it exists.
if [ "$#" -gt 0 ]; then
  "$@"
else
  # Default: prove the credential works and report the mirror direction, which is the
  # fact that decides whether sovereign can be canonical yet.
  echo "gitea: $(curl -s -H "Authorization: token ${TOKEN}" "${GITEA_URL}/api/v1/version")"
  curl -s -H "Authorization: token ${TOKEN}" \
    "${GITEA_URL}/api/v1/repos/search?q=&limit=50" |
    python3 -c '
import json, sys
d = json.load(sys.stdin)
repos = d.get("data", [])
mirrors = [r for r in repos if r.get("mirror")]
print(f"repos visible: {len(repos)}, pull-mirrors: {len(mirrors)}")
if mirrors:
    print("PULL MIRRORS ARE READ-ONLY — sovereign cannot be canonical until these are")
    print("flipped to push-mirrors. A push returns 403 'mirror repository is read-only'.")
'
fi
