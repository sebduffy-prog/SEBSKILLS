#!/usr/bin/env python3
"""Creator screening + EMV helper. Pure stdlib, Python 3.9+.

Two jobs:
  1. fraud-screen a creator against public benchmark red flags -> risk score
  2. compute an EMV estimate + a sanity-check CPM/CPE for a proposed fee

All numbers are DIRECTIONAL benchmarks from public 2025 sources (HypeAuditor,
Ayzenberg EMV Index, CreatorIQ). They do not replace a paid audit tool — they
give you a fast, defensible desk-screen and force the right questions.

Usage:
    python3 creator_screen.py screen --tier micro --er 0.9 --fake-pct 34 \
        --growth-spike 22 --generic-comment-pct 40 --audience-geo-gap 25 --aqs 55
    python3 creator_screen.py emv --impressions 120000 --likes 8000 \
        --comments 300 --fee 4000
"""
import argparse
import json
import sys

# Engagement-rate floors by tier (%). Below floor = likely fraud / dead audience.
# Source: HypeAuditor / InfluenceFlow 2025 benchmarks.
ER_FLOOR = {"nano": 3.0, "micro": 2.0, "mid": 1.5, "macro": 1.0, "mega": 0.6}

# Ayzenberg-style default engagement values (USD) used for EMV.
# Tune to your own paid-media CPM before quoting to a client.
VALUE_PER_LIKE = 0.10
VALUE_PER_COMMENT = 1.00
CPM_IMPRESSIONS = 8.00  # $ per 1,000 impressions

# Red-flag thresholds from public 2025 fraud-detection guidance.
FAKE_PCT_FLAG = 25.0        # >25% suspicious followers
GROWTH_SPIKE_FLAG = 15.0    # >15% growth in a 7-day window unexplained
GENERIC_COMMENT_FLAG = 15.0 # >15% emoji/one-word/copy-paste comments
GEO_GAP_FLAG = 20.0         # >20pt gap vs target market
AQS_FLAG = 60.0             # HypeAuditor Audience Quality Score below 60


def screen(args):
    flags = []
    floor = ER_FLOOR.get(args.tier, 1.0)
    if args.er is not None and args.er < floor:
        flags.append(f"ER {args.er}% below {args.tier} floor {floor}%")
    if args.fake_pct is not None and args.fake_pct > FAKE_PCT_FLAG:
        flags.append(f"Suspicious followers {args.fake_pct}% > {FAKE_PCT_FLAG}%")
    if args.growth_spike is not None and args.growth_spike > GROWTH_SPIKE_FLAG:
        flags.append(f"Unexplained 7d growth {args.growth_spike}% > {GROWTH_SPIKE_FLAG}%")
    if args.generic_comment_pct is not None and args.generic_comment_pct > GENERIC_COMMENT_FLAG:
        flags.append(f"Generic comments {args.generic_comment_pct}% > {GENERIC_COMMENT_FLAG}%")
    if args.audience_geo_gap is not None and args.audience_geo_gap > GEO_GAP_FLAG:
        flags.append(f"Audience geo gap {args.audience_geo_gap}pt > {GEO_GAP_FLAG}pt")
    if args.aqs is not None and args.aqs < AQS_FLAG:
        flags.append(f"AQS {args.aqs} < {AQS_FLAG}")

    n = len(flags)
    verdict = "PASS" if n == 0 else ("REVIEW" if n <= 2 else "REJECT")
    print(json.dumps({"verdict": verdict, "flag_count": n, "flags": flags}, indent=2))


def emv(args):
    est = (args.likes * VALUE_PER_LIKE
           + args.comments * VALUE_PER_COMMENT
           + (args.impressions / 1000.0) * CPM_IMPRESSIONS)
    out = {"emv_usd": round(est, 2)}
    if args.fee and args.fee > 0:
        out["emv_to_fee_ratio"] = round(est / args.fee, 2)
        if args.impressions:
            out["effective_cpm"] = round(args.fee / (args.impressions / 1000.0), 2)
        eng = args.likes + args.comments
        if eng:
            out["effective_cpe"] = round(args.fee / eng, 3)
    print(json.dumps(out, indent=2))


def main():
    p = argparse.ArgumentParser(description="Creator fraud-screen + EMV helper")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("screen", help="Fraud red-flag screen")
    s.add_argument("--tier", choices=list(ER_FLOOR), default="micro")
    s.add_argument("--er", type=float, help="Engagement rate %")
    s.add_argument("--fake-pct", type=float, help="Suspicious follower %")
    s.add_argument("--growth-spike", type=float, help="Max 7d growth %")
    s.add_argument("--generic-comment-pct", type=float)
    s.add_argument("--audience-geo-gap", type=float, help="pt gap vs target market")
    s.add_argument("--aqs", type=float, help="HypeAuditor Audience Quality Score 1-100")
    s.set_defaults(func=screen)

    e = sub.add_parser("emv", help="Earned Media Value estimate")
    e.add_argument("--impressions", type=float, default=0)
    e.add_argument("--likes", type=float, default=0)
    e.add_argument("--comments", type=float, default=0)
    e.add_argument("--fee", type=float, default=0, help="Proposed creator fee")
    e.set_defaults(func=emv)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
