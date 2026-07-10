#!/usr/bin/env bash
# flake_scan.sh — language-agnostic flake detector.
# Runs a test command N times against the SAME code and reports the pass/fail
# ratio per run. A test that both passes and fails with no code change is flaky.
#
# Usage:   flake_scan.sh <RUNS> <command...>
# Example: flake_scan.sh 20 pytest tests/test_checkout.py::test_total
#          flake_scan.sh 15 npx jest --runInBand payment.test.ts
#
# Exit code: 0 if every run agreed (all pass OR all fail = deterministic),
#            1 if runs disagreed (FLAKY), 2 on bad usage.
set -u

if [ "$#" -lt 2 ]; then
  echo "usage: flake_scan.sh <RUNS> <command...>" >&2
  exit 2
fi

RUNS="$1"; shift
case "$RUNS" in ''|*[!0-9]*) echo "RUNS must be a positive integer" >&2; exit 2;; esac

pass=0; fail=0; log_dir="$(mktemp -d)"
echo "flake_scan: $RUNS runs of: $*"
echo "logs: $log_dir"

for i in $(seq 1 "$RUNS"); do
  if "$@" >"$log_dir/run_$i.log" 2>&1; then
    pass=$((pass+1)); printf 'run %2d: PASS\n' "$i"
  else
    fail=$((fail+1)); printf 'run %2d: FAIL (see %s/run_%d.log)\n' "$i" "$log_dir" "$i"
  fi
done

echo "----"
echo "pass=$pass fail=$fail of $RUNS"
if [ "$pass" -gt 0 ] && [ "$fail" -gt 0 ]; then
  echo "VERDICT: FLAKY (non-deterministic across identical code)"
  exit 1
fi
echo "VERDICT: DETERMINISTIC (all runs agreed)"
exit 0
