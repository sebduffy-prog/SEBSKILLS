---
name: oklch-color-engine
category: frontend-and-design
description: >-
  Do perceptually-uniform colour work in OKLCH/OKLab — parse any input, convert
  to OKLCH, build even lightness/chroma ramps, interpolate gradients without grey
  dead-zones, and gamut-map so every stop stays inside sRGB or Display-P3 before
  you emit CSS oklch(). Reach for this whenever HSL/hex maths gives muddy midpoints,
  uneven tint scales, or colours that clip on wide-gamut screens. Grounded on
  culori + CSS Color 4.
when_to_use:
  - Building a tint/shade scale (50–950) that must step evenly in perceived lightness
  - Interpolating a gradient or data-viz ramp that goes grey/muddy in HSL or hex
  - Shifting hue/lightness/chroma of a brand colour while keeping it on-screen
  - Deciding whether a colour fits sRGB vs Display-P3 and clamping it if not
  - Emitting production CSS oklch() / color(display-p3 …) with correct fallbacks
when_not_to_use:
  - Only checking text/background contrast ratios — use accessible-contrast-checker
  - Generating hue-rotated harmony sets (complementary/triad) — use color-harmony-generator
  - Managing named design tokens across themes — use brand-color-token-system
  - Verifying palettes for CVD safety — use colorblind-safe-palettes
keywords:
  - oklch
  - oklab
  - color
  - gamut
  - culori
  - interpolate
  - gradient
  - lightness
  - chroma
  - hue
  - srgb
  - display-p3
  - css-color-4
  - perceptual
  - tint-scale
  - clampchroma
similar_to:
  - perceptual-gradient-designer
  - color-harmony-generator
  - brand-color-token-system
  - accessible-contrast-checker
  - colorblind-safe-palettes
inputs_needed: One or more source colours (hex, rgb, hsl, named, or oklch strings) and a target gamut (srgb or p3)
produces: CSS oklch()/color() strings, even lightness ramps, gamut-mapped gradient stops, and a reusable JS colour util
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# OKLCH Colour Engine

OKLCH is OKLab in cylindrical form: **L** = perceptual lightness (0–1), **C** =
chroma (0 → ~0.37+, unbounded), **H** = hue angle (0–360°). Unlike HSL, equal L
steps look equally light and interpolation never dips through grey. This skill
does the parse → OKLCH → manipulate → gamut-map → serialise pipeline correctly.

## When to use

Use it the moment you need colour *maths* rather than colour *lookup*: even tint
scales, clean gradients, hue/lightness nudges, and sRGB-vs-P3 clamping. If you
only need a contrast number or a fixed harmony set, use the sibling skill named
in the frontmatter instead.

## Prerequisites

- **CSS-only path** needs nothing — `oklch()` and `color(display-p3 …)` ship in
  all current evergreen browsers (Chrome/Edge 111+, Safari 16.4+, Firefox 113+).
