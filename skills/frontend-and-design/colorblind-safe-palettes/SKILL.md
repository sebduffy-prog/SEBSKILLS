---
name: colorblind-safe-palettes
category: frontend-and-design
description: >
  Pick, validate, and repair categorical colour palettes for colour-vision
  deficiency (protan/deutan/tritan ~8% of men, 0.5% of women). Drop in proven
  safe schemes (Okabe-Ito, Paul Tol bright/muted/high-contrast, Viridis), then
  prove separation by simulating CVD with the Machado 2009 matrices and scoring
  every pair with CIEDE2000 ΔE. Use when charts, maps, dashboards, or status UI
  must stay readable for colourblind viewers, when a red/green legend is
  suspect, or when a designer asks "is this palette accessible?".
when_to_use:
  - Choosing categorical/series colours for a chart, map, legend, or dashboard
  - Auditing an existing palette for red-green or blue-yellow confusion
  - A stakeholder or WCAG review asks whether colours are colourblind-safe
  - Replacing a failing swatch and needing proof the fix separates under CVD
  - Picking a sequential/diverging ramp that survives greyscale + CVD (Viridis)
when_not_to_use:
  - Text/background contrast ratios (WCAG 1.4.3) — use accessible-contrast-checker
  - Generating on-brand harmonious hues from scratch — use color-harmony-generator
  - Perceptual gradient/ramp construction in OKLCH — use perceptual-gradient-designer
  - Full brand token pipeline (naming, tiers, export) — use brand-color-token-system
keywords:
  - colorblind
  - color-vision-deficiency
  - cvd
  - protanopia
  - deuteranopia
  - tritanopia
  - okabe-ito
  - paul-tol
  - viridis
  - deltae
  - ciede2000
  - machado
  - accessibility
  - categorical-palette
  - daltonism
  - a11y
similar_to:
  - accessible-contrast-checker
  - color-harmony-generator
  - perceptual-gradient-designer
  - brand-color-token-system
  - dataviz
inputs_needed: A set of hex colours to audit, OR the number of categories needing distinct colours.
produces: A verified CVD-safe palette (hex list + roles) plus a per-CVD CIEDE2000 separation report flagging any colliding pair.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Colourblind-Safe Palettes

Categorical colour is an accessibility surface. Roughly 1 in 12 men and 1 in 200
women have colour-vision deficiency (CVD) — most commonly red-green (protan /
deutan), rarely blue-yellow (tritan). This skill gives you (a) drop-in palettes
that are already proven safe, and (b) a zero-dependency checker that *proves* any
palette stays separable by simulating CVD and measuring perceptual distance.

## When to use

Reach for this whenever colour is doing semantic work — series in a chart,
regions on a map, categories in a legend, or status pills. If you can't tell two
categories apart in the simulated-CVD report, neither can ~8% of your audience.

## Prerequisites

- `python3` (stdlib only — the checker has **no** pip dependencies).
- Palette as hex strings, or a target category count.

## Proven palettes (copy these first)

Prefer a vetted scheme over hand-picking. Order matters — the schemes are ordered
so the first *n* colours stay maximally separable. Never assign colour by red/green
alone; pair it with shape, label, or position.

**Okabe-Ito** — 8 colours, the de-facto scientific standard (Okabe & Ito 2008).
Named, safe across all CVD types, prints in greyscale reasonably.
```
#000000 black      #E69F00 orange     #56B4E9 sky-blue   #009E73 bluish-green
#F0E442 yellow     #0072B2 blue       #D55E00 vermillion #CC79A7 reddish-purple
```

**Paul Tol — bright** (default categorical, up to 7). Grey is the bad/missing-data slot.
```
#4477AA blue  #EE6677 red  #228833 green  #CCBB44 yellow  #66CCEE cyan  #AA3377 purple  #BBBBBB grey
```

