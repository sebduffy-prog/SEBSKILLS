---
name: filmic-static-panels
description: |
  Recreate the cinematic "static" container look — dark gradient
  panels (raised→surface, hairline border, soft radius, depth shadow)
  sitting under a full-screen animated FILM-GRAIN / TV-static overlay
  (half-res canvas, a few precomputed noise frames cycled at ~16fps,
  `mix-blend-mode:screen`) plus a radial vignette. The grain gives
  cards, chart containers and bars a tactile, premium, slightly noisy
  texture without per-element cost — one overlay textures the whole
  page. Trigger when the user asks for "that static look", "film grain
  on the containers", "grainy / noisy dark cards", "cinematic panel
  surface", "TV static texture", "premium dark dashboard cards",
  "vignette + grain", or wants to reuse the HFA / Affinity Field
  fingerprint-card and mekko-bar container aesthetic. Pairs with
  vccp-media-design for the wider brand system.
category: frontend-and-design
when_to_use:
  - Recreating the cinematic "static look" or film-grain on containers
  - Building grainy/noisy dark cards or a cinematic panel surface
  - Adding TV-static texture, vignette, or premium dark dashboard cards
  - Reusing the HFA / Affinity Field fingerprint-card and mekko-bar aesthetic
when_not_to_use:
  - The wider VCCP brand system — use vccp-media-design
  - Generic colour/font theming — use theme-factory
keywords:
  - film grain
  - tv static
  - noise overlay
  - dark panels
  - gradient cards
  - vignette
  - cinematic
  - mix-blend-mode screen
  - canvas noise
  - premium dashboard
  - grainy cards
  - texture
similar_to:
  - vccp-media-design
  - theme-factory
inputs_needed: The page/containers to texture and the desired grain intensity, radius, and vignette strength.
produces: CSS/canvas code for grainy dark gradient panels under a full-screen film-grain + vignette overlay.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Filmic static panels

The look = three cheap layers stacked on a near-black page:

1. **Panel surface** — a top-to-bottom gradient from `--raised` to
   `--surface`, a 1px hairline border at ~8% white, a 16px radius and a
   deep soft shadow on hover. Reads as a lit slab floating on black.
2. **Film-grain / static overlay** — ONE fixed full-screen `<canvas>`
   that cycles a handful of pre-rendered monochrome-noise frames at
   ~16fps with `mix-blend-mode:screen` at ~5% opacity. Because it sits
   above everything (`pointer-events:none`), every panel and bar inherits
   the same living grain for free.
3. **Vignette** — a fixed radial-gradient that darkens the edges so the
   centre of the composition lifts.

The grain is the signature; the panels just give it surfaces to sit on.

## Files

- [`assets/static-panels.css`](assets/static-panels.css) — design tokens, `.panel` surface, `#grain` + `#vignette` overlays.
- [`assets/grain.js`](assets/grain.js) — self-initialising grain animator (`sizeGrain` / `makeGrain` / `tickGrain`).
- [`assets/demo.html`](assets/demo.html) — minimal working page: a couple of panels + bars under the grain.

## Use it

```html
<link rel="stylesheet" href="static-panels.css">
...
<div class="panel">…card / chart container…</div>
<div class="bar" style="--bar:var(--f2); height:60%"></div>
...
<!-- overlays: keep these LAST in <body>, above content -->
<canvas id="grain"></canvas>
<div id="vignette"></div>
<script src="grain.js"></script>
```

## Knobs

| Want | Change |
|---|---|
| Stronger / weaker static | `#grain { opacity }` (default `0.05`; 0.03 subtle, 0.09 gritty) |
| Coarser grain | lower the canvas divisor in `sizeGrain` (÷2 → ÷3 = chunkier) |
| Faster / slower flicker | the `60`ms delay in `tickGrain` (lower = faster) |
| More frames (less obvious loop) | bump the `4` in `makeGrain` |
| Panel lift | `--raised` / `--surface` gap, and the hover shadow on `.panel` |

## Notes

- `mix-blend-mode:screen` brightens; on a near-black page that yields the
  classic grey static speckle. On light backgrounds use `overlay` or
  `soft-light` instead.
- Half-resolution canvas (`innerWidth/2`) keeps it cheap; the CSS scales
  it back up, which also softens the noise pleasingly.
- Respect `prefers-reduced-motion`: gate `tickGrain`'s animation (render a
  single static frame) when the user opts out — included in `grain.js`.
- One overlay textures the whole page, so it is effectively free per
  panel — add as many `.panel`s as you like.
