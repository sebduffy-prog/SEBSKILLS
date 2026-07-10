---
name: vccp-logo-use
category: frontend-and-design
description: >
  Apply the four official VCCP bear-and-girl logo lockups —
  `Logo.png`, `Bear_Lockup.png`, `Girl_Lockup.png`, `Girl_and_Bear.png`
  — to client-branded surfaces with controlled recolouring. The
  silhouettes are flat black on transparent and can be recoloured to
  any single client brand colour for co-branded pitch decks, white-
  labelled tools, sponsor placements, and bespoke client work. Covers
  CSS-filter recolouring on the web, SVG-mask recolouring for crisp
  scaling, ImageMagick / Pillow recolouring for static export, and
  python-pptx recolouring for slide decks. Trigger when the user
  mentions "VCCP logo for [client]", "recolour the bear", "put the
  VCCP mark in [colour]", "client-branded VCCP lockup", "co-branded
  deck", "white-label the VCCP logo", "make the bear navy / red /
  white / gold", or any request to use the four VCCP lockups in a
  colour other than black. Use this alongside vccp-media-design
  for the rest of the brand system — this skill is logo-only. SKIP
  if the surface is a pure VCCP-owned artifact (use vccp-media-design
  and keep black silhouettes).
when_to_use:
  - Placing a VCCP lockup on a client-branded or co-branded surface (pitch deck, sponsor placement, white-labelled tool)
  - Recolouring the bear/girl silhouettes to a client's primary brand colour ("make the bear navy / red / white / gold")
  - Recolouring the mark on the web via CSS mask, CSS filter chain, or inline SVG mask
  - Producing flat single-colour PNG exports for print/PDF via ImageMagick
  - Inserting a recoloured lockup into a PowerPoint deck via Pillow + python-pptx
  - Choosing which of the four lockups fits a surface (primary mark, 16:9 hero, square tile, partnership artwork)
when_not_to_use:
  - Pure VCCP-owned surfaces — keep the silhouettes black and use vccp-media-design instead
  - The wider VCCP brand system (typography, highlighter motif, slide grids) — that's vccp-media-design; this skill is logo-only
  - General brand work for non-VCCP clients — use brand-guidelines
  - Gradient fills, two-tone recolours, or any treatment beyond a single flat colour — explicitly forbidden by the mark
keywords:
  - vccp logo
  - bear lockup
  - girl lockup
  - recolour
  - co-branded
  - white-label
  - client brand colour
  - silhouette
  - css mask
  - css filter
  - svg mask
  - imagemagick
  - pillow
  - python-pptx
  - lockup
  - sponsor placement
  - pitch deck
  - flat colour
similar_to:
  - vccp-media-design
  - brand-guidelines
  - professional-page-templates
inputs_needed:
  - Which lockup the surface needs (Logo.png primary, Bear_Lockup.png 16:9 hero, Girl_Lockup.png square, Girl_and_Bear.png partnership artwork)
  - The client's exact primary brand hex (or confirmation none is supplied, to fall back to the standard palette)
  - Surface tone (light or dark) to check contrast and decide on a white-silhouette fallback
  - Target medium (web, static export/print, or PowerPoint) to pick the recolouring recipe
  - Display size, to export at 2x (4x for posters)
produces: A recoloured VCCP lockup in the client's single flat brand colour — as CSS/SVG markup, an exported PNG, or a placed slide image
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# VCCP logo use — client-branded recolouring

Four official lockups, supplied as flat-black silhouettes on
transparent PNG, designed to be recoloured for client-branded
surfaces. The shapes are sacred; the colour is the variable.

## The four lockups

All four live next to this file in [`assets/`](assets/). Reference
them from here, not from elsewhere — single source of truth.

| File | Dimensions | Aspect | Description |
|---|---|---|---|
| [`Logo.png`](assets/Logo.png) | 1620 × 1620 | 1:1 | Primary lockup. Bear + girl on a baseline above a "VCCP / Media" wordmark. The full identity. |
| [`Bear_Lockup.png`](assets/Bear_Lockup.png) | 1920 × 1080 | 16:9 | Bear silhouette alone, no baseline, no wordmark. |
| [`Girl_Lockup.png`](assets/Girl_Lockup.png) | 1080 × 1080 | 1:1 | Girl silhouette alone, no baseline, no wordmark. |
| [`Girl_and_Bear.png`](assets/Girl_and_Bear.png) | 2880 × 1620 | 16:9 | Both characters facing each other, the scale-comparison artwork. No wordmark. |

