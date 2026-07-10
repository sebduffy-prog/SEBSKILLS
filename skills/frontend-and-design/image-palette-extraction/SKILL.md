---
name: image-palette-extraction
category: frontend-and-design
description: >-
  Extract a dominant palette from a photo, poster, or logo and turn it into a
  usable theme — quantise pixels (median-cut, k-means/WSMeans, or Celebi = Wu
  then WSMeans), rank swatches with Material's Score, pick a source colour, then
  derive a Material-You / Material Design 3 dynamic scheme (light + dark tonal
  palettes) emitted as CSS custom properties. Reach for this whenever you need
  "colours from this image", album-art theming, a logo-driven brand ramp, or a
  wallpaper-adaptive UI. Grounded on material-color-utilities (TS + Python).
when_to_use:
  - Deriving primary/accent colours from album art, a hero photo, or a wallpaper
  - Turning an uploaded logo into a full light + dark theme automatically
  - Ranking the N most "theme-worthy" colours in an image, not just most frequent
  - Building Material Design 3 tonal palettes + surface/on-colour token sets
  - Emitting --md-sys-color-* CSS variables that flip on prefers-color-scheme
when_not_to_use:
  - You already have a source hex and only need even tint/shade ramps — use oklch-color-engine
  - Rotating one colour into complementary/triad harmonies — use color-harmony-generator
  - Only checking text/background contrast ratios — use accessible-contrast-checker
  - Managing named tokens across many brands/themes — use brand-color-token-system
  - Ensuring a palette is CVD-safe — use colorblind-safe-palettes
keywords:
  - palette
  - quantize
  - median-cut
  - k-means
  - celebi
  - material-you
  - material-design-3
  - dominant-color
  - source-color
  - dynamic-scheme
  - tonal-palette
  - album-art
  - hct
  - score
  - wsmeans
  - css-variables
similar_to:
  - oklch-color-engine
  - color-harmony-generator
  - brand-color-token-system
  - accessible-contrast-checker
  - colorblind-safe-palettes
inputs_needed: An image file or URL (photo, poster, logo, screenshot, album art) and a target — raw palette, a source colour, or a full light/dark theme
produces: Ranked ARGB/hex swatches, a chosen source colour, Material Design 3 tonal palettes, and light+dark CSS custom-property token sets
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Image Palette Extraction → Dynamic Theme

Two jobs, in order. **(1) Quantise** — reduce millions of pixels to a small set of
representative colours. **(2) Theme** — rank those colours, pick a *source*, and
expand it into a Material Design 3 dynamic scheme (full tonal palettes for light
and dark). Material's own pipeline is **Celebi** (`Wu` histogram cut → `WSMeans`
k-means refine) → **Score** (ranks by chroma + population, avoids near-greys and
over-similar hues) → **DynamicScheme** (source colour → primary/secondary/tertiary/
neutral tonal palettes → surface & on-colour tokens).

## When to use

Use this when the *input is an image* and you want colour out. If you already hold
a hex and just need scales, gradients, or harmonies, use the sibling colour skills.

## Prerequisites

- **Browser / Node:** `npm i @material/material-color-utilities` (the canonical M3 lib).
- **Python (true Celebi + M3):** `pip3 install materialyoucolor` — ships prebuilt
  wheels incl. macOS; C++ quantiser backend. Verified against the T-Dynamos port.
- **Python zero-native fallback:** just `Pillow` (already present) — median-cut via
  `Image.quantize()` plus a tiny k-means. Use when the native wheel won't install.
- Source colour is one ARGB `int` (`0xAARRGGBB`). Convert hex with the lib helpers.

## Recipe A — Browser/Node: image → theme → CSS vars (Material's happy path)

```js
import {
  sourceColorFromImage, themeFromSourceColor, applyTheme,
  argbFromHex, hexFromArgb, QuantizerCelebi, Score, Hct,
} from '@material/material-color-utilities';

// 1. Easiest: let the lib quantise + Score + pick the source in one call.
const img = document.querySelector('img');       // must be loaded & same-origin/CORS-ok
const source = await sourceColorFromImage(img);   // -> ARGB int of best theme colour

// 2. Expand source into a full M3 theme (optionally blend in brand colours).
const theme = themeFromSourceColor(source, [
  { name: 'brand', value: argbFromHex('#e4002b'), blend: true },
]);

// 3. Paint --md-sys-color-* custom properties onto <body>, honouring dark mode.
const dark = matchMedia('(prefers-color-scheme: dark)').matches;
applyTheme(theme, { target: document.body, dark });

// theme.schemes.light / .dark expose every role; read one:
console.log('primary', hexFromArgb(theme.schemes[dark ? 'dark' : 'light'].primary));
```

**Want the ranked palette yourself** (e.g. to show swatches)? Do the two steps by hand:

```js
// pixels: Int32Array/array of ARGB ints from a <canvas> getImageData pass.
function argbPixels(canvas) {
  const { data } = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height);
  const out = [];
  for (let i = 0; i < data.length; i += 4) {
    if (data[i + 3] < 255) continue;              // skip transparent (logo backgrounds)
    out.push((255 << 24) | (data[i] << 16) | (data[i + 1] << 8) | data[i + 2]);
  }
  return out;
}
const counts = QuantizerCelebi.quantize(argbPixels(canvas), 128); // Map<argb, population>
const ranked = Score.score(counts);               // number[] — best theme colours first
const swatches = ranked.map(hexFromArgb);         // ['#0b57d0', ...]
```

## Recipe B — Python: true Celebi + Score + Material Design 3 scheme

