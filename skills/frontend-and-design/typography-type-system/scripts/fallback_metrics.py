#!/usr/bin/env python3
"""Compute a zero-CLS @font-face fallback override block.

Given the web font's metrics (readable from its head/hhea/OS-2 tables) plus the
average glyph width of both the web font and a system fallback, this emits the
size-adjust / ascent-override / descent-override / line-gap-override values that
make the fallback occupy the SAME box as the web font. Swapping in the real font
then causes no layout shift (CLS ~= 0). This is the same math next/font and
@capsizecss/metrics use.

All *-override values are percentages of the (adjusted) em. ascent/descent/
line-gap are given in font units and normalised by unitsPerEm, then divided by
size-adjust so they scale with the resized fallback.

Usage:
  python3 fallback_metrics.py \
    --ascent 1950 --descent 494 --line-gap 0 --units-per-em 2048 \
    --web-avg 1017 --fallback-avg 977

Metric sources: read with fontkit/opentype.js, or look up common families in
https://github.com/seek-oss/capsize (packages/metrics). Arial avg width ~977,
Times New Roman ~908 (units-per-em 2048); use the matching fallback.
"""
import argparse


def compute(ascent, descent, line_gap, units_per_em, web_avg, fallback_avg):
    if fallback_avg <= 0 or units_per_em <= 0:
        raise ValueError("fallback_avg and units_per_em must be > 0")
    size_adjust = web_avg / fallback_avg
    to_pct = lambda units: (units / units_per_em) / size_adjust * 100
    return {
        "size-adjust": round(size_adjust * 100, 4),
        "ascent-override": round(to_pct(ascent), 4),
        "descent-override": round(to_pct(descent), 4),
        "line-gap-override": round(to_pct(line_gap), 4),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ascent", type=float, required=True, help="hhea/OS2 ascent in font units")
    p.add_argument("--descent", type=float, required=True, help="descent magnitude in font units (positive)")
    p.add_argument("--line-gap", type=float, default=0.0)
    p.add_argument("--units-per-em", type=float, required=True)
    p.add_argument("--web-avg", type=float, required=True, help="web font xAvgCharWidth / avg glyph width")
    p.add_argument("--fallback-avg", type=float, required=True, help="fallback font avg glyph width, same unitsPerEm basis")
    p.add_argument("--fallback-family", default="Arial", help="system fallback family name")
    p.add_argument("--name", default="MyFontFallback", help="name for the generated @font-face family")
    a = p.parse_args()
    m = compute(a.ascent, a.descent, a.line_gap, a.units_per_em, a.web_avg, a.fallback_avg)
    print("/* Add BOTH families to your stack: font-family: 'MyFont', '%s', sans-serif; */" % a.name)
    print("@font-face {")
    print("  font-family: '%s';" % a.name)
    print("  src: local('%s');" % a.fallback_family)
    print("  size-adjust: %s%%;" % m["size-adjust"])
    print("  ascent-override: %s%%;" % m["ascent-override"])
    print("  descent-override: %s%%;" % m["descent-override"])
    print("  line-gap-override: %s%%;" % m["line-gap-override"])
    print("}")


if __name__ == "__main__":
    main()
