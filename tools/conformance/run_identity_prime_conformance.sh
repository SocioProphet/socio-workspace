#!/usr/bin/env bash
# Aggregate runner for the Identity-Prime conformance lane.
# Runs every Identity-Prime / HELL-ER / Regis / extraction / masking / audience validator
# in one shot. Exit 0 only if all pass. Intended for local use and as the command a
# CI step should invoke (see docs/architecture/identity-prime-gap-register.md P0 #1).
set -u
cd "$(dirname "$0")" || exit 2

VALIDATORS=(
  validate_identity_is_prime_fixtures.py
  validate_hell_er_fixtures.py
  validate_hell_er_negative_fixtures.py
  validate_er_plus_workspace.py
  validate_regis_extract_masking_fixtures.py
)

fail=0
for v in "${VALIDATORS[@]}"; do
  if [[ ! -f "$v" ]]; then
    printf '  SKIP  %s (not found)\n' "$v"; continue
  fi
  if python3 "$v" >/tmp/ip_conf_out 2>&1; then
    printf '  PASS  %s\n' "$v"
  else
    printf '  FAIL  %s\n' "$v"; sed 's/^/        /' /tmp/ip_conf_out; fail=1
  fi
done

if [[ $fail -ne 0 ]]; then
  echo "identity-prime conformance: FAIL"; exit 1
fi
echo "identity-prime conformance: ALL PASS"
