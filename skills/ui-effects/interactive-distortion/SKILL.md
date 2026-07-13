---
name: interactive-distortion
category: ui-effects
description: >
  Build a WebGL2 interactive mouse-driven pixel distortion effect for images and videos in
  React/Next.js. Use this skill whenever the user asks for "interactive distortion", "pixel warp",
  "cursor-follow distortion", "Akella DistortedPixels", "liquid hover on image", "melting image
  effect", or any hover/mouse-velocity-driven displacement effect over an image or video. Also use
  when the user references the Framer InteractiveDistortion component, Fugu 4D, or describes the
  effect as "image that ripples when you move the mouse over it", "pixel grid that warps with
  cursor", or similar. Trigger this even if the user just describes wanting to make a hero image
  feel interactive without naming the technique.
when_to_use:
  - User wants a hover-responsive hero image or video that "feels alive"
  - User references "distortion", "pixel warp", "liquid effect", "Akella", "DistortedPixels", or "Fugu 4D"
  - User describes an image that ripples/smears when the cursor moves over it, or a cursor that leaves a trail
  - User is building a portfolio, landing page, or pitch deck and wants an interactive image effect
  - User wants a pixel-grid warp over a video with presets (smoothDistortion, highDetail, pixelated)
when_not_to_use:
  - Image shatters into tiles that fly apart on hover — use image-shatter
  - Liquid/ripple effect without the pixel-grid warp mechanic — see liquid-image
  - Chromatic/spectral shader distortions — see spectral-distortion
  - Ambient noise backgrounds rather than media distortion — see spectra-noise
  - Dozens of instances on one page (browser WebGL context limit, typically 16)
keywords:
  - interactive distortion
  - pixel warp
  - cursor-follow distortion
  - webgl2
  - shader
  - data texture
  - mouse velocity
  - hover effect
  - hero image
  - video distortion
  - liquid hover
  - melting image
  - akella
  - distortedpixels
  - fugu 4d
  - framer
  - react
  - nextjs
  - presets
similar_to:
  - image-shatter
  - liquid-image
  - spectral-distortion
  - spectra-noise
inputs_needed:
  - Media type (image or video) and the raw asset URL (self-hosted or CORS-enabled)
  - Preset choice (smoothDistortion, highDetail, pixelated) or custom tuning values (grid, mouseInfluence, strength, relaxation, distortionStrength)
  - Container dimensions (parent must have explicit size) and objectFit behavior
  - Whether the deployment is commercial (Fugu 4D port is personal/experimental use only)
produces: A single self-contained InteractiveDistortion.tsx React component (WebGL2 renderer + shader + wrapper, no dependencies beyond React)
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Interactive Distortion Component

Generates a self-contained React component that applies a WebGL2 mouse-velocity-driven distortion to an image or video. The effect works by maintaining a low-resolution "data texture" of 2D offsets that get nudged by mouse velocity each frame, then slowly relaxed back to zero. The main image is then sampled with those offsets applied, producing a painterly smear/pixel-warp.

This skill collapses the Framer module's architecture (a separate `WebGL2Renderer` component + the distortion component) into a **single self-contained file** with no external dependencies beyond React.

## What the effect looks like

Move your cursor over an image or video and a grid of pixels lags behind the motion — like dragging your finger through wet paint. Three built-in presets:

- **smoothDistortion** — fine grid, long-tail relaxation, subtle
- **highDetail** — very fine grid, sharp response (expensive, images only)
- **pixelated** — coarse chunky grid, high impact (the default, reads well in video)

## When to use

- User wants a hover-responsive hero image or video
- User references "distortion", "pixel warp", "liquid effect", "Akella", "DistortedPixels", "Fugu 4D"
- User is building a portfolio, landing page, or pitch deck and wants the image to "feel alive"
- User describes an image where the cursor leaves a trail

## What to produce

A **single `.tsx` file** called `InteractiveDistortion.tsx` — contains the WebGL2 renderer, the distortion shader, and the React wrapper. Use the code from `assets/InteractiveDistortion.tsx`.

> **No local bundle? (remote use)** If you're reading this SKILL.md from GitHub raw and don't have the `assets/` folder on disk, fetch the one bundled file it references (curl `-fsSL` or WebFetch):
> - `https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/skills/ui-effects/interactive-distortion/assets/InteractiveDistortion.tsx`

### Usage

