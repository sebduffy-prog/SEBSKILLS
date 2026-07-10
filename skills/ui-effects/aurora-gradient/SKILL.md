---
name: aurora-gradient
category: ui-effects
description: >
  Animated multi-color gradient blob background (React, pure CSS) — soft blurred
  "aurora" blobs drift across a container. Use when the user asks for an "aurora
  background", "gradient background", "animated gradient", "blob background",
  "mesh gradient", "glow background", references Stripe/Linear/Vercel-style
  ambient color fields, or wants an ambient hero backdrop with drifting color
  washes. Framer category — Backgrounds.
when_to_use:
  - Hero section background for a SaaS, portfolio, or product launch page
  - Behind glass cards (pairs well with liquid-glass-button)
  - Ambient section dividers between page blocks
  - Anywhere a static gradient would go but motion is wanted
  - User references Stripe/Linear/Vercel-style ambient color fields
when_not_to_use:
  - Mouse/cursor-driven image warping — use interactive-distortion instead
  - Grainy animated noise fields — use spectra-noise instead
  - Foreground image effects rather than a backdrop — use liquid-image or image-shatter
  - Canvas/WebGL-based backgrounds — this is pure CSS keyframes only
keywords:
  - aurora background
  - gradient background
  - animated gradient
  - blob background
  - mesh gradient
  - glow background
  - ambient hero backdrop
  - drifting color washes
  - blurred blobs
  - mix-blend-mode
  - css keyframes
  - react component
  - stripe
  - linear
  - vercel
  - framer backgrounds
similar_to:
  - spectra-noise
  - liquid-glass-button
  - liquid-image
inputs_needed:
  - Container size/placement (e.g. full-viewport hero vs section)
  - Color palette (3-6 CSS colors; defaults to 4 vivid hues)
  - Light or dark background (blendMode "screen" for dark, "overlay" for light)
  - Optional tuning - speed, blur radius, blob opacity
produces: assets/AuroraGradient.tsx — single-file, zero-dependency React component that wraps overlay content
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Aurora Gradient

Drop-in React component that paints 3–6 large blurred color blobs inside a container and slowly drifts them. Pure CSS animation (keyframes + blend modes), zero canvas/WebGL.

## What the effect looks like

A container with soft, oversaturated color clouds floating and morphing. Colors blend via `mix-blend-mode: screen`, so overlaps create new hues. Works best behind dark content with some transparency on top. No JS animation loop — just CSS keyframes with staggered delays.

## When to use

- Hero section background (SaaS, portfolio, product launch)
- Behind glass cards (pairs well with `liquid-glass-button`)
- Ambient section dividers
- Any place you'd otherwise reach for a static gradient but want motion

## What to produce

`assets/AuroraGradient.tsx` — single file, no dependencies. Wrap any content you want overlayed inside it:

```tsx
import AuroraGradient from "@/components/AuroraGradient";

<AuroraGradient style={{ width: "100%", height: "100vh" }}>
  <h1 style={{ color: "white" }}>Hero title</h1>
</AuroraGradient>
```

## Props

| Prop | Type | Default | Notes |
|---|---|---|---|
| `colors` | `string[]` | 4 vivid hues | Any CSS color. 3–6 works best. |
| `speed` | `number` | `18` | Animation duration (seconds). Lower = faster drift. |
| `blur` | `number` | `80` | Blur radius in px. Big numbers = softer clouds. |
| `opacity` | `number` | `0.8` | Blob layer opacity. |
| `blendMode` | CSS blend mode | `"screen"` | Try `"overlay"` on light backgrounds. |

## Implementation notes

- Each blob gets a deterministic-looking but staggered animation via delay = `(i * speed) / colors.length`.
- Position uses `(i * 23) % 60` / `(i * 37) % 60` — cheap pseudo-random so blobs don't stack.
- `isolation: isolate` on the outer container so blend modes don't leak out.
- Content wrapper sits at `z-index: 1` above the blob layer.

## Attribution

Inspired by common Framer marketplace "aurora"/"gradient blob" backgrounds. No Framer code reused — pure CSS reimplementation.
