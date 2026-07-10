#!/usr/bin/env bash
# contract_gate.sh — CI gate for a data contract.
# Lints the current contract, optionally runs data tests, and prints a
# categorised changelog (info / warning / error) against a baseline version.
# Fails (exit 1) when the changelog contains error-level = breaking changes.
#
# Usage:
#   scripts/contract_gate.sh <contract.yaml> [baseline.yaml]
#
# datacontract must be on PATH (see SKILL.md Prerequisites).
set -euo pipefail

CONTRACT="${1:?usage: contract_gate.sh <contract.yaml> [baseline.yaml]}"
BASELINE="${2:-}"

echo "== lint =="
datacontract lint "$CONTRACT"

if [[ -n "$BASELINE" && -f "$BASELINE" ]]; then
  echo "== changelog (${BASELINE} -> ${CONTRACT}) =="
  # Capture output; the changelog prints info/warning/error lines.
  OUT="$(datacontract changelog "$BASELINE" "$CONTRACT" 2>&1)" || true
  printf '%s\n' "$OUT"
  # Breaking = any error-level entry. Match case-insensitively on the word "error".
  if printf '%s\n' "$OUT" | grep -qiE '(^|[^a-z])error([^a-z]|$)'; then
    echo "BREAKING CHANGE detected — failing gate." >&2
    exit 1
  fi
  echo "No breaking changes."
else
  echo "No baseline supplied — skipping changelog (first version or new contract)."
fi

echo "Gate passed."
