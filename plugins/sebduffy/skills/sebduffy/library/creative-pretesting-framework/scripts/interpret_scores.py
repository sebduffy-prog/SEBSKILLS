#!/usr/bin/env python3
"""Interpret real ad-pretest scores into a go/refine/kill gate.

Grounded on published System1 Test Your Ad bands (Star / Spike / Fluency) and
Kantar LINK+ percentile logic. Stdlib only; runs on macOS python3.9.

Usage:
  echo '{"vendor":"system1","star":3.4,"spike":1.12,"fluency":88}' \
      | python3 interpret_scores.py
  python3 interpret_scores.py --star 2.1 --spike 0.95 --fluency 70

This does NOT run a test or predict scores. It only classifies scores you were
GIVEN by the vendor, so a strategist reads every number the same way twice.
"""
import argparse
import json
import sys

# System1 published bands. Each list is (lower_inclusive, label).
STAR_BANDS = [(5.0, "Exceptional"), (4.0, "Strong"), (3.0, "Good"),
              (2.0, "Modest"), (0.0, "Low")]
SPIKE_BANDS = [(1.33, "Exceptional"), (1.19, "Strong"), (1.10, "Good"),
               (1.00, "Modest"), (0.0, "Low")]
FLUENCY_BANDS = [(95, "Exceptional"), (91, "Strong"), (83, "Good"),
                 (73, "Modest"), (0, "Low")]

# Verdict thresholds (defensible defaults; override per brief).
STAR_GO = 3.0      # >=3.0 Star = long-term brand-building potential
STAR_KILL = 2.0    # <2.0 Star = weak, rework or drop
SPIKE_GO = 1.10    # >=1.10 = credible short-term sales spike
FLUENCY_MIN = 83   # <83 = branding too weak, fix attribution first


def band(value, bands):
    """Return the label for the first band whose floor <= value."""
    for floor, label in bands:
        if value >= floor:
            return label
    return bands[-1][1]


def gate(star, spike, fluency):
    """Return (verdict, reasons[]) from System1-style scores."""
    reasons = []
    if fluency is not None and fluency < FLUENCY_MIN:
        reasons.append(
            "Fluency {:.0f} < {} — branding too weak; the ad may work for the "
            "category, not the brand. Fix distinctive assets before re-testing."
            .format(fluency, FLUENCY_MIN))
    if star is None:
        return "INCOMPLETE", ["No Star Rating supplied — cannot gate long-term."]
    if star < STAR_KILL:
        reasons.insert(0, "Star {:.1f} < {:.1f} — below brand-building floor."
                       .format(star, STAR_KILL))
        return "KILL / REWORK", reasons
    if star >= STAR_GO and (spike is None or spike >= SPIKE_GO) and \
            (fluency is None or fluency >= FLUENCY_MIN):
        reasons.insert(0, "Star {:.1f} ({}) clears the {:.1f} bar."
                       .format(star, band(star, STAR_BANDS), STAR_GO))
        return "GO", reasons
    # Between kill and go, or a soft flag tripped.
    reasons.insert(0, "Star {:.1f} ({}) is airable but not a clear winner."
                   .format(star, band(star, STAR_BANDS)))
    if spike is not None and spike < SPIKE_GO:
        reasons.append("Spike {:.2f} ({}) — soft short-term; expect slow burn."
                       .format(spike, band(spike, SPIKE_BANDS)))
    return "REFINE", reasons


def main():
    ap = argparse.ArgumentParser(description="Gate ad-pretest scores.")
    ap.add_argument("--star", type=float)
    ap.add_argument("--spike", type=float)
    ap.add_argument("--fluency", type=float)
    args = ap.parse_args()

    data = {}
    if args.star is None and not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            data = json.loads(raw)
    star = args.star if args.star is not None else data.get("star")
    spike = args.spike if args.spike is not None else data.get("spike")
    fluency = args.fluency if args.fluency is not None else data.get("fluency")

    verdict, reasons = gate(star, spike, fluency)
    out = {
        "verdict": verdict,
        "star": star, "star_band": band(star, STAR_BANDS) if star is not None else None,
        "spike": spike, "spike_band": band(spike, SPIKE_BANDS) if spike is not None else None,
        "fluency": fluency, "fluency_band": band(fluency, FLUENCY_BANDS) if fluency is not None else None,
        "reasons": reasons,
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