All four are pure black `#000` on alpha-transparent backgrounds. They
recolour cleanly to any solid hex.

## When to recolour

**Recolour rules:**

- Recolour ONLY for client-branded / co-branded / sponsor / white-
  labelled surfaces. On VCCP-owned surfaces the silhouettes stay black
  (handle via [[vccp-media-design]]).
- Pick ONE colour per surface. No gradient fills. No two-tone fur.
  No drop shadows in the brand colour.
- Always check **contrast against the surface**. A navy bear on dark-
  navy paper disappears. Test at the smallest size the logo will
  appear.
- Recolour to the client's **primary brand colour** unless the brand
  guide names a secondary mark colour explicitly. Don't invent
  "complementary" recolours.

## Recolouring recipes

The silhouettes are pure black, so any "replace black with N" method
works. Five approaches for five contexts:

### 1. CSS filter chain (web, quick)

Fast for prototypes. Pixel-accurate at 1× but slightly soft at large
sizes; degraded by mobile GPU rounding. Use up to ~480px tall.

```css
.vccp-bear-recolour {
  /* Reset to white silhouette, then tint with mix-blend-mode */
  filter:
    brightness(0)              /* collapse all colour to black */
    invert(1)                  /* black → white */
    drop-shadow(0 0 0 #1F4DD8) /* tint via shadow */
    drop-shadow(0 0 0 #1F4DD8); /* twice for opacity */
}
```

Limitations: shadows aren't pixel-perfect at sharp edges. Use the
mask method below for hero-scale recolouring.

### 2. CSS mask (web, sharp at any size)

The right way to do crisp web recolouring. Uses the PNG as an alpha
mask over a flat-coloured div.

```html
<div class="vccp-recolour" data-colour="#1F4DD8" aria-label="VCCP Media (client-branded)"></div>
```

```css
.vccp-recolour {
  width: 200px;
  aspect-ratio: 1;
  background-color: var(--client-brand, #1F4DD8);
  mask-image: url('/brand/Logo.png');
  -webkit-mask-image: url('/brand/Logo.png');
  mask-repeat: no-repeat;
  -webkit-mask-repeat: no-repeat;
  mask-position: center;
  -webkit-mask-position: center;
  mask-size: contain;
  -webkit-mask-size: contain;
}
```

Set `--client-brand: <hex>` on the surface root. The whole mark
recolours instantly when the variable changes.

### 3. SVG inline mask (web, controllable per-fill)

If you need to fill only the bear (leaving the wordmark in another
colour, etc.), use SVG `<mask>`:

```html
<svg viewBox="0 0 1620 1620" width="200" height="200" aria-label="VCCP Media (client-branded)">
  <defs>
    <mask id="vccpLogoMask">
      <image href="/brand/Logo.png" width="1620" height="1620" />
    </mask>
  </defs>
  <rect width="1620" height="1620" fill="#1F4DD8" mask="url(#vccpLogoMask)" />
</svg>
```

Replace the single `<rect>` with multiple shapes if you need
multi-colour treatment (e.g. bear in client colour, wordmark in ink).

### 4. ImageMagick (static export, prepress)

For PDF / print / Photoshop hand-off. Produces a flat single-colour
PNG at the same resolution as the source.

```bash
# Recolour Logo.png to a client navy
magick assets/Logo.png \
  -channel RGB -fill '#1F4DD8' -colorize 100% \
  +channel \
  exports/client-acme/Logo_navy.png

# Variant: white silhouette for dark surfaces
magick assets/Logo.png \
  -channel RGB -fill '#FFFFFF' -colorize 100% \
  +channel \
  exports/client-acme/Logo_white.png
```

The `-colorize 100%` flag preserves the alpha channel — the bear's
fur edges stay clean.

### 5. python-pptx (PowerPoint, programmatic)