- **Programmatic path** uses [culori](https://culorijs.org) (MIT). Install:
  ```bash
  npm i culori          # full build, all modes pre-registered
  ```
  For tree-shaken bundles import from `culori/fn` and register modes yourself
  (see Pitfalls). Node 18+; works in the browser too.

## Recipes

### 1. CSS-native, zero-JS lightness ramp

Hold H and C fixed, walk L in even steps. This is the whole trick behind a good
tint scale — no build step required:

```css
:root {
  /* brand hue 264, chroma 0.13; only L changes */
  --brand-50:  oklch(0.97 0.03 264);
  --brand-200: oklch(0.90 0.07 264);
  --brand-400: oklch(0.72 0.13 264);
  --brand-600: oklch(0.55 0.15 264);
  --brand-800: oklch(0.40 0.12 264);
  --brand-950: oklch(0.25 0.07 264);
}
```

Wide-gamut colours degrade gracefully — put the sRGB fallback first, P3 second:

```css
.accent { background: oklch(0.68 0.20 150); }               /* clamped to sRGB */
@supports (color: color(display-p3 1 1 1)) {
  .accent { background: color(display-p3 0.34 0.79 0.42); } /* fuller P3 */
}
```

Interpolate *in* OKLCH so a CSS gradient stays vivid through its midpoint:

```css
background: linear-gradient(in oklch, oklch(0.7 0.18 30), oklch(0.7 0.18 300));
/* use `in oklch longer hue` to sweep the long way round the wheel */
```

### 2. Parse anything → OKLCH object (culori)

```js
import { oklch, formatCss } from 'culori';

const c = oklch('#3b82f6');
// ⇒ { mode: 'oklch', l: 0.62…, c: 0.19…, h: 258… }
formatCss(c);                    // 'oklch(0.62 0.19 258)'  (CSS Color 4 syntax)
```

`oklch()` accepts hex, `rgb()`, `hsl()`, CSS named colours, or an existing
`oklch(…)` string. A neutral grey returns `h: undefined` — guard for that before
doing hue maths.

### 3. Even tint scale by fixing hue + chroma, sampling L

```js
import { interpolate, samples, formatCss, oklch } from 'culori';

const base = oklch('#e11d48');                 // crimson
const light = { ...base, l: 0.97, c: 0.03 };
const dark  = { ...base, l: 0.25, c: 0.10 };

const ramp = interpolate([light, base, dark], 'oklch');
const stops = [50,100,200,300,400,500,600,700,800,900,950];
const scale = samples(stops.length).map(ramp).map(formatCss);
// pair stops[i] ↔ scale[i]; every step moves ~equal perceived lightness
```

`samples(n)` returns `n` evenly-spaced `t` values in `[0,1]` (e.g. `samples(3)`
→ `[0, 0.5, 1]`); mapping them through the interpolator yields the stops.

### 4. Gradient interpolation that never goes grey

Interpolating two saturated colours in sRGB/hex passes through a desaturated
midpoint. In OKLCH it stays chromatic. Control the hue path explicitly:

```js
import {
  interpolate, samples, formatHex,
  interpolatorLinear, fixupHueShorter, fixupHueLonger
} from 'culori';

const grad = interpolate(['#ffd500', '#0057ff'], 'oklch', {
  h: { use: interpolatorLinear, fixup: fixupHueShorter }  // shortest hue arc
});
const hexStops = samples(9).map(grad).map(formatHex);
```

Swap `fixupHueShorter` → `fixupHueLonger` to rotate the long way; without a fixup,
culori won't normalise the ±360° ambiguity and hue can jump.

### 5. Gamut-map into sRGB or Display-P3

Raising chroma or converting from P3 can push a colour outside the target gamut.
Never hard-clip RGB channels (that shifts hue) — reduce chroma while holding L and
H. `toGamut` runs the **CSS Color 4 gamut-mapping algorithm** by default (binary
search on chroma in OKLCH, deltaE-OK with a JND of ~0.02, plus local clipping):

```js
import { toGamut, inGamut, clampChroma, formatCss } from 'culori';

const wild = 'oklch(0.72 0.30 150)';           // too chromatic for sRGB
inGamut('rgb')(wild);                          // ⇒ false

const toSrgb = toGamut('rgb', 'oklch');        // CSS algorithm, hue-preserving
formatCss(toSrgb(wild));                        // in-gamut oklch()

const toP3 = toGamut('p3', 'oklch');           // wider target keeps more chroma
formatCss(toP3(wild));

// Lighter-weight alternative: pure chroma clamp (no deltaE step)
formatCss(clampChroma(wild, 'oklch', 'rgb'));
```

Rule of thumb: `toGamut` for final render fidelity, `clampChroma` when you just
need a fast in-gamut result and don't care about the last fraction of a JND.

### 6. Snap an arbitrary colour to your brand palette

```js
import { nearest, differenceEuclidean } from 'culori';

const palette = { Brand:'#e11d48', Ink:'#111827', Sky:'#0ea5e9', Sand:'#f5e9d3' };
const match = nearest(Object.keys(palette), differenceEuclidean('oklch'),
                      name => palette[name]);
match('#ff0040', 1);   // ⇒ ['Brand']  — nearest in OKLab, not RGB
```

## Verify

Sanity-check with a throwaway script (no repo needed):

```bash
cd "$(mktemp -d)" && npm i --silent culori >/dev/null 2>&1
node --input-type=module -e '
import { oklch, interpolate, samples, toGamut, inGamut, formatCss } from "culori";
const ramp = interpolate([{mode:"oklch",l:.95,c:.04,h:264},
                          {mode:"oklch",l:.30,c:.09,h:264}], "oklch");
const stops = samples(5).map(ramp);
const Ls = stops.map(s => +s.l.toFixed(3));
console.log("L steps:", Ls);                       // must be monotonically DOWN
const g = toGamut("rgb","oklch")("oklch(0.72 0.30 150)");
console.log("mapped:", formatCss(g), "inGamut:", inGamut("rgb")(g)); // → true
'
```

Pass criteria: the L values decrease smoothly and evenly, and the mapped colour
reports `inGamut: true`. In a browser, paste an `oklch()` value into DevTools'
colour picker — it round-trips and shows the gamut boundary.

## Pitfalls

- **Tree-shaken import returns undefined.** With `culori/fn` you must register
  modes: `import { useMode, modeOklch } from 'culori/fn'; const oklch = useMode(modeOklch);`.
  The plain `culori` entry has them pre-registered — prefer it unless bundle size
  is critical.
- **Grey has no hue.** Achromatic inputs give `h: undefined`; `{...c, h: 264}`
  before interpolating, or hue fixups silently no-op.
- **Chroma is not a percentage.** OKLCH C is an open-ended number (~0–0.4 in
  practice), not 0–100%. A "vivid" colour is ~0.15–0.25; above ~0.32 nothing is
  sRGB-displayable at mid lightness.
- **Don't clip RGB to fix out-of-gamut.** Channel clipping distorts hue and
  lightness. Always reduce chroma (`toGamut`/`clampChroma`) instead.
- **`in oklch` gradients need modern browsers.** The CSS `linear-gradient(in oklch,…)`
  interpolation is Chrome 111+/Safari 16.2+/Firefox 113+; for older targets
  pre-compute stops with culori (recipe 4) and emit a plain multi-stop gradient.
- **P3 fallback ordering.** Declare the sRGB `oklch()` value first and the
  `color(display-p3 …)` inside `@supports` second, or non-P3 browsers render nothing.
