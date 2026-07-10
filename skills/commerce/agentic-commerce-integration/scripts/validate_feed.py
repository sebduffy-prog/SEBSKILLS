#!/usr/bin/env python3
"""Validate an ACP / OpenAI Instant Checkout product feed (JSON array or NDJSON).

Grounded on OpenAI Agentic Commerce "Products" file-upload spec (2026-04-17):
required item fields, availability enum, checkout-eligibility deps, ISO codes.
No third-party deps (stdlib only; Python 3.9 compatible).

Usage:
    python3 validate_feed.py feed.json
    python3 validate_feed.py feed.ndjson --checkout   # enforce checkout-only reqs

Exit code 0 = all rows valid; 1 = one or more rows failed; 2 = bad input.
"""
import argparse
import json
import re
import sys

REQUIRED = [
    "item_id", "title", "description", "url", "brand", "image_url",
    "price", "availability", "is_eligible_search", "is_eligible_checkout",
    "seller_name", "seller_url", "target_countries", "store_country",
]
# Required only when a row opts into in-chat checkout.
CHECKOUT_REQUIRED = ["seller_tos", "seller_privacy_policy"]

AVAILABILITY = {"in_stock", "out_of_stock", "pre_order", "backorder", "unknown"}
MAXLEN = {"item_id": 100, "title": 150, "description": 5000, "brand": 70}
PRICE_RE = re.compile(r"^\d+(\.\d{1,2})?\s+[A-Z]{3}$")   # "29.99 USD"
ISO2_RE = re.compile(r"^[A-Z]{2}$")


def as_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"true", "yes", "1"}
    return None


def check_row(row, idx, enforce_checkout):
    errs = []
    if not isinstance(row, dict):
        return [f"row {idx}: not an object"]

    for f in REQUIRED:
        if row.get(f) in (None, ""):
            errs.append(f"row {idx}: missing required field '{f}'")

    for f, limit in MAXLEN.items():
        val = row.get(f)
        if isinstance(val, str) and len(val) > limit:
            errs.append(f"row {idx}: '{f}' exceeds {limit} chars ({len(val)})")

    avail = row.get("availability")
    if avail is not None and avail not in AVAILABILITY:
        errs.append(f"row {idx}: availability '{avail}' not in {sorted(AVAILABILITY)}")

    price = row.get("price")
    if isinstance(price, str) and not PRICE_RE.match(price):
        errs.append(f"row {idx}: price '{price}' must be '<amount> <ISO4217>' e.g. '29.99 USD'")

    store = row.get("store_country")
    if isinstance(store, str) and not ISO2_RE.match(store):
        errs.append(f"row {idx}: store_country '{store}' must be ISO 3166-1 alpha-2 (e.g. 'US')")

    checkout_on = as_bool(row.get("is_eligible_checkout"))
    if checkout_on and (enforce_checkout or True):
        for f in CHECKOUT_REQUIRED:
            if row.get(f) in (None, ""):
                errs.append(f"row {idx}: '{f}' required when is_eligible_checkout is true")
    return errs


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read().strip()
    if not text:
        raise ValueError("empty file")
    if text[0] == "[":
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("top-level JSON must be an array of products")
        return data
    # NDJSON fallback: one product object per line.
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def main():
    ap = argparse.ArgumentParser(description="Validate an ACP product feed")
    ap.add_argument("path", help="feed.json (array) or feed.ndjson")
    ap.add_argument("--checkout", action="store_true",
                    help="(reserved) checkout deps are always enforced on checkout-eligible rows")
    args = ap.parse_args()

    try:
        rows = load(args.path)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"ERROR reading {args.path}: {e}", file=sys.stderr)
        sys.exit(2)

    all_errs = []
    for i, row in enumerate(rows):
        all_errs.extend(check_row(row, i, args.checkout))

    if all_errs:
        for e in all_errs:
            print(e)
        print(f"\nFAIL: {len(all_errs)} issue(s) across {len(rows)} row(s)")
        sys.exit(1)
    print(f"OK: {len(rows)} row(s) valid")


if __name__ == "__main__":
    main()
