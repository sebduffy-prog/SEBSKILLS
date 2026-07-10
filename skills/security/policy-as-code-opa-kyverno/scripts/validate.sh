#!/usr/bin/env bash
# validate.sh — CI gate for policy-as-code: format, compile, unit-test, then gate manifests.
# Usage: bash validate.sh <policy-dir> [manifests-dir-or-file ...]
# Exits non-zero on the first failure so it drops straight into CI.
set -euo pipefail

POLICY_DIR="${1:-policy}"
shift || true
MANIFESTS=("$@")

command -v opa >/dev/null || { echo "ERROR: opa not on PATH"; exit 127; }

echo "==> opa fmt (formatting check)"
opa fmt --fail --list "$POLICY_DIR"

echo "==> opa check (compile, strict)"
opa check --strict "$POLICY_DIR"

echo "==> opa test (unit tests + coverage)"
opa test "$POLICY_DIR" -c >/dev/null && opa test "$POLICY_DIR" -v

if [ "${#MANIFESTS[@]}" -gt 0 ]; then
  command -v conftest >/dev/null || { echo "ERROR: conftest not on PATH"; exit 127; }
  echo "==> conftest test (gate manifests)"
  conftest test -p "$POLICY_DIR" "${MANIFESTS[@]}"
fi

echo "==> ALL POLICY CHECKS PASSED"