```tsx
import InteractiveDistortion from "@/components/InteractiveDistortion";

<div style={{ width: "100%", height: "600px" }}>
  <InteractiveDistortion
    mediaType="image"
    imageUrl="/hero.jpg"
    preset="pixelated"
    objectFit="cover"
  />
</div>

// Or with video:
<InteractiveDistortion
  mediaType="video"
  videoUrl="/hero.mp4"
  preset="smoothDistortion"
  autoPlay
  autoLoop
  videoPerformanceMode
/>

// Or custom tuning:
<InteractiveDistortion
  mediaType="image"
  imageUrl="/hero.jpg"
  preset="custom"
  grid={40}
  mouseInfluence={0.2}
  strength={0.15}
  relaxation={0.92}
  distortionStrength={1.2}
/>
```

## Implementation notes (critical — do not skip)

1. **WebGL2 required.** The shader uses `#version 300 es` and `RGB32F` float textures. If the target browser is pre-2017 Safari or any IE, this will fail. Add a fallback `<img>` / `<video>` element that shows when WebGL2 isn't available (the asset does this).

2. **CORS on the image/video source.** The component sets `crossOrigin = "anonymous"` so the texture is readable. If the image is hosted elsewhere without proper CORS headers, you'll get a black texture or a console error. Self-host assets in `/public` or ensure the CDN sends `Access-Control-Allow-Origin`.

3. **The data texture is the cleverness.** Don't try to do per-pixel distortion by updating the full-resolution image every frame — the whole point is that a tiny `grid × grid` texture (typically 15–80) of 2D offsets gets updated on CPU, then the GPU samples it with bilinear interpolation during the fragment shader. Keep this architecture.

4. **Mouse velocity, not position.** The distortion responds to `vX = x - prevX`, `vY = y - prevY`, not absolute cursor position. A stationary cursor causes the data texture to decay to zero via the `relaxation` multiplier each frame. This is what makes the effect feel alive.

5. **`object-fit` is done in the shader.** The `a1`/`a2` aspect ratio values (in `uResolution.zw`) remap UV space so the image covers/contains properly regardless of container shape. This is why you can't just drop in arbitrary image dimensions without the shader math — the Framer code does this correctly and the asset preserves it.

6. **Video uploads every frame.** `gl.texImage2D(..., video)` re-uploads the current video frame. This is expensive; on low-end devices the `videoPerformanceMode` flag uses coarser grid presets. Adaptive quality (`adaptiveQuality`) monitors FPS and drops grid resolution if it falls below 25fps.

7. **Container must have explicit size.** The component sizes itself to its parent. A parent with `height: auto` will collapse to zero.

## Next.js specifics

`InteractiveDistortion.tsx` must start with `"use client";` — WebGL requires the browser.

If the image/video URL is a Next.js static asset, pass the URL directly (e.g. `"/hero.jpg"`). Don't try to use `next/image`'s optimized URLs — the component needs raw URLs it can pass to `new Image()` / `<video>`.

For images that need optimization, either:
- Use the raw asset and accept the size, or
- Serve a pre-optimized variant from your CDN and pass that URL

## Presets reference

All preset values (from the Framer module):

| Preset | grid (image) | grid (video) | mouseInfluence | strength | relaxation |
|---|---|---|---|---|---|
| smoothDistortion | 50 | 30 | 0.25 | 0.11 | 0.90 |
| highDetail | 607 | 80 | 0.11 | 0.36 | 0.96 |
| pixelated | 15 | 12 | 0.13 | 0.15 | 0.90 |

For `custom`, the user passes all five values as props (grid, mouseInfluence, strength, relaxation, distortionStrength).

## Common requests

- **"Make it work without mouse / on mobile"** — add touch handlers (asset already includes `touchmove`). On mobile, the user has to actually touch the element. For a continuous ambient distortion, inject synthetic mouse velocity via `setInterval` in a `useEffect` — e.g. `setInterval(() => { mouseRef.current.vX = Math.sin(Date.now() * 0.001) * 0.02 }, 16)`.
- **"Chain multiple images"** — instantiate multiple `<InteractiveDistortion>` components in a grid. Each maintains its own WebGL context; note the browser's context limit (typically 16). If you need dozens, share a single context with multiple textures (beyond this skill's scope).
- **"Use an SVG or canvas as the source"** — possible but not out-of-the-box. Pre-render the source to a `<canvas>`, export via `toDataURL()`, and pass as `imageUrl`. Or modify the `onInit` handler to accept a canvas source directly.
- **"Make the cursor leave a visible trail"** — increase `relaxation` toward 0.98 and `strength` toward 0.3. Trails are already emergent in the default model.

## Attribution

The technique is originally by Yuriy Artyukh (Akella) — https://github.com/akella/DistortedPixels — released under MIT. The Framer port this skill is based on is by Fugu 4D Agency and is not licensed for redistribution or commercial derivative work. **This skill is intended for personal/experimental use only.** If the user wants to ship this in commercial client work, they should either re-implement from Akella's MIT source directly, or get written permission from Fugu 4D. Flag this if the context suggests commercial deployment.
