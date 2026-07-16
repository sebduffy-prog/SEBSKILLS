#!/usr/bin/env python3
"""Offline bookkeeping helpers: bank reconciliation + AR/AP aging.

Pure stdlib (Python 3.9+). No network, no dependencies. Feed it CSVs exported
from Xero / QuickBooks / a bank, get back matched pairs and aging buckets.

Usage:
  # Match a bank statement against ledger/invoice rows
  python3 reconcile.py match --bank bank.csv --ledger ledger.csv \
      [--days 4] [--out matches.csv]

  # Bucket open receivables/payables by age
  python3 reconcile.py aging --invoices invoices.csv [--asof 2026-07-10]

CSV columns (case-insensitive, extra columns ignored):
  bank.csv     : date, amount, description        (amount signed: +in / -out)
  ledger.csv   : date, amount, reference          (amount signed)
  invoices.csv : due_date, amount, paid[, contact]  (paid defaults 0)

Matching is deterministic: exact amount (to the cent) + date within --days,
greedy nearest-date first. Nothing is mutated; new rows are emitted.
"""
import argparse
import csv
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

AGING_BUCKETS = ((0, "current"), (30, "1-30"), (60, "31-60"),
                 (90, "61-90"), (10**9, "90+"))
DEFAULT_DATE_WINDOW = 3


def parse_date(value):
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError("unrecognised date: %r" % value)


def parse_money(value):
    cleaned = (value or "").replace(",", "").replace("$", "").replace("£", "").strip()
    if cleaned in ("", "-"):
        return Decimal("0")
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError("bad amount: %r" % value) from exc


def load_rows(path, date_key, amount_key, label_key):
    """Return list of dicts with normalised date/amount/label; validate input."""
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        lower = {name.lower(): name for name in (reader.fieldnames or [])}
        for required in (date_key, amount_key):
            if required not in lower:
                raise SystemExit("%s: missing required column %r (have %s)"
                                 % (path, required, list(lower)))
        for i, raw in enumerate(reader, start=2):
            try:
                rows.append({
                    "date": parse_date(raw[lower[date_key]]),
                    "amount": parse_money(raw[lower[amount_key]]),
                    "label": (raw.get(lower.get(label_key, ""), "") or "").strip(),
                    "paid": parse_money(raw[lower["paid"]]) if "paid" in lower else Decimal("0"),
                    "row": i,
                })
            except ValueError as exc:
                raise SystemExit("%s line %d: %s" % (path, i, exc))
    return rows


def match(bank, ledger, window):
    """Greedy exact-amount, nearest-date matcher. Returns (pairs, b_open, l_open)."""
    used_ledger = set()
    pairs = []
    for b in bank:
        best, best_gap = None, None
        for idx, l in enumerate(ledger):
            if idx in used_ledger or l["amount"] != b["amount"]:
                continue
            gap = abs((b["date"] - l["date"]).days)
            if gap <= window and (best_gap is None or gap < best_gap):
                best, best_gap = idx, gap
        if best is not None:
            used_ledger.add(best)
            pairs.append((b, ledger[best], best_gap))
    bank_open = [b for b in bank if b not in [p[0] for p in pairs]]
    ledger_open = [l for i, l in enumerate(ledger) if i not in used_ledger]
    return pairs, bank_open, ledger_open


def aging(invoices, as_of):
    buckets = {name: Decimal("0") for _, name in AGING_BUCKETS}
    for inv in invoices:
        outstanding = inv["amount"] - inv["paid"]
        if outstanding <= 0:
            continue
        days = (as_of - inv["date"]).days
        for threshold, name in AGING_BUCKETS:
            if days <= threshold:
                buckets[name] += outstanding
                break
    return buckets


def cmd_match(args):
    bank = load_rows(args.bank, "date", "amount", "description")
    ledger = load_rows(args.ledger, "date", "amount", "reference")
    pairs, bank_open, ledger_open = match(bank, ledger, args.days)
    print("Matched %d of %d bank lines (window=%d days)"
          % (len(pairs), len(bank), args.days))
    print("Unreconciled bank lines : %d" % len(bank_open))
    print("Unreconciled ledger rows: %d" % len(ledger_open))
    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["bank_date", "ledger_date", "amount", "day_gap", "description"])
            for b, l, gap in pairs:
                w.writerow([b["date"], l["date"], b["amount"], gap, b["label"]])
        print("Wrote %s" % args.out)
    return 0


def cmd_aging(args):
    as_of = parse_date(args.asof) if args.asof else date.today()
    invoices = load_rows(args.invoices, "due_date", "amount", "contact")
    buckets = aging(invoices, as_of)
    total = sum(buckets.values())
    print("Aging as of %s" % as_of)
    for _, name in AGING_BUCKETS:
        print("  %-8s %12s" % (name, buckets[name]))
    print("  %-8s %12s" % ("TOTAL", total))
    return 0


def build_parser():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("match", help="reconcile bank vs ledger")
    m.add_argument("--bank", required=True)
    m.add_argument("--ledger", required=True)
    m.add_argument("--days", type=int, default=DEFAULT_DATE_WINDOW)
    m.add_argument("--out")
    m.set_defaults(func=cmd_match)
    a = sub.add_parser("aging", help="bucket open invoices by age")
    a.add_argument("--invoices", required=True)
    a.add_argument("--asof")
    a.set_defaults(func=cmd_aging)
    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    sys.exit(args.func(args))
