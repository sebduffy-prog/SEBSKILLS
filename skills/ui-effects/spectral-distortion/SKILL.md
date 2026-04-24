---
name: spectral-distortion
description: Compose a red-themed spectra-noise WebGL shader background with an interactive-distortion image overlay so that the spectra's animated field continuously distorts the image while mouse input still adds its own warp. Use this skill whenever the user asks for a "spectral distortion", "red spectra background that distorts the image", "shader-driven image warp", "ambient generative distortion", or any composition that layers spectra-noise behind an interactive-distortion image and feeds the shader motion into the distortion field. Trigger this even when the user describes the effect loosely ("red shader background melting the photo", "the noise should also warp the picture").
---

# Spectral Distortion Component

Composes two existing ui-effects skills — [`spectra-noise`](../spectra-noise) and [`interactive-distortion`](../interactive-distortion) — into a single layered component:

1. A full-bleed **red** `SpectraNoise` canvas sits in the background.
2. An `InteractiveDistortion` layer renders an image on top of the spectra background.
3. The spectra's animated field is sampled as a synthetic velocity signal and fed into the distortion component, so the image is **continuously distorted by the spectra** even when the cursor is idle. Mouse movement still adds its own velocity on top.
4. Foreground `children` sit above both layers with an explicit stacking context — **all content remains visible**.

## When to use

- User wants "a red spectral component on the background" and asks for that same component to also distort an image.
- User is dressing up a hero section, pitch-deck slide, or dashboard panel and wants an atmospheric red shader backdrop whose motion is picked up by a foreground image.
- User asks to combine `spectra-noise` and `interactive-distortion` without writing the layering + driving logic themselves.