**Paul Tol — high-contrast** (up to 3, also greyscale-safe; add #000/#FFF).
```
#004488 blue   #DDAA33 yellow   #BB5566 red
```

**Paul Tol — vibrant** (up to 7; bad data #BBBBBB).
```
#EE7733 orange #0077BB blue #33BBEE cyan #EE3377 magenta #CC3311 red #009988 teal #BBBBBB grey
```

**Paul Tol — muted** (up to 9, no strong red/blue; bad data #DDDDDD).
```
#CC6677 rose #332288 indigo #DDCC77 sand #117733 green #88CCEE cyan #882255 wine #44AA99 teal #999933 olive #AA4499 purple
```

**Viridis family** — for *sequential/diverging* ramps (heatmaps, continuous),
not categorical. Perceptually uniform, monotonic in lightness, so it survives
both greyscale and every CVD type. Options: `viridis`, `cividis` (tuned for CVD),
`mako`, `rocket`. Sample endpoints of viridis: `#440154 → #21908C → #FDE725`.

Sources: [Okabe & Ito](https://jfly.uni-koeln.de/color/),
[Paul Tol's notes](https://sronpersonalpages.nl/~pault/),
[Viridis](https://bids.github.io/colormap/).

## Recipe A — audit an existing palette

Run the checker. It simulates protan/deutan/tritan vision with the **Machado
2009** severity-1.0 matrices and reports the minimum **CIEDE2000** distance
between every pair, per vision type.

```bash
python3 scripts/cvd_check.py --min 15 "#D62728" "#2CA02C" "#1F77B4"
```
```
vision      min ΔE00   closest pair
----------------------------------------------
normal          48.6   #D62728 / #1F77B4
protan          33.4   #D62728 / #2CA02C
deutan          13.9   #D62728 / #2CA02C  <-- FAIL
tritan          12.5   #2CA02C / #1F77B4  <-- FAIL
VERDICT: not CVD-safe — merge/replace the flagged pair(s).
```
Matplotlib's default red/green/blue trio looks bold to normal vision (ΔE 48.6)
but the red and green fall to 13.9 under deutan — fine at the default floor,
flagged once you demand the comfortable `--min 15`.

**Reading ΔE00 bands:** `<5` indistinguishable · `5–10` risky · `≥10` practical
categorical floor (where Okabe-Ito / Tol land) · `≥15` comfortable. Default
threshold is `10`; raise it with `--min 15` for high-stakes UI.

## Recipe B — pick a fresh palette for N categories

1. Need ≤ 7? Take Paul Tol **bright** (or Okabe-Ito for 8) in order — done.
2. Need 8–9? Use Okabe-Ito (8) or Tol **muted** (9). Beyond ~10 categories,
   colour alone fails everyone; add facets, labels, or direct annotation.
3. Adding brand colours? Slot them in, then **prove** with Recipe A before shipping.
4. Reserve one neutral grey (`#BBBBBB`/`#DDDDDD`) exclusively for missing/other.

## Recipe C — repair a failing pair

When the report flags a collision, don't nudge the hue blindly — CVD flattens the
axis you'd nudge along. Instead:

- **Shift lightness**, not just hue. CVD preserves luminance contrast, so making
  one swatch clearly darker/lighter reliably restores separation (this is why
  high-contrast schemes are also greyscale-safe).
- Swap the offender for the next unused colour in a proven scheme.
- Re-run the checker until every vision row clears your threshold.

## CSS / JS wiring

Expose as tokens so the whole app shares one audited source of truth:
```css
:root{ --cat-1:#4477AA; --cat-2:#EE6677; --cat-3:#228833; --cat-4:#CCBB44;
       --cat-5:#66CCEE; --cat-6:#AA3377; --cat-nodata:#BBBBBB; }
```
For live browser simulation (design QA), CSS SVG filters approximate CVD but are
less accurate than Machado — trust the checker for pass/fail, use filters for feel.

## Verify

```bash
# Known-good palettes must PASS at the default floor:
python3 scripts/cvd_check.py "#E69F00" "#56B4E9" "#009E73" "#F0E442" "#0072B2" "#D55E00" "#CC79A7"
python3 scripts/cvd_check.py "#4477AA" "#EE6677" "#228833" "#CCBB44" "#66CCEE" "#AA3377"
# The matplotlib red/green/blue trio must FAIL the comfortable threshold:
python3 scripts/cvd_check.py --min 15 "#D62728" "#2CA02C" "#1F77B4"   # exit code 1
```
The CIEDE2000 core is validated against the Sharma et al. 2005 reference pairs
(e.g. ΔE00 = 2.0425 for the canonical G1 pair). Exit code: `0` safe, `1` fail.

## Pitfalls

- **Simulation ≠ measurement.** A palette that *looks* fine to you can collapse
  under CVD. Always run the checker; don't eyeball hex codes.
- **Machado matrices apply to gamma-encoded sRGB**, not linearised RGB (the
  DaltonLens finding). The script does this correctly — don't "fix" it by
  linearising first, or the sim skews.
- **Colour is never the only channel.** WCAG 1.4.1 requires a second cue —
  shape, pattern, label, or position. A CVD-safe palette still fails a viewer
  with full achromatopsia or a greyscale print if colour carries meaning alone.
- **Adjacency matters.** Two colours can pass the pairwise check yet confuse when
  touching (simultaneous contrast). Add hairline separators between fills.
- **Don't reuse the missing-data grey** for a real category — it reads as "no data".
- **Sequential data wants a ramp, not categories.** Use Viridis/cividis, not a
  qualitative scheme, for magnitude — categorical hues imply unordered groups.
- **Tritan is rare but real.** Blue/yellow-heavy palettes that pass deutan can
  still fail tritan — the checker tests all three, so read every row.
