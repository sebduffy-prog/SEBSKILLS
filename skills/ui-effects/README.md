# UI Effects

**Drop-in React / Next.js / WebGL components for showstopper interactive effects.**

Each skill produces a single `.tsx` file (plus minimal dependencies) you can copy into any React/Next.js project. These are re-implementations of premium Framer modules as standalone code — no Framer runtime required.

Most require `"use client"` for Next.js app router.

## Index

| Skill | Effect | Tech | Key props |
|---|---|---|---|
| [`image-shatter`](image-shatter) | Image shatters into a grid on hover, spring-animated tiles with cursor magnet | `framer-motion` | `tilesX`, `tilesY`, `maxOffset`, `magnetStrength` |
| [`interactive-distortion`](interactive-distortion) | WebGL2 pixel displacement that follows the mouse over an image or video | WebGL2 (raw) | `strength`, `falloff`, `resolution` |
| [`liquid-image`](liquid-image) | Water-ripple hover with grayscale→color reveal mask | WebGL | `rippleStrength`, `revealRadius` |
| [`liquid-glass-button`](liquid-glass-button) | Apple-style frosted glass button with shine/highlight | Pure CSS (no JS) | CSS variables |
| [`rubiks-image-cube`](rubiks-image-cube) | 3D rotatable cube displaying image segments or colour tiles | CSS 3D + `framer-motion` | `images`, `shuffleOnMount` |
| [`spectra-noise`](spectra-noise) | Animated shader background — hue shift, scanlines, warp, noise | WebGL shader | `speed`, `hueShift`, `warp` |

## When to use each

| Goal | Pick |
|---|---|
| Hero image needs "wow" on hover | `image-shatter` or `liquid-image` |
| Image should feel alive/melty under the cursor | `interactive-distortion` |
| A premium-feeling back/close button | `liquid-glass-button` |
| Playful portfolio/photo showcase | `rubiks-image-cube` |
| Full-screen animated background | `spectra-noise` |

## Combining

- `spectra-noise` (bg) + `liquid-glass-button` (foreground CTAs) = Apple/vision-OS feel
- `frontend-design` (layout) + `image-shatter` (hero) = portfolio site
- `interactive-distortion` + `liquid-glass-button` + `theme-factory` = premium product landing

## Performance notes

- Shader-based skills (`interactive-distortion`, `liquid-image`, `spectra-noise`) respect `prefers-reduced-motion`
- `image-shatter` caps at ~112 tiles (14×8) by default and downscales on mobile
- `rubiks-image-cube` is CSS-3D, not WebGL — cheap
- `liquid-glass-button` is pure CSS — cheapest

## Attribution

Re-implementations of Framer modules. Each `SKILL.md` credits the original Framer component and the technique (framer-motion patterns, WebGL2 displacement, CPPN noise, etc.).