`python-pptx` can't recolour a PNG in-place. Two options:

**Option A (recommended):** Recolour with Pillow before insertion,
then place via `add_picture`:

```python
from PIL import Image
from pathlib import Path

def recolour_silhouette(src_path: Path, hex_colour: str) -> Path:
    img = Image.open(src_path).convert('RGBA')
    r, g, b = int(hex_colour[1:3], 16), int(hex_colour[3:5], 16), int(hex_colour[5:7], 16)
    pixels = img.load()
    for x in range(img.width):
        for y in range(img.height):
            pr, pg, pb, pa = pixels[x, y]
            if pa > 0:                          # any visible pixel
                pixels[x, y] = (r, g, b, pa)    # keep alpha, swap RGB
    out = src_path.parent / f"{src_path.stem}_{hex_colour.strip('#')}.png"
    img.save(out)
    return out

# Usage in a deck builder
recoloured = recolour_silhouette(LOGO_PATH, '#1F4DD8')
slide.shapes.add_picture(str(recoloured), Inches(4.5), Inches(0.6), height=Inches(2.6))
```

**Option B (faster, less control):** Use python-pptx's
`PictureFormat.recolor` — only works with the limited set of Office
recolour values, mostly tints of one accent. Don't use for arbitrary
client brand hex.

## Picking the recoloured tone

Reach for these standard client-brand palettes when no exact hex is
specified:

| Vibe | Hex |
|---|---|
| Corporate navy | `#1F4DD8` |
| Classic red | `#D03540` |
| Forest green | `#1F5E3A` |
| Editorial ink | `#0A0A0A` (i.e. keep black) |
| Paper white | `#FFFFFF` (use on dark surfaces only) |
| Premium gold | `#C8A45C` |
| Cyber magenta | `#FF2BD6` |

When the client supplies their own primary brand hex (which is the
norm), use that exact value. Don't "interpret" or "tint for
balance" — just match.

## Workflow

1. **Identify which lockup.** Primary mark goes to `Logo.png`. Hero
   banners go to `Bear_Lockup.png` (16:9). Editorial spacers and
   social tiles to `Girl_Lockup.png` (square). Co-branded artwork
   that tells a "VCCP partnering with [client]" story to
   `Girl_and_Bear.png`.
2. **Identify the surface tone.** Light surface → use the client's
   primary. Dark surface → use the client's primary if it has
   sufficient contrast; fall back to white silhouette if not.
3. **Pick the method** above for the medium (web mask, ImageMagick
   for static, Pillow for PPTX).
4. **Always render the wordmark coherent with the bear.** For
   `Logo.png`, the wordmark recolours with the silhouette — they're
   one flat-colour mark. Never try to keep wordmark black with bear
   in client colour; that reads as a broken file.
5. **Export at 2× the display size** for retina + print bleed
   safety. Use 4× for poster artwork.

## Anti-patterns

1. **Recolouring on a VCCP-owned surface.** That's a brand error —
   use [[vccp-media-design]] and keep black silhouettes.
2. **Two-tone recolour (bear in colour A, wordmark in colour B).**
   The mark is one shape; treat it as one colour.
3. **Gradient fills.** The silhouettes are designed to read flat. A
   gradient turns them into a different mark.
4. **Adding a drop shadow in the brand colour.** Flat-only. The mark
   has its own weight; it doesn't need a halo.
5. **Stretching to fit.** Always preserve aspect ratio. `Logo.png` is
   1:1, `Bear_Lockup.png` is 16:9, `Girl_Lockup.png` is 1:1,
   `Girl_and_Bear.png` is 16:9.
6. **Using on top of busy photography.** Place on a flat or barely-
   textured backdrop. If the client's hero is photographic, recolour
   to white + put behind a tasteful tinted scrim.

## Compatibility

- [[vccp-media-design]] — the rest of the VCCP brand system (typography,
  highlighter motif, mustard/teal halves, slide grids). This skill is
  the logo-recolour subset for client-branded work.
- [[brand-guidelines]] — general brand work for non-VCCP clients.
- [[professional-page-templates]] — when the recoloured lockup is
  going into a website hero.
