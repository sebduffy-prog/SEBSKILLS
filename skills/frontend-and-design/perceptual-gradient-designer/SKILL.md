---
name: perceptual-gradient-designer
category: frontend-and-design
description: >-
  Design banding-free multi-stop gradients by interpolating in OKLab/OKLCH instead of
  naive sRGB — kills the grey dead-zone where blue→yellow or red→green go muddy, and kills
  the 8-bit staircase with dithered noise. Reach for this whenever a gradient looks washed
  out in the middle, shows visible bands on a large fill, or you need the SAME ramp as both
  a CSS `linear-gradient(in oklab, …)` one-liner AND a pixel-exact `<canvas>` render.
  Grounded on CSS Color 4 / CSS Images 4 and Ottosson's OKLab.
when_to_use:
  - A blue→yellow / red→green / complementary gradient goes grey or muddy in the middle
  - A large gradient fill (hero, background, splash) shows visible colour banding on-screen
  - You need one perceptual ramp emitted as BOTH CSS and a canvas/WebGL texture
  - Placing >2 stops so perceived brightness climbs evenly, not lumpily
  - Adding dither/noise to defeat 8-bit quantisation without a visible grain
when_not_to_use:
  - Even tint/shade scales or single-colour gamut mapping — use oklch-color-engine
  - Hue-rotated harmony sets (complementary/triad/analogous) — use color-harmony-generator
  - Only checking text-on-gradient contrast — use accessible-contrast-checker
  - Full-screen animated shader fields — use webgl-3d-scene or spectra-noise
keywords:
  - gradient
  - oklab
  - oklch
  - interpolation
  - banding
  - dithering
  - perceptual
  - color-space
  - css-color-4
  - linear-gradient
  - canvas
  - grey-dead-zone
  - multi-stop
  - color-mix
  - ottosson
similar_to:
  - oklch-color-engine
  - color-harmony-generator
  - colorblind-safe-palettes
  - motion-system
  - webgl-3d-scene
inputs_needed: Two or more stop colours (hex/rgb/oklch), a direction/angle, and the render target (CSS, canvas, or both)
produces: A CSS `linear-gradient(in oklab …)` string with midpoint hints, plus a self-contained JS module that renders the identical ramp to a `<canvas>` with dithering
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Perceptual Gradient Designer

Naive `linear-gradient(red, blue)` interpolates in **sRGB**, a non-perceptual space.
The straight line from red to blue passes near the grey axis, so the midpoint desaturates
into mud — the "grey dead-zone". Interpolating in **OKLab** (perceptually uniform, from
Ottosson 2020) keeps chroma up across the whole sweep, so the midpoint stays a vivid
purple. Two failure modes to defeat: the **dead-zone** (fixed by colour space) and
**banding** (8-bit staircase on big fills, fixed by dithering). This skill produces the
same ramp two ways so CSS and canvas match.

## When to use

Use it when a gradient's *middle* looks wrong (washed/grey) or its *surface* looks wrong
(visible stripes). If the endpoints are fine and only the ramp math matters, this is the
skill. For single-colour scales or gamut clamping, drop to `oklch-color-engine`.

## Prerequisites

- Modern browser for the CSS path (Chrome 111+, Safari 16.2+, Firefox 128+ ship
  `linear-gradient(in oklab …)` and `color-mix(in oklab …)`). Provide an sRGB fallback.
- Node 18+ (or any browser console) to run the JS module. No packages — the OKLab math is
  inlined. `node --version` to confirm.

## Recipe 1 — CSS one-liner (the fast path)

Set the interpolation space with `in <space>` **after** the angle, **before** the stops.
Rectangular spaces (`oklab`, `srgb`, `display-p3`): no hue keyword. Polar spaces
(`oklch`, `hsl`): add `shorter hue` (default) / `longer hue` / `increasing hue` /
`decreasing hue`.

```css
.hero {
  /* fallback for old engines — MUST come first */
  background: linear-gradient(90deg, #ff2d55, #0a84ff);
  /* perceptual override — vivid purple midpoint, no grey */
  background: linear-gradient(90deg in oklab, #ff2d55, #0a84ff);
}
```

Pick the space by intent:

- **`in oklab`** — the safe default. Shortest perceptual path, never loops through unwanted
  hues. Use for two-stop and most multi-stop ramps.
- **`in oklch longer hue`** — deliberately sweep *through* the wheel (red → green *via*
  yellow/orange), rainbow/spectrum effects.
- **`in oklch shorter hue`** — perceptual but takes the short arc; near-identical to oklab
  for adjacent hues, differs when stops are far apart on the wheel.

Move a midpoint with a bare-percentage **colour hint** between two stops (shifts the 50%
crossover without adding a stop):

```css
/* crossover pushed to 35% so the blue half dominates */
background: linear-gradient(90deg in oklab, #ff2d55, 35%, #0a84ff);
```

`color-mix()` gives you a single sampled point on the same ramp (great for tokens/borders):

```css
--mid: color-mix(in oklab, #ff2d55, #0a84ff);        /* 50/50 */
--q3:  color-mix(in oklab, #ff2d55 25%, #0a84ff 75%); /* 75% toward blue */
```

## Recipe 2 — Pixel-exact canvas render (kills banding)

CSS gives you no control over the 8-bit staircase. On big fills you'll see bands. Render the
ramp yourself in OKLab and add ordered dithering so quantisation error scatters below the
perception threshold. This module reproduces `in oklab` exactly, then adds noise.

