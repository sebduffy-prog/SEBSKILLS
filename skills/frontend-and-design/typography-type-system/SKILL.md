---
name: typography-type-system
category: frontend-and-design
description: >-
  Build a real typography system, not just font-sizes — a modular scale with a
  named ratio, fluid clamp() steps, variable-font axes wired correctly, self-hosted
  WOFF2 with unicode-range subsetting, and a zero-CLS loading strategy using
  size-adjust + ascent/descent/line-gap-override so swapping in the web font causes
  no layout shift. Reach for this when text looks arbitrary (random 18/22/28px),
  when web fonts flash and reflow (FOUT/CLS), when you want one font-weight axis
  instead of 6 files, or when tuning line-height, measure and OpenType features.
  Grounded on web.dev font-best-practices, utopia.fyi and the CSS Fonts spec.
when_to_use:
  - Font sizes across the app are ad-hoc (18/20/23/28px) and you want a principled modular scale
  - A web font flashes then reflows the page on load (visible FOUT / cumulative layout shift)
  - You are shipping 4-6 separate weight files and want one variable font with a weight axis
  - Self-hosting fonts and need the correct @font-face, WOFF2, preload and unicode-range subset
  - Setting readable body text — line-height, measure (line length), letter-spacing per size
  - Turning on OpenType features (ligatures, tabular figures, fractions, stylistic sets)
when_not_to_use:
  - You only need the clamp() slope/intercept math for fluid tokens — use fluid-responsive-system
  - You are pairing/choosing typefaces for a brand identity — use brand-guidelines or vccp-media-design
  - The task is colour tokens or contrast, not type — use oklch-color-engine or accessible-contrast-checker
  - You want a whole page scaffolded fast — use quick-landing, then layer this system in
keywords:
  - typography
  - type scale
  - modular scale
  - variable fonts
  - font-display
  - cls
  - fout
  - size-adjust
  - ascent-override
  - woff2
  - unicode-range
  - self-host fonts
  - opentype features
  - line-height
  - measure
  - font-optical-sizing
similar_to:
  - fluid-responsive-system
  - motion-system
  - brand-guidelines
  - oklch-color-engine
inputs_needed: >-
  Target font family/families (variable WOFF2 preferred), a base body size (px),
  a scale ratio intent (e.g. tight 1.2 / classic 1.25 / expressive 1.333), and
  min/max viewport widths for fluid steps. For zero-CLS: the web font's ascent,
  descent, line-gap, unitsPerEm and average glyph width plus a system fallback.
produces: >-
  A :root CSS block of type-scale custom properties (fluid clamp() per step),
  correct self-hosted @font-face rules (WOFF2, font-display, unicode-range,
  variable weight range), a zero-CLS fallback @font-face with metric overrides,
  and body-copy defaults (line-height, measure, feature settings).
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Typography Type System

Craft a complete, defensible type system: a modular scale, variable fonts wired
right, self-hosting, and CLS-free loading. This is the *type craft* layer. For the
raw fluid clamp() interpolation math (slope/intercept) lean on
**fluid-responsive-system**; this skill decides the ratios, the loading, and the
reading experience.

## When to use

Use when type feels arbitrary, when fonts flash/reflow, when you have too many
weight files, or when body copy is hard to read. Skip for pure colour, brand
typeface selection, or the bare clamp math (see when_not_to_use).

## Prerequisites

- No packages required for the CSS itself — it is vanilla CSS custom properties.
- To subset/convert fonts: `fonttools` (`pip install fonttools brotli`) gives
  `pyftsubset` for WOFF2 + unicode-range subsetting. Optional but recommended.
- To read a font's metrics for zero-CLS overrides: fontkit / opentype.js in Node,
  or look them up in the `@capsizecss/metrics` dataset. `scripts/fallback_metrics.py`
  turns those numbers into the CSS.
- Variable fonts: prefer a single variable WOFF2 (one file, all weights) — Inter,
  Roboto Flex, Source Serif 4, Fraunces all ship one.

## Recipe 1 — the modular scale

Pick ONE ratio and derive every step from a base. Common ratios: 1.2 (minor third,
tight/dense UI), 1.25 (major third, classic), 1.333 (perfect fourth, expressive
editorial). Step n = base * ratio^n.

```css
:root {
  /* base 18px, ratio 1.25; each step is fluid between a 360px and 1240px vw */
  --step--1: clamp(0.90rem, 0.86rem + 0.18vw, 1.00rem);  /* small / captions   */
  --step-0:  clamp(1.13rem, 1.06rem + 0.30vw, 1.25rem);  /* body               */
  --step-1:  clamp(1.41rem, 1.29rem + 0.53vw, 1.75rem);  /* h4                 */
  --step-2:  clamp(1.76rem, 1.55rem + 0.90vw, 2.44rem);  /* h3                 */
  --step-3:  clamp(2.20rem, 1.86rem + 1.47vw, 3.42rem);  /* h2                 */
  --step-4:  clamp(2.75rem, 2.20rem + 2.32vw, 4.78rem);  /* h1                 */
}
h1 { font-size: var(--step-4); } /* … */
p  { font-size: var(--step-0); }
```

Generate the exact clamp() values with the Utopia calculator (utopia.fyi) or the
**fluid-responsive-system** skill — a good move is a *tighter ratio on mobile*
(e.g. 1.2) widening to a bolder ratio on desktop (e.g. 1.333), which those tools
support directly. Do not hand-invent clamp numbers; derive them.

