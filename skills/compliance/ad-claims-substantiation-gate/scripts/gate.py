#!/usr/bin/env python3
"""Ad-claims substantiation gate.

Reads a claims ledger (JSON) and BLOCKS (exit 2) if any claim that is capable of
objective substantiation lacks an attributed source, is flagged [verify], or is
missing sign-off. This is the hard human gate: nothing ships until every objective
claim is green. Puffery/opinion is allowed to pass without a source.

Ledger schema (list of claim objects):
  {
    "id": "C1",
    "text": "Britain's most-recommended paint",
    "type": "superiority",        # factual|comparative|superiority|health|environmental|puffery
    "sources": [                    # attributed evidence; empty => unsubstantiated
      {"ref": "YouGov BrandIndex 2026-Q1", "cited_text": "...", "verified": true}
    ],
    "status": "verify",            # verified|verify|unsubstantiated (optional; derived if absent)
    "signed_off_by": null           # reviewer name; required for objective claims
  }

Usage:
  python3 gate.py ledger.json            # enforce, exit 2 on any blocker
  python3 gate.py ledger.json --report   # print table, exit 0 (advisory only)

No third-party dependencies. Python 3.9+.
"""
import json
import sys

OBJECTIVE = {"factual", "comparative", "superiority", "health", "environmental"}
PUFFERY = {"puffery", "opinion"}


def classify(claim):
    """Return (is_blocked, reason) for one claim. Immutable: reads, never mutates."""
    ctype = (claim.get("type") or "").lower().strip()
    text = claim.get("id", "?")
    if ctype in PUFFERY:
        return (False, "puffery/opinion - no substantiation required")
    if ctype not in OBJECTIVE:
        return (True, f"unknown claim type {ctype!r} - classify before shipping")

    sources = claim.get("sources") or []
    attributed = [s for s in sources if s.get("ref") and s.get("verified") is True]
    if not attributed:
        return (True, "no attributed, verified source (unsubstantiated)")

    status = (claim.get("status") or "").lower().strip()
    if status == "verify" or any(s.get("verified") is not True for s in sources):
        return (True, "at least one source flagged [verify] - confirm before shipping")

    if not claim.get("signed_off_by"):
        return (True, "objective claim missing human sign-off")

    # Comparative claims must evidence every named competitor.
    if ctype == "comparative" and not claim.get("competitors_covered"):
        return (True, "comparative claim: set competitors_covered=true (evidence for ALL rivals)")

    return (False, f"substantiated by {len(attributed)} source(s), signed off by {claim['signed_off_by']}")


def main(argv):
    if len(argv) < 2:
        print("usage: gate.py <ledger.json> [--report]", file=sys.stderr)
        return 64
    report_only = "--report" in argv[2:]
    try:
        with open(argv[1], "r", encoding="utf-8") as fh:
            ledger = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read ledger: {exc}", file=sys.stderr)
        return 65
    if not isinstance(ledger, list):
        print("ERROR: ledger must be a JSON array of claim objects", file=sys.stderr)
        return 65

    blockers = []
    for claim in ledger:
        blocked, reason = classify(claim)
        mark = "BLOCK" if blocked else "PASS "
        print(f"[{mark}] {claim.get('id','?'):<6} {claim.get('type','?'):<13} {reason}")
        if blocked:
            blockers.append(claim.get("id", "?"))

    print(f"\n{len(ledger)} claims, {len(blockers)} blocked.")
    if blockers and not report_only:
        print(f"GATE FAILED - unsubstantiated: {', '.join(blockers)}", file=sys.stderr)
        return 2
    print("GATE PASSED" if not blockers else "advisory mode: not enforced")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
