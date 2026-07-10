#!/usr/bin/env python3
"""Summarise FAIL findings from a Prowler OCSF JSON output file.

Prowler's `--output-formats json-ocsf` writes a JSON array of OCSF Detection
Findings. This reads that file (stdin or path), keeps only failures, and prints
a severity-ranked summary + per-service counts. Schema-tolerant: it probes the
likely OCSF/Prowler keys and falls back gracefully rather than crashing.

Usage:
  python3 prowler_fails.py output/prowler-output.ocsf.json
  python3 prowler_fails.py < output/prowler-output.ocsf.json
  python3 prowler_fails.py results.json --severity critical,high
"""
import argparse
import json
import sys
from collections import Counter

SEV_ORDER = ["critical", "high", "medium", "low", "informational"]


def load(path):
    raw = sys.stdin.read() if path in (None, "-") else open(path, encoding="utf-8").read()
    data = json.loads(raw)
    return data if isinstance(data, list) else [data]


def status_of(f):
    return str(f.get("status_code") or f.get("status") or "").upper()


def severity_of(f):
    sev = f.get("severity")
    if isinstance(sev, dict):
        sev = sev.get("name") or sev.get("id")
    return str(sev or "unknown").lower()


def title_of(f):
    fi = f.get("finding_info") or {}
    return fi.get("title") or f.get("message") or f.get("check_id") or "(untitled)"


def service_of(f):
    # Prowler stashes the service in unmapped/resources/metadata depending on version.
    for path in (("resources", 0, "group", "name"),
                 ("resources", 0, "type"),
                 ("cloud", "provider")):
        cur = f
        try:
            for key in path:
                cur = cur[key]
            if cur:
                return str(cur)
        except (KeyError, IndexError, TypeError):
            continue
    unmapped = f.get("unmapped") or {}
    return str(unmapped.get("service_name") or "unknown")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="-", help="OCSF JSON file, or - for stdin")
    ap.add_argument("--severity", help="comma list to keep, e.g. critical,high")
    args = ap.parse_args()

    keep = {s.strip().lower() for s in args.severity.split(",")} if args.severity else None
    findings = load(args.path)

    fails = [f for f in findings if status_of(f) == "FAIL"]
    if keep:
        fails = [f for f in fails if severity_of(f) in keep]

    if not fails:
        print("No FAIL findings matched. Estate looks clean for the given filter.")
        return 0

    by_sev = Counter(severity_of(f) for f in fails)
    by_svc = Counter(service_of(f) for f in fails)

    print(f"FAIL findings: {len(fails)}\n")
    print("By severity:")
    for sev in SEV_ORDER + sorted(set(by_sev) - set(SEV_ORDER)):
        if by_sev.get(sev):
            print(f"  {sev:<14} {by_sev[sev]}")
    print("\nTop services:")
    for svc, n in by_svc.most_common(12):
        print(f"  {svc:<24} {n}")

    print("\nCritical/High detail:")
    ranked = sorted(fails, key=lambda f: SEV_ORDER.index(severity_of(f))
                    if severity_of(f) in SEV_ORDER else 99)
    for f in ranked:
        if severity_of(f) in ("critical", "high"):
            print(f"  [{severity_of(f).upper():<8}] {service_of(f):<18} {title_of(f)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
