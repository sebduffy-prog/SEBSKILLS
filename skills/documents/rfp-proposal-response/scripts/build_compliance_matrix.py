#!/usr/bin/env python3
"""Turn a shredded-requirements JSON list into a compliance-matrix CSV.

The compliance matrix is the spine of an RFP response: one row per atomic
requirement, each with an owner, a compliance verdict, a page/section cross-
reference, and the drafted proof point. This script enforces that shape so no
requirement silently goes unanswered.

Input JSON: a list of objects. Only `id` and `requirement` are required; the
rest default to empty / TBD so a fresh matrix is a clean checklist.

    [
      {"id": "3.1.1", "requirement": "Vendor must be ISO 27001 certified",
       "section": "Security", "mandatory": true, "owner": "InfoSec"}
    ]

Usage:
    python3 build_compliance_matrix.py requirements.json > matrix.csv
    python3 build_compliance_matrix.py requirements.json -o matrix.csv

Import matrix.csv into Excel/Sheets/Loopio. Compliance uses the standard
government-bid vocabulary: Comply / Partial / Exception / No Bid.
"""
import argparse
import csv
import json
import sys

COLUMNS = [
    "req_id",           # e.g. 3.1.1 — traceable back to the solicitation
    "section",          # RFP section / heading the requirement sits under
    "requirement",      # verbatim requirement text (do not paraphrase)
    "mandatory",        # M (must/shall) or D (desirable/should)
    "compliance",       # Comply | Partial | Exception | No Bid
    "owner",            # named SME accountable for the answer
    "response_ref",     # where the answer lives (proposal §, page, attachment)
    "win_theme",        # win theme this requirement ladders up to
    "proof_point",      # the drafted evidence/answer or library snippet id
    "status",           # Not started | Drafting | Review | Final
]

VALID_COMPLIANCE = {"Comply", "Partial", "Exception", "No Bid", ""}


def to_row(item, index):
    if "requirement" not in item:
        raise ValueError(f"item {index} is missing required field 'requirement'")
    compliance = item.get("compliance", "")
    if compliance not in VALID_COMPLIANCE:
        raise ValueError(
            f"item {index}: compliance {compliance!r} must be one of "
            f"{sorted(c for c in VALID_COMPLIANCE if c)}"
        )
    mandatory_flag = item.get("mandatory")
    if isinstance(mandatory_flag, bool):
        mandatory = "M" if mandatory_flag else "D"
    else:
        mandatory = str(mandatory_flag or "").strip() or "M"
    return {
        "req_id": str(item.get("id", index + 1)),
        "section": item.get("section", ""),
        "requirement": item["requirement"].strip(),
        "mandatory": mandatory,
        "compliance": compliance,
        "owner": item.get("owner", ""),
        "response_ref": item.get("response_ref", ""),
        "win_theme": item.get("win_theme", ""),
        "proof_point": item.get("proof_point", ""),
        "status": item.get("status", "Not started"),
    }


def build(items):
    if not isinstance(items, list):
        raise ValueError("top-level JSON must be a list of requirement objects")
    return [to_row(item, i) for i, item in enumerate(items)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="path to shredded requirements JSON")
    parser.add_argument("-o", "--output", help="output CSV path (default stdout)")
    args = parser.parse_args(argv)

    try:
        with open(args.input, encoding="utf-8") as fh:
            items = json.load(fh)
        rows = build(items)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    out = open(args.output, "w", newline="", encoding="utf-8") if args.output else sys.stdout
    try:
        writer = csv.DictWriter(out, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if args.output:
            out.close()
    print(f"wrote {len(rows)} requirements", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
