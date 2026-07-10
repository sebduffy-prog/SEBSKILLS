---
name: color-harmony-generator
category: frontend-and-design
description: >-
  Generate complementary, analogous, triadic, split-complementary, tetradic and
  square colour harmonies by rotating hue in OKLCH so every swatch stays equally
  light and equally saturated — unlike HSL, where a hue spin makes yellow washed
  out and blue muddy. Holds L and C fixed, rotates H by fixed degrees, then
  clamps chroma PER HUE because the sRGB boundary changes with angle. Reach for
  this to turn one brand colour into a balanced, usable multi-hue palette with
  correct CSS oklch() output. Grounded on culori + CSS Color 4.
when_to_use:
  - Turning a single brand or seed colour into a complementary/triad/analogous set
  - Building an accent + secondary palette where every hue reads equally vivid
  - Picking data-series colours that are evenly spaced round the perceptual wheel
  - Generating split-complementary or tetradic schemes for illustration/marketing
  - Fixing an HSL harmony where the rotated hues look uneven in lightness
when_not_to_use:
  - Building a single-hue tint/shade ramp (50–950) — use oklch-color-engine
  - Only checking text/background contrast ratios — use accessible-contrast-checker
  - Verifying a set survives colour-vision deficiency — use colorblind-safe-palettes
  - Managing named tokens across light/dark themes — use brand-color-token-system
  - Extracting a palette from a photo — use image-palette-extraction
keywords:
  - color-harmony
  - complementary
  - analogous
  - triadic
  - split-complementary
  - tetradic
  - square
  - oklch
  - hue-rotation
  - culori
  - palette
  - clampchroma
  - color-wheel
  - css-color-4
  - perceptual
similar_to:
  - oklch-color-engine
  - perceptual-gradient-designer
  - colorblind-safe-palettes
  - brand-color-token-system
  - color-psychology-advertising
inputs_needed: One seed colour (hex, rgb, hsl, named, or oklch) and a scheme name (complementary, analogous, triadic, split, tetradic, square)
produces: A set of gamut-safe CSS oklch() strings — one per harmony hue — plus a reusable JS generator that clamps chroma per hue
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Colour Harmony Generator

A harmony is a set of hues at fixed angular offsets on the colour wheel. The
trick most tools get wrong: they rotate hue in **HSL**, where equal hue steps
produce wildly *unequal* perceived lightness — HSL yellow (`hsl(60 100% 50%)`)
looks far brighter than HSL blue (`hsl(240 100% 50%)`) despite identical S and L.
Do the rotation in **OKLCH** instead: hold **L** (perceptual lightness) and **C**
(chroma) constant, rotate only **H**, and every swatch comes out equally light
and equally saturated. Then clamp chroma per hue, because the sRGB gamut edge is
closer to grey at some angles (blue) than others (green).

## When to use

Use it the moment you have *one* colour and need *several* that belong together —
an accent's complement, a triad for a chart, an analogous run for a gradient's
anchor stops. If you instead need many shades of a *single* hue, that's a tint
ramp — use `oklch-color-engine`. If you only need a contrast number, use
`accessible-contrast-checker`.

## Prerequisites

- **CSS-only path** needs nothing: `oklch()` ships in all evergreen browsers
  (Chrome/Edge 111+, Safari 16.4+, Firefox 113+). You can hand-write rotated
  hues once you know the base L/C/H.
