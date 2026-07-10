---
name: liquid-image
category: ui-effects
description: Build a WebGL liquid-water hover effect for images in React/Next.js — ripples follow the cursor, and a grayscale-to-colour reveal mask follows the hover. Use this skill whenever the user asks for a "liquid image", "water ripple image", "water effect on image", "hover ripple", "grayscale to colour reveal on hover", or references the Framer LiquidImage component. Also use when the user describes the effect as "image that ripples like water when you hover", "image that reveals colour when you touch it", "image with waves that follow the mouse", or wants an interactive photo with a magical / dreamy / tactile feel. Trigger even without exact naming — e.g. "make this photo feel alive when you hover", "add that rippling water thing to the hero image".
when_to_use:
  - User wants a hover-responsive photograph for portfolio, hero, or gallery
  - User mentions "liquid image", "water effect", "ripple hover", "colour reveal on hover"
  - User wants grayscale-to-colour reveal that follows the cursor
  - User is building atmospheric / editorial / pitch-deck UI with image focus
when_not_to_use:
  - User wants pixel-grid distortion instead of fluid ripples → use interactive-distortion
  - User wants the image to break into tiles on hover → use image-shatter
  - User wants an animated background, not an image effect → use spectra-noise or aurora-gradient
  - User wants a static colour-on-hover with no fluid motion → use plain CSS, not this
similar_to:
  - interactive-distortion
  - image-shatter
  - spectral-distortion
keywords:
  - liquid
  - water
  - ripple
  - hover
  - webgl
  - grayscale
  - colour-reveal
  - liquidimage
  - water ripple image
  - hover ripple
  - wake trail
  - hotspots
  - shader
  - react
  - framer
inputs_needed:
  - Image URL or path (must be CORS-accessible)
  - Container dimensions (width × height)
produces: A single self-contained LiquidImage.tsx React component
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Liquid Image Component

Generates a self-contained React component that renders an image with a WebGL water-ripple hover effect. When the cursor moves over the image, ripples emanate from the cursor position (both a live ripple and a fading wake trail of the last 8 positions), and the image simultaneously transitions from grayscale to full colour within a soft circular mask around the cursor.

Also supports **persistent hotspots** — fixed points in the image that stay rippled and colourful regardless of cursor position, useful for drawing attention to specific regions.

## What the effect looks like

Mouse over a photograph. Where your cursor is, the image appears in full colour and subtly distorts with a water-like ripple. The rest of the image stays grayscale. Move away and ripples fade, colour desaturates, back to grayscale. Touch-enabled for mobile.

## When to use

- User wants a hover-responsive photograph for a portfolio, hero, or gallery
- User references "liquid image", "water effect", "ripple hover", "colour reveal"
- User describes "photo reveals colour when you hover" / "water waves on the image"
- User is building something atmospheric (pitch deck webpage, editorial site, interactive narrative)

## What to produce

A single `.tsx` file called `LiquidImage.tsx`. Zero dependencies beyond React. Use the code from `assets/LiquidImage.tsx`.

### Usage

```tsx
import LiquidImage from "@/components/LiquidImage";

<div style={{ width: 600, height: 400 }}>
  <LiquidImage
    image={{ src: "/hero.jpg", alt: "Hero image" }}
    strength={0.15}        // 0.01-0.5, displacement amount
    speed={0.18}           // 0.01-1, ripple animation speed
    borderRadius={8}       // 0-64 px
  />
</div>

// With persistent hotspots (fixed colour-reveal points)
<LiquidImage
  image={{ src: "/map.jpg" }}
  hotspots={[
    { x: 0.25, y: 0.4 },   // x, y in 0-1 UV space
    { x: 0.7, y: 0.3 },
    { x: 0.5, y: 0.8 },
  ]}
/>
```

## Implementation notes

1. **WebGL1, not WebGL2.** The shader uses `precision highp float` and `texture2D` (not `texture`). Works in every browser with WebGL. Don't "upgrade" to WebGL2 — this effect doesn't benefit and it cuts compatibility.

2. **High-DPI / devicePixelRatio handling.** The canvas internal dimensions are `offsetWidth * dpr` while the CSS dimensions stay at `offsetWidth`. This keeps the image crisp on retina without blowing up GPU cost. The asset handles this.

3. **Offscreen canvas for `object-fit: cover`.** The image is drawn to an offscreen 2D canvas with cover logic (centred, scaled to fill, cropped), then uploaded to the WebGL texture every frame. This is why the image fits any container aspect ratio. If you skip the offscreen canvas, the image will stretch.

4. **Wake trail = array of `{x, y, t}`.** Up to 8 recent cursor positions are kept as "wake points", each with a timestamp. In the fragment shader, each wake point contributes a ripple whose amplitude decays with both distance and time. This is what gives the effect its trailing water-behind-the-boat feel.

5. **Mask radius is animated, not the whole effect.** The grayscale→colour reveal happens via a `maskRadius` uniform that animates 0→1.5 on mouse-enter using ease-in-out cubic, over 650ms. Ripples are always active but only visible when the cursor is over the element. The mask is what makes hover feel dramatic.

6. **Y-axis inversion.** Mouse coords from DOM are `y-down`; WebGL UVs are `y-up`. The asset inverts y when passing to the shader (`my = 1 - my`). Remember this if you modify the shader logic.

7. **Hotspots use `t` set far in the past.** Persistent hotspots pass `t = now - 100000` so the time-based decay is effectively zero — they always ripple.

## Next.js specifics

Must start with `"use client"` — WebGL + mouse events need the browser.

For Next.js `next/image` users: don't pass `next/image` objects. The component needs a raw URL string it can pass to `new Image()`. Use `/public/hero.jpg` style paths directly.

Images must be CORS-accessible. Self-hosted in `/public` works; external CDNs need `Access-Control-Allow-Origin`. The component sets `crossOrigin = "anonymous"`.

## Props reference

| Prop | Type | Default | Description |
|---|---|---|---|
| `image` | `{ src: string; alt?: string }` | Framer demo image | Source image |
| `strength` | number | 0.15 | Ripple displacement amount (0.01-0.5) |
| `speed` | number | 0.18 | Ripple animation speed (0.01-1) |
| `borderRadius` | number | 8 | Rounded corners, px |
| `hotspots` | `{ x: number; y: number }[]` | `[]` | Persistent ripple/colour points in 0-1 UV space |
| `style` | CSSProperties | — | Container style override |

## Common requests

- **"Make it colour by default, grayscale on hover"** — invert the mask in the shader: change `mix(grayColor, color.rgb, mask)` to `mix(color.rgb, grayColor, mask)`.
- **"Stronger ripples"** — bump `strength` toward 0.3. Above 0.4 it becomes glitchy.
- **"Slower ripples"** — drop `speed` to 0.08. The asset clamps the animation but visual cadence changes.
- **"Remove the colour reveal, just ripples"** — remove the `mix(grayColor, color.rgb, mask)` call; output `color.rgb` directly. Trivial shader edit.
- **"Make it responsive to scroll instead of hover"** — pipe scroll position to `mouseRef.current.x/y` via a scroll listener. The rest of the pipeline doesn't care where the "mouse" comes from.
- **"Add multiple images in a gallery"** — each instance creates its own WebGL context; browsers typically cap at 16. For a gallery of 20+ images, use intersection observer + lazy mount.

## Attribution

Original from the Framer "LiquidImage" module by Gustav WF (https://gustavwf.supply/). The WebGL water-ripple + colour-reveal pattern is a common shader technique. For personal/experimental use this adaptation is fine; if shipping commercially, re-implementing the shader from scratch is straightforward (the math is standard).