Do **not** use this skill when:
- The user just wants a shader background (use `spectra-noise` directly).
- The user just wants mouse-driven image distortion (use `interactive-distortion` directly).
- The user wants a different colour (you can re-skin via props, but the skill defaults to red because that's the request that triggered the skill).

## Prerequisites

This skill assumes both dependency skills are already installed in the project:

```
components/
├── SpectraNoise.tsx          ← from skills/ui-effects/spectra-noise
├── InteractiveDistortion.tsx ← from skills/ui-effects/interactive-distortion
└── SpectralDistortion.tsx    ← this skill
```

If they aren't present, run the two dependency skills first, then drop this file in.

## What to produce

A **single `.tsx` file** called `SpectralDistortion.tsx` — pure composition, no WebGL code of its own. Use the code from `assets/SpectralDistortion.tsx` verbatim.

### Usage

```tsx
import SpectralDistortion from "@/components/SpectralDistortion";

<SpectralDistortion
  imageUrl="/hero.jpg"
  // Defaults to a red palette. Override via `spectraProps` if needed.
>
  <h1 style={{ color: "white" }}>All content stays visible on top.</h1>
  <p>This paragraph renders above the shader + the distorted image.</p>
</SpectralDistortion>
```

### Full prop surface

```tsx
<SpectralDistortion
  imageUrl="/hero.jpg"
  videoUrl={undefined}                 // optional — pass a video instead of an image
  mediaType="image"                    // "image" | "video"
  ambientStrength={0.6}                // 0-1, how strongly the shader drives the distortion
  ambientFrequency={0.4}               // Hz-ish, speed of the ambient warp signal
  imageOpacity={0.85}                  // 0-1, blend the image over the spectra
  imageBlendMode="screen"              // any CSS mix-blend-mode; "screen" keeps the red visible
  height="100vh"
  distortionPreset="pixelated"         // "pixelated" | "smoothDistortion" | "highDetail" | "custom"
  spectraProps={{                      // forwarded to SpectraNoise
    useCustomColors: true,
    primaryColor: [0.15, 0.0, 0.0],
    secondaryColor: [0.7, 0.05, 0.1],
    accentColor:   [1.0, 0.25, 0.2],
    colorIntensity: 0.85,
    warpAmount: 0.35,
    noiseIntensity: 0.06,
    scanlineIntensity: 0.12,
    scanlineFrequency: 0.5,
    speed: 0.45,
  }}
  distortionProps={{                   // forwarded to InteractiveDistortion
    objectFit: "cover",
    distortionStrength: 1.2,
  }}
>
  {/* Anything you put here renders above the effect. */}
</SpectralDistortion>
```

## How it works

The composition uses three stacked absolutely-positioned layers inside a `position: relative` container:

| Layer | z-index | Content | Notes |
|---|---|---|---|
| Background | 0 | `<SpectraNoise />` with red palette | Full-bleed, covers parent |
| Mid | 1 | `<InteractiveDistortion />` with image/video | `mix-blend-mode: screen` by default so the red shows through highlights |
| Foreground | 10 | `children` | `pointer-events: auto`; everything the user writes stays readable |

### Feeding the shader motion into the distortion

`InteractiveDistortion` already applies the distortion from a mouse-velocity signal (`mouseRef.current.vX / vY`). We **inject a synthetic low-frequency velocity** each frame that mirrors the spectra's own hue/warp oscillation — specifically `sin(t*ω) * amp` on X and `cos(t*ω*1.3) * amp` on Y — so the same temporal character that drives the shader also drives the distortion.

The synthetic signal is added *alongside* the mouse velocity, not in place of it. When the cursor is still, the image breathes with the spectra. When the user moves the cursor, their input stacks on top.

The injection uses a small `useEffect` that reaches into the `InteractiveDistortion`'s mouse ref via a forwarded handle. **Do not try to duplicate the InteractiveDistortion internals here** — the single-file composition simply nudges the existing ref.

## Keeping content visible

Two defaults matter:

1. **`mix-blend-mode: screen`** on the distortion layer. This multiplies highlights with the red background instead of occluding it — the image becomes a red-tinted inlay rather than a solid block. Override with `imageBlendMode="normal"` if the user wants the image to fully cover the shader.
2. **`pointer-events: auto; z-index: 10`** on the children container. The two WebGL canvases stay at `pointer-events: none` under the children, so buttons / links / forms the user puts inside still receive clicks.

If the user reports content looks washed out, first try lowering `imageOpacity`, then `ambientStrength`, then the spectra's `warpAmount`. Don't reach for a fourth blend layer — the above three controls cover the readability envelope.

## Performance notes

- You now have **two** WebGL contexts on screen (one WebGL1 for spectra, one WebGL2 for distortion). On low-end devices this is noticeable. If perf is poor:
  - Drop `resolutionScale` on the spectra (pass via `spectraProps={{ resolutionScale: 0.5 }}`).
  - Drop the distortion grid — e.g. `distortionPreset="pixelated"` (the default, grid=15 for image) is already the cheapest preset.
  - Set `ambientStrength={0}` to stop the per-frame ref write (tiny gain).
- Respect `prefers-reduced-motion`: the composition inherits whatever the two dependency components do. If a user has reduced-motion on and the dependency components honor it, this will too. If not, wrap in a `useReducedMotion` guard before enabling.

## Common requests

- **"Make the red more intense / less intense"** — tune `spectraProps.colorIntensity` (default 0.85). Or pass a custom palette; the defaults use `primary=[0.15,0,0]`, `secondary=[0.7,0.05,0.1]`, `accent=[1.0,0.25,0.2]`.
- **"Different colour family"** — the skill defaults to red because the triggering request asked for red, but any `SpectraNoiseProps` you pass via `spectraProps` works. E.g. `spectraProps={{ theme: "ocean", useCustomColors: false }}` for blue.
- **"I want the image to cover the background fully"** — set `imageOpacity={1}` and `imageBlendMode="normal"`.
- **"Distortion too wobbly / not wobbly enough"** — tune `ambientStrength` (0 = mouse only, 1 = strong constant warp) and `ambientFrequency`.
- **"The image doesn't react to my cursor any more"** — the mouse handler still runs; if it feels weak, increase `distortionProps.distortionStrength` or switch the preset to `smoothDistortion` which has a stronger/slower falloff.

## Constraints respected

- This skill **does not modify** the existing `spectra-noise` or `interactive-distortion` assets. It is a pure composition wrapper.
- The ui-effects `README.md` has been updated with an index row, nothing else.
- No changes are made to `install.sh`, the Muse dashboard integration, or anything outside `skills/ui-effects/spectral-distortion/`.
