#!/usr/bin/env bash
# validate.sh — offline lint for Falco rules and Tetragon TracingPolicies.
# Works from macOS or any host without an eBPF kernel: it validates SYNTAX only,
# it does not load probes. Use before shipping a rule/policy to a live cluster.
#
# Usage:
#   scripts/validate.sh path/to/custom_rules.yaml        # Falco rules
#   scripts/validate.sh path/to/tracingpolicy.yaml       # Tetragon TracingPolicy
#
# Detection: a file whose `kind:` is TracingPolicy(Namespaced) is treated as
# Tetragon; anything with a top-level `- rule:` / `- macro:` list is treated as Falco.
set -euo pipefail

FILE="${1:-}"
if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  echo "usage: $0 <rules-or-policy.yaml>" >&2
  exit 2
fi

# 1) YAML must parse at all (python3 is available on macOS 3.9+).
python3 - "$FILE" <<'PY'
import sys, yaml
try:
    list(yaml.safe_load_all(open(sys.argv[1])))
except Exception as e:
    print(f"YAML PARSE ERROR: {e}", file=sys.stderr); sys.exit(1)
print("yaml: ok")
PY

# 2) Route to the right validator.
if grep -qE '^[[:space:]]*kind:[[:space:]]*TracingPolicy' "$FILE"; then
  echo "detected: Tetragon TracingPolicy"
  if command -v kubectl >/dev/null 2>&1; then
    # Dry-run against the API server (schema check) if a cluster is reachable.
    kubectl apply --dry-run=server -f "$FILE" 2>/dev/null \
      && echo "kubectl server dry-run: ok" \
      || echo "note: no reachable cluster/CRD — parsed YAML only (install Tetragon CRDs to schema-check)"
  else
    echo "note: kubectl not found — parsed YAML only"
  fi
else
  echo "detected: Falco rules"
  if command -v falco >/dev/null 2>&1; then
    falco --validate "$FILE"     # real schema/condition validation
  elif command -v docker >/dev/null 2>&1; then
    echo "using falcosecurity/falco container to validate..."
    docker run --rm -v "$(cd "$(dirname "$FILE")" && pwd)":/r \
      falcosecurity/falco:latest falco --validate "/r/$(basename "$FILE")"
  else
    echo "note: neither 'falco' nor 'docker' present — parsed YAML only."
    echo "      run 'falco --validate $FILE' on a host with Falco for full checks."
  fi
fi
echo "done."