- **Programmatic path** uses [culori](https://culorijs.org) (MIT):
  ```bash
  npm i culori          # full build, all colour modes pre-registered
  ```
  Node 18+; runs in the browser too.

## The offset table

Each scheme is just base hue **H** plus these degree offsets (hue is circular —
always `mod 360`):

| Scheme                | Hue offsets (°)        | Swatches |
|-----------------------|------------------------|----------|
| complementary         | `0, 180`               | 2        |
| analogous             | `-30, 0, +30`          | 3        |
| triadic               | `0, 120, 240`          | 3        |
| split-complementary   | `0, 150, 210`          | 3        |
| tetradic (rectangle)  | `0, 60, 180, 240`      | 4        |
| square                | `0, 90, 180, 270`      | 4        |

## Recipes

### 1. Hand-written CSS harmony (zero JS)

Convert the seed to OKLCH once (recipe 2 or any converter), then reuse its L and
C and only change the hue number. Seed `#e11d48` → `oklch(0.64 0.23 18)`:

```css
:root {
  --seed:      oklch(0.64 0.23 18);   /* crimson, H = 18 */
  --triad-b:   oklch(0.64 0.23 138);  /* +120 → green   */
  --triad-c:   oklch(0.64 0.23 258);  /* +240 → blue    */
}
```

Because L is held at 0.64 for all three, they read as the *same weight* — none
jumps forward or recedes the way an HSL triad would. Note the blue may need its
chroma trimmed (recipe 3); `0.23` is safe here but verify per hue.

### 2. Seed → OKLCH object (culori)

```js
import { oklch, formatCss } from 'culori';

const seed = oklch('#e11d48');
// ⇒ { mode:'oklch', l:0.64…, c:0.23…, h:18… }
formatCss(seed);                 // 'oklch(0.64 0.23 18)'
```

`oklch()` parses hex, `rgb()`, `hsl()`, CSS named colours, or an existing
`oklch(…)` string. A **neutral grey has `h: undefined`** — a harmony of grey is
meaningless, so bail out early if the seed has no hue.

### 3. Generator that clamps chroma per hue (the correct way)

The seed's chroma may be reachable at hue 18 but out of sRGB at hue 258. Clamp
**each rotated colour independently** so none silently clips to a duller,
lightness-shifted value on render:

```js
import { oklch, clampChroma, formatCss } from 'culori';

const SCHEMES = {
  complementary: [0, 180],
  analogous:     [-30, 0, 30],
  triadic:       [0, 120, 240],
  split:         [0, 150, 210],
  tetradic:      [0, 60, 180, 240],
  square:        [0, 90, 180, 270],
};

function harmony(input, scheme = 'triadic') {
  const base = oklch(input);
  if (!base) throw new Error(`Unparseable colour: ${input}`);
  if (base.h === undefined) throw new Error('Seed is achromatic — no hue to rotate');
  const offsets = SCHEMES[scheme];
  if (!offsets) throw new Error(`Unknown scheme: ${scheme}`);

  return offsets.map((deg) => {
    const rotated = { ...base, h: (base.h + deg + 360) % 360 };
    // clampChroma reduces C until the colour fits sRGB, keeping L and H exact
    const safe = clampChroma(rotated, 'oklch', 'rgb');
    return formatCss({ ...safe, l: round(safe.l), c: round(safe.c), h: round(safe.h) });
  });
}

const round = (n) => Math.round(n * 1000) / 1000;

harmony('#e11d48', 'triadic');
// ⇒ [ 'oklch(0.64 0.23 18)', 'oklch(0.64 0.19 138)', 'oklch(0.64 0.21 258)' ]
//   note the green/blue chroma trimmed to stay in gamut — L stays 0.64 for all
```

Immutable throughout: `{ ...base, h }` and `{ ...safe, … }` never mutate the
parsed seed, so you can reuse `base` for every offset.

### 4. Wide-gamut variant (Display-P3)

Same code, wider target — swap the gamut argument so P3-capable hues keep more
punch, then still emit an sRGB fallback first:

```js
const safeP3 = clampChroma(rotated, 'oklch', 'p3');   // clamp to Display-P3
```

```css
.accent { background: oklch(0.64 0.19 138); }              /* sRGB-clamped */
@supports (color: color(display-p3 1 1 1)) {
  .accent { background: oklch(0.64 0.24 138); }            /* fuller P3 */
}
```

### 5. Nudge for role, not just hue

A raw harmony gives you hues; a *usable* palette often wants the secondaries
slightly quieter. After rotating, drop chroma ~15–25% on non-seed swatches so the
seed stays the hero — do it *after* the per-hue clamp so you never re-inflate
past the gamut edge:

```js
const supporting = { ...safe, c: safe.c * 0.8 };
```

## Verify

- **Equal lightness holds.** Parse every output back through `oklch()` and assert
  all `l` values match the seed's (± rounding). If one drifted, a clamp changed L
  — you clamped in the wrong space (e.g. RGB), not OKLCH.
- **Everything is in gamut.** `import { inGamut } from 'culori'; const ok = inGamut('rgb');`
  then `offsets.map(...).every(c => ok(c))` must be `true`.
- **Eyeball on a neutral swatch board.** Render the set as adjacent tiles on both
  `#fff` and `#111`; a correct OKLCH harmony reads balanced on both, an HSL one
  visibly see-saws in weight.
- **CSS renders.** Paste an output string into any evergreen browser devtools
  colour swatch — it must resolve, not fall back to black.

## Pitfalls

- **Rotating in HSL/hex.** This is the whole reason the skill exists. Equal hue
  steps in HSL give unequal lightness; the palette looks lopsided. Always rotate
  in OKLCH.
- **Clamping once, for the seed only.** Chroma valid at the seed hue can clip at
  the complement. Clamp *each* rotated colour — recipe 3.
- **Clamping in the wrong space.** `clampChroma(c, 'oklch', …)` preserves L and H
  and only lowers C. A generic RGB clamp or naive `Math.min` on channels shifts
  lightness and hue — defeating the point.
- **Achromatic seed.** Grey/white/black have `h: undefined`; rotating undefined
  yields `NaN`. Guard before generating (recipe 3 throws).
- **Forgetting `mod 360`.** `base.h + 240` can exceed 360; `oklch()` tolerates
  it but keep hues normalised for clean, comparable output.
- **Tree-shaken culori.** `import 'culori'` registers all modes. If you import
  from `culori/fn`, you must `useMode(modeOklch)` and register the rgb/p3 gamuts
  yourself or `clampChroma`/`inGamut` silently misbehave.
- **Analogous spacing too tight.** ±30° is the default; below ~±15° the hues are
  nearly indistinguishable. Widen the offset if the set needs to read as distinct.
