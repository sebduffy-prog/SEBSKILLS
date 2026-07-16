#!/usr/bin/env python3
"""Post-process social-listening daily counts: Share of Voice + spike detection.

Pure stdlib (Python 3.9+). No network. Feed it the daily mention counts you
already pulled from Brand24 / Brandwatch and it returns:
  - Share of Voice (%) per brand over the window, plus per-day SOV series.
  - Spike days per brand via a rolling z-score (default window 7, threshold 2.5).

Input JSON (stdin or --infile), shape:
    {
      "IRN-BRU":  [{"date": "2026-06-01", "count": 120}, ...],
      "Coca-Cola":[{"date": "2026-06-01", "count": 340}, ...]
    }
Dates are ISO (YYYY-MM-DD). Missing days are treated as zero when aligning.

Usage:
    python3 listening_analysis.py --infile counts.json
    cat counts.json | python3 listening_analysis.py --window 7 --z 2.5
"""
import argparse
import json
import statistics
import sys
from datetime import date, timedelta


def _parse(day: str) -> date:
    return date.fromisoformat(day)


def align_dates(series_by_brand):
    """Return sorted list of all dates spanning min..max across every brand."""
    all_days = [
        _parse(row["date"])
        for rows in series_by_brand.values()
        for row in rows
    ]
    if not all_days:
        return []
    lo, hi = min(all_days), max(all_days)
    span, cur = [], lo
    while cur <= hi:
        span.append(cur)
        cur += timedelta(days=1)
    return span


def to_dense(rows, span):
    """Map a brand's [{date,count}] onto the full date span, filling zeros."""
    lookup = {_parse(r["date"]): int(r["count"]) for r in rows}
    return [lookup.get(d, 0) for d in span]


def share_of_voice(series_by_brand, span):
    """Overall SOV (%) per brand and a per-day SOV matrix."""
    dense = {b: to_dense(rows, span) for b, rows in series_by_brand.items()}
    totals = {b: sum(v) for b, v in dense.items()}
    grand = sum(totals.values()) or 1
    overall = {b: round(100 * t / grand, 2) for b, t in totals.items()}
    per_day = []
    for i, d in enumerate(span):
        day_total = sum(dense[b][i] for b in dense) or 1
        per_day.append({
            "date": d.isoformat(),
            **{b: round(100 * dense[b][i] / day_total, 2) for b in dense},
        })
    return overall, per_day, dense


def detect_spikes(counts, window=7, z=2.5):
    """Flag indices where count exceeds rolling mean + z*std of prior `window` days."""
    spikes = []
    for i in range(len(counts)):
        prior = counts[max(0, i - window):i]
        if len(prior) < window:
            continue
        mu = statistics.mean(prior)
        sd = statistics.pstdev(prior)
        if sd == 0:
            continue
        score = (counts[i] - mu) / sd
        if score >= z:
            spikes.append({"index": i, "count": counts[i], "z": round(score, 2)})
    return spikes


def run(series_by_brand, window, z):
    span = align_dates(series_by_brand)
    overall, per_day, dense = share_of_voice(series_by_brand, span)
    spikes = {}
    for b in dense:
        flagged = detect_spikes(dense[b], window, z)
        for f in flagged:
            f["date"] = span[f.pop("index")].isoformat()
        spikes[b] = flagged
    return {
        "window": {"start": span[0].isoformat(), "end": span[-1].isoformat()} if span else {},
        "share_of_voice_pct": overall,
        "sov_per_day": per_day,
        "spikes": spikes,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--infile", help="JSON file; defaults to stdin")
    ap.add_argument("--window", type=int, default=7, help="rolling window (days)")
    ap.add_argument("--z", type=float, default=2.5, help="z-score spike threshold")
    args = ap.parse_args()
    raw = open(args.infile).read() if args.infile else sys.stdin.read()
    data = json.loads(raw)
    if not isinstance(data, dict):
        sys.exit("Input must be a JSON object keyed by brand name.")
    print(json.dumps(run(data, args.window, args.z), indent=2))


if __name__ == "__main__":
    main()