```js
// oklab-gradient.js — self-contained, no deps. Ottosson coefficients.
const srgbToLin = c => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const linToSrgb = c => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055);

function hexToOklab(hex) {
  const n = parseInt(hex.replace('#', ''), 16);
  const r = srgbToLin(((n >> 16) & 255) / 255);
  const g = srgbToLin(((n >> 8) & 255) / 255);
  const b = srgbToLin((n & 255) / 255);
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return {
    L: 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    a: 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    b: 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  };
}

function oklabToRgb({ L, a, b }) {
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const r = linToSrgb(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s);
  const g = linToSrgb(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s);
  const bl = linToSrgb(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s);
  return [r, g, bl]; // still 0..1 float, may be out of gamut
}

// 4x4 Bayer matrix, normalised to [-0.5, 0.5] — the anti-banding dither.
const BAYER = [0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5].map(v => v / 16 - 0.5);

// stops: [{ at: 0..1, hex }], sorted. Renders a WxH horizontal ramp into ctx.
function renderGradient(ctx, w, h, stops) {
  const lab = stops.map(s => ({ at: s.at, c: hexToOklab(s.hex) }));
  const img = ctx.createImageData(w, h);
  for (let x = 0; x < w; x++) {
    const t = x / (w - 1);
    let i = 0;
    while (i < lab.length - 2 && t > lab[i + 1].at) i++;
    const seg = (t - lab[i].at) / (lab[i + 1].at - lab[i].at);
    const A = lab[i].c, B = lab[i + 1].c;
    const rgb = oklabToRgb({
      L: A.L + (B.L - A.L) * seg,
      a: A.a + (B.a - A.a) * seg,
      b: A.b + (B.b - A.b) * seg,
    });
    for (let y = 0; y < h; y++) {
      const d = BAYER[(y & 3) * 4 + (x & 3)] / 255; // ±0.5 LSB of dither
      const o = (y * w + x) * 4;
      for (let k = 0; k < 3; k++) {
        img.data[o + k] = Math.max(0, Math.min(255, Math.round(rgb[k] * 255 + d)));
      }
      img.data[o + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
}
```

Drive it:

```js
const canvas = document.querySelector('canvas');
const ctx = canvas.getContext('2d');
renderGradient(ctx, canvas.width, canvas.height, [
  { at: 0, hex: '#ff2d55' },
  { at: 0.5, hex: '#7c3aed' }, // explicit midpoint stop
  { at: 1, hex: '#0a84ff' },
]);
```

## Recipe 3 — Even perceptual stop placement

When you add intermediate stops, place them by **equal steps in OKLab L**, not by eyeballing
hex. Sample the endpoints' L, then position each stop where the CSS/canvas ramp already has
that L — because OKLab L *is* perceived lightness, evenly spaced `at:` values already climb
evenly. The trap is picking intermediate *hex* colours whose L jumps: compute
`hexToOklab(hex).L` for every stop and confirm the L values are monotonic and roughly even
before shipping. If one stop's L spikes, the gradient will show a bright/dark "pinch" there.

## Verify

1. **Dead-zone check (CSS):** render `linear-gradient(90deg, #ff0, #00f)` beside
   `linear-gradient(90deg in oklab, #ff0, #00f)`. The plain one greys out mid-sweep; the
   oklab one stays saturated through purple. If they look identical, the browser dropped the
   `in oklab` (check support / that the fallback line isn't winning).
2. **Banding check (canvas):** render a wide, near-black-to-dark gradient (`#0a0a12 → #14203a`)
   full-width. Zoom in — with `BAYER` dithering on you should see fine speckle, no hard
   stripes. Comment out the `+ d` term and the stripes reappear.
3. **Round-trip the math (Node):** `hexToOklab` → `oklabToRgb` on `#ff2d55` must return the
   original ±0.004 per channel. Paste both functions into `node` and check
   `oklabToRgb(hexToOklab('#ff2d55')).map(c=>Math.round(c*255))` → `[255, 45, 85]`.
4. **Parity:** sample the canvas midpoint pixel and compare to CSS `color-mix(in oklab, …)`
   at 50% — they should match within ±1/255 (dither aside).

## Pitfalls

- **Fallback ordering.** The plain sRGB `background:` MUST come first; the `in oklab` line
  overrides it in supporting engines. Reverse them and modern browsers keep the muddy one.
- **`in oklch` without a hue keyword loops the long way** only if you asked for `longer hue`.
  Default is `shorter hue`. If a two-colour gradient unexpectedly rainbows, you set `longer`.
- **Out-of-gamut after interpolation.** OKLab midpoints of two in-gamut colours can land
  outside sRGB. The clamp in `renderGradient` (`min/max 0..255`) is a blunt clip that can
  shift hue slightly. For critical work, gamut-map with `oklch-color-engine` before drawing.
- **Dither too strong = visible grain.** Bayer at ±0.5 LSB is the sweet spot. Scaling `d`
  up to hide bad banding means your real problem is too few bits — render at higher bit depth
  or reduce the gradient's contrast range instead.
- **Don't interpolate in linear-sRGB thinking it's "perceptual".** Linear-light fixes
  *blending/compositing*, not perceived-uniform *hue paths*. It still dead-zones. OKLab is the
  space that keeps chroma up.
- **`color-mix` percentages are toward the second colour.** `color-mix(in oklab, A 25%, B)`
  is 25% A / 75% B — mostly B. Easy to invert.