```python
from materialyoucolor.quantize import ImageQuantizeCelebi        # C++ backend
from materialyoucolor.score.score import Score
from materialyoucolor.hct import Hct
from materialyoucolor.scheme.scheme_tonal_spot import SchemeTonalSpot
from materialyoucolor.dynamiccolor.material_dynamic_colors import MaterialDynamicColors
from materialyoucolor.dynamiccolor.color_spec import COLOR_NAMES

# 1. Quantise: quality=1 = every pixel (raise to 5–10 for big images), max 128 colours.
#    Returns {argb_int: population}.
counts = ImageQuantizeCelebi("cover.jpg", 1, 128)

# 2. Score → ranked list of ARGB ints; [0] is the strongest theme colour.
ranked = Score.score(counts)
source = ranked[0]

def hexi(argb): return "#%06X" % (argb & 0xFFFFFF)
print("palette:", [hexi(c) for c in ranked])
print("source:", hexi(source))

# 3. Build a dynamic scheme (9 variants: TonalSpot=Android default, Vibrant,
#    Expressive, Neutral, Monochrome, Fidelity, Content, Rainbow, FruitSalad).
def build(dark: bool):
    scheme = SchemeTonalSpot(Hct.from_int(source), dark, 0.0, spec_version="2025")
    mdc = MaterialDynamicColors(spec="2025")
    return {name: getattr(mdc, name).get_hex(scheme) for name in COLOR_NAMES}

light, dark = build(False), build(True)
print("light primary:", light["primary"], "| dark primary:", dark["primary"])
```

Emit both maps as a stylesheet — one `:root` block, one dark override:

```python
def css_block(sel, tokens):
    lines = [f"  --md-sys-color-{k}: {v.rstrip('F')[:7] if len(v)==9 else v};" for k, v in tokens.items()]
    return f"{sel} {{\n" + "\n".join(lines) + "\n}"

css = css_block(":root", light) + "\n" + \
      "@media (prefers-color-scheme: dark) {\n" + css_block(":root", dark) + "\n}"
open("theme.css", "w").write(css)   # get_hex returns #RRGGBBAA; trim the alpha above
```

## Recipe C — Zero-native-dependency fallback (Pillow only)

When the `materialyoucolor` wheel can't build (odd platform), quantise with Pillow's
median-cut and refine the top colours with a compact k-means. No Material scheme, but
you still get a clean ranked palette + a source colour.

```python
from PIL import Image
from collections import Counter

def extract_palette(path, k=8, resize=128):
    im = Image.open(path).convert("RGB")
    im.thumbnail((resize, resize))                       # cheap: cap work at ~16k px
    # MEDIANCUT is Pillow's built-in median-cut quantiser (MAXCOVERAGE / FASTOCTREE also exist).
    pal = im.quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    rgb = pal.convert("RGB")
    counts = Counter(rgb.getdata())                      # {(r,g,b): population}
    # Rank median-cut-ish: population weighted by colourfulness (avoid flat greys).
    def chroma(c): return max(c) - min(c)
    ranked = sorted(counts, key=lambda c: counts[c] * (1 + chroma(c) / 255), reverse=True)
    return ["#%02X%02X%02X" % c for c in ranked]

print(extract_palette("cover.jpg"))
```

Median-cut vs k-means vs Celebi, in one breath: **median-cut** recursively splits the
colour box along its longest axis (fast, deterministic, Pillow-native); **k-means /
WSMeans** iteratively moves cluster centroids to pixel means (tighter clusters, needs
seeding); **Celebi** seeds k-means from a Wu histogram cut — best of both, and what
Material ships. **Score** is the extra step that makes results *theme-worthy* rather
than merely frequent (it down-weights near-grey and hue-duplicate clusters).

## Verify

- **JS:** `hexFromArgb(source)` returns a plausible dominant hex; `theme.schemes.light`
  and `.dark` are populated; after `applyTheme`, `getComputedStyle(document.body)
  .getPropertyValue('--md-sys-color-primary')` is non-empty.
- **Python B:** `python3 -c "from materialyoucolor.quantize import ImageQuantizeCelebi"`
  imports clean; `Score.score(counts)` returns a non-empty list of ints; `light` and
  `dark` dicts share the same keys (`COLOR_NAMES`) with differing values.
- **Fallback C:** `extract_palette` returns `k` distinct `#RRGGBB` strings, ordered
  strongest-first, and the top swatch visibly matches the image's dominant colour.
- Sanity check contrast of `primary` on `surface` with **accessible-contrast-checker**
  before shipping any generated theme.

## Pitfalls

- **CORS / tainted canvas (JS):** `sourceColorFromImage` and `getImageData` throw on
  cross-origin images without `crossOrigin="anonymous"` + a permissive server. Proxy
  or same-origin the asset.
- **Logos with transparency:** transparent pixels read as black and hijack the palette.
  Skip `alpha < 255` (Recipe A does) or matte onto the intended background first.
- **`get_hex` returns 8-digit `#RRGGBBAA`.** Trim the trailing `FF` alpha before writing
  CSS hex, or emit `rgba()` from `get_rgba(scheme)` instead.
- **`quality` is a subsample stride, not a percentage.** `1` = every pixel (slow on
  large images); bump to `5–10` for speed. Downscale huge inputs first regardless.
- **Most-frequent ≠ best theme colour.** A grey/black background often dominates by
  population; that's exactly why you rank with `Score` (or the chroma-weight in C)
  instead of taking the top raw cluster.
- **Pick the right variant.** `SchemeTonalSpot` is muted/Android-default; use
  `SchemeVibrant` or `SchemeExpressive` for punchier brand-led palettes, `SchemeContent`
  to stay faithful to the source hue, `SchemeMonochrome` for greyscale UIs.
- **Spec version drift:** pin `spec_version="2025"` (M3 expressive) vs the older 2021
  spec — token values differ, so a fixed version keeps regenerated themes stable.