## Recipe 2 — self-hosted, subsetted, variable @font-face

```css
@font-face {
  font-family: "Inter";
  src: url("/fonts/inter-var-latin.woff2") format("woff2") tech(variations);
  font-weight: 100 900;          /* the whole weight AXIS in one file */
  font-style: normal;
  font-display: swap;            /* text visible immediately, swaps in */
  unicode-range: U+0000-00FF, U+2000-206F, U+2190-21FF, U+2212; /* latin subset */
}
body { font-family: "Inter", "InterFallback", system-ui, sans-serif; }
h1   { font-weight: 780; }       /* any value on the axis, not just 700 */
```

- **WOFF2 only** — supported everywhere; smallest. Convert/subset:
  `pyftsubset Inter.ttf --flavor=woff2 --unicodes="U+0000-00FF,U+2000-206F" \
   --layout-features='*' --output-file=inter-var-latin.woff2`
- **font-display**: `swap` for content (never invisible text); `optional` when
  performance outranks getting the exact font on first paint; `block` only for
  short brand headings above the fold.
- **Preload only the one font used in the first viewport**, and only when
  self-hosting from the same origin — it bypasses browser prioritisation, so do
  not preload every weight:
  `<link rel="preload" href="/fonts/inter-var-latin.woff2" as="font"
   type="font/woff2" crossorigin>`
- **Variable-font axes**: expose weight via `font-weight`, optical size via
  `font-optical-sizing: auto` (or explicit `font-variation-settings: "opsz" 32`),
  and custom axes (e.g. Fraunces `SOFT`, `WONK`) only through
  `font-variation-settings`. Do not fake bold with `font-synthesis`.

## Recipe 3 — zero-CLS fallback (the reflow killer)

`font-display: swap` shows a fallback, then swaps — which *reflows* unless the
fallback occupies the same box. Fix it with a metric-overridden fallback
`@font-face` so the fallback is pre-stretched to the web font's dimensions.

```
python3 scripts/fallback_metrics.py \
  --ascent 1950 --descent 494 --line-gap 0 --units-per-em 2048 \
  --web-avg 1017 --fallback-avg 977 --name InterFallback
```

Emits (read Inter's metrics from fontkit; Arial avg width 977 @ 2048 upm):

```css
@font-face {
  font-family: "InterFallback";
  src: local("Arial");
  size-adjust: 104.0942%;
  ascent-override: 91.4699%;
  descent-override: 23.1724%;
  line-gap-override: 0%;
}
```

Put `"InterFallback"` immediately after the real font in the stack (Recipe 2).
Before the WOFF2 arrives, Arial is resized to Inter's exact metrics; the swap is
invisible. This is what next/font and fontaine do under the hood.

## Recipe 4 — readable body copy

```css
p {
  font-size: var(--step-0);
  line-height: 1.6;              /* body: 1.5-1.65; tighten as size grows */
  max-width: 66ch;              /* measure: 45-75ch, ~66 ideal for reading */
  text-wrap: pretty;            /* avoids orphans/ragged last lines        */
  font-feature-settings: "kern", "liga", "calt"; /* on by default, be explicit */
}
h1, h2, h3 { line-height: 1.1; letter-spacing: -0.01em; text-wrap: balance; }
.tabular   { font-variant-numeric: tabular-nums; }   /* align figures in tables */
.fraction  { font-feature-settings: "frac"; }
```

Rules of thumb: line-height shrinks as font-size grows (display ~1.05-1.15, body
~1.5-1.65); negative letter-spacing only on large headings; positive tracking on
all-caps labels (`letter-spacing: 0.06em`). Use `tabular-nums` for any column of
numbers.

## Verify

- Smoke-test the helper:
  `python3 scripts/fallback_metrics.py --ascent 1950 --descent 494 --line-gap 0
   --units-per-em 2048 --web-avg 1017 --fallback-avg 977` → prints a valid
  `@font-face` block.
- **CLS**: DevTools → Performance → record a reload; the "Layout Shift" track for
  the font should be ~0. Or Lighthouse CLS < 0.1.
- **Network**: only WOFF2 files load; each subset is small; no unused weight files.
- **Rendering**: set DevTools network to Slow 3G — text appears instantly (swap)
  and does NOT jump when the font arrives (proves the fallback metrics).
- **Scale**: every heading/body size resolves to a `--step-*` token, none to a
  raw px literal.

## Pitfalls

- **`font-display: swap` alone still reflows** — you MUST pair it with the
  metric-overridden fallback (Recipe 3) or accept the shift. Swap fixes invisible
  text, not layout shift.
- **Preloading every weight** hurts more than it helps; preload one file max.
- **Shipping separate 400/500/600/700 files** when a variable font gives the whole
  axis in one download — check if your family has a variable build first.
- **`unicode-range` too narrow** drops glyphs (curly quotes U+2018-2019, en/em
  dashes U+2013-2014, ellipsis U+2026) → tofu boxes. Include punctuation ranges.
- **Fabricated clamp numbers** — derive them from a ratio (Utopia /
  fluid-responsive-system), never eyeball them.
- **`font-synthesis` faux-bold/italic** looks wrong on variable fonts; use real
  axis values (`font-weight: 780`) or a real italic file.
- **Fallback avg width must use the same unitsPerEm basis** as the web font in the
  script, or size-adjust is wrong. The `@capsizecss/metrics` dataset normalises
  this for you.
