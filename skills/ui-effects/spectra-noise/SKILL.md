---
name: spectra-noise
category: ui-effects
description: >
  Build a WebGL shader-based animated noise background component for React/Next.js.
  Use this skill whenever the user asks for a "spectra noise", "animated shader background",
  "CPPN neural network visual", "generative noise backdrop", or any full-screen animated
  WebGL background with hue-shift, scanlines, warp, and noise controls. Also use when the
  user references the Framer SpectraNoise component, wants to recreate a Framer shader
  module in a standalone React project, or asks for a psychedelic / cyberpunk / fluid
  animated background. Trigger this even if the user just describes the effect ("trippy
  shifting blobs of colour", "shader gradient that moves") rather than naming it.
when_to_use:
  - User wants an animated shader background for a hero section, landing page, or dashboard panel
  - User references "Spectra Noise" or wants a Framer shader module recreated as a standalone React component
  - User describes the effect in their own words — trippy shifting colour blobs, generative shader gradient that moves
  - User asks for a psychedelic / cyberpunk / fluid animated backdrop with hue-shift, scanlines, warp, or noise controls
  - User needs a themed (cyberpunk, neon, fire, ocean, forest, sunset, monochrome) or custom-colour atmospheric background
  - Project needs an atmospheric visual backdrop (e.g. the Madonna dashboard or a pitch-deck webpage)
when_not_to_use:
  - Simple drifting colour-wash backgrounds without shaders — use aurora-gradient instead
  - Distortion applied to a specific image rather than a full-screen backdrop — use liquid-image or spectral-distortion
  - Static gradients or CSS-only effects where WebGL is overkill
  - Non-React projects or environments where a canvas/WebGL context is unavailable
keywords: [webgl, shader, cppn, noise, animated background, generative, fragment shader, hue-shift, scanlines, warp, react, nextjs, framer, cyberpunk, psychedelic, hero background, fullscreen, resolution scale, themes, custom colors]
similar_to: [aurora-gradient, spectral-distortion, liquid-image, interactive-distortion]
inputs_needed:
  - Whether the project is React or Next.js (App Router needs "use client"), and TypeScript or plain JS
  - Desired theme (default/cyberpunk/neon/fire/ocean/forest/sunset/monochrome) or custom primary/secondary/accent colours
  - Where it sits (hero, panel) and whether the parent has explicit dimensions
  - Performance constraints — mobile targets may need a lower resolutionScale
produces: A single self-contained SpectraNoise.tsx (or .jsx) React component rendering a full-screen animated WebGL CPPN shader background, no dependencies beyond React
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Spectra Noise Component

Generates a self-contained React component that renders a full-screen animated WebGL fragment shader. Originally a Framer module — this skill strips the Framer-specific wrappers (`addPropertyControls`, `useIsStaticRenderer`) and produces a clean standalone component that works in any React/Next.js project.

## What the effect looks like

A CPPN (Compositional Pattern-Producing Network) shader generates smoothly-animated coloured blobs that shift hue over time. Layered on top: scanlines, film-grain noise, and UV warp distortion. Themes include Cyberpunk, Neon, Fire, Ocean, Forest, Sunset, Monochrome — plus a custom-colour mode with primary/secondary/accent control.

## When to use

- User wants an animated shader background for a hero section, landing page, or dashboard panel
- User references "Spectra Noise" or a Framer shader module
- User describes the effect in their own words (trippy, shifting, generative, shader-like)
- User is building the Madonna dashboard, a pitch deck webpage, or any project needing atmospheric visual backdrop

## What to produce

A **single `.tsx` file** (or `.jsx` if project is plain JS) called `SpectraNoise.tsx`. No external dependencies beyond React.

### File structure to generate

```
components/
└── SpectraNoise.tsx   ← all shader code + React wrapper in one file
```

### Usage the user should see afterwards

```tsx
import SpectraNoise from "@/components/SpectraNoise";

<div style={{ position: "relative", width: "100%", height: "100vh" }}>
  <SpectraNoise
    theme="cyberpunk"        // or: default | neon | fire | ocean | forest | sunset | monochrome
    hueShift={0}             // -180 to 180 degrees
    noiseIntensity={0.05}    // 0 to 1
    scanlineIntensity={0.15} // 0 to 1
    scanlineFrequency={0.5}  // 0 to 1
    warpAmount={0.3}         // 0 to 2
    speed={0.5}              // 0 to 3
    resolutionScale={1}      // 0.25 to 2 (lower = better perf)
  />
  <div style={{ position: "relative", zIndex: 1 }}>
    {/* your content on top */}
  </div>
</div>
```

## Implementation

Use the full component code from `assets/SpectraNoise.tsx` in this skill's folder. Copy it directly — it's already cleaned of Framer imports and typed for TypeScript. If the project is JavaScript, strip the type annotations; the component logic is identical.

**No local bundle? (remote use)** If `assets/SpectraNoise.tsx` isn't on disk (e.g. you only have this SKILL.md), fetch it — the shader's CPPN weight matrices are not regenerable, so you must use this exact file, don't reconstruct it:

```
curl -fsSL https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/skills/ui-effects/spectra-noise/assets/SpectraNoise.tsx
```

(or WebFetch the same URL).

**Critical implementation notes (do not skip):**

1. **Fullscreen triangle, not quad.** The geometry is a single oversized triangle covering the viewport (vertices `[-1,-1, 3,-1, -1,3]`). This is faster than a quad and avoids seam artifacts. Don't "fix" this to use a quad.

2. **`lowp` precision in the fragment shader.** The CPPN matrix math is heavy but the output range is bounded, so `lowp` works and is dramatically faster on mobile GPUs. Don't promote to `highp` unless you see banding on desktop.

3. **Canvas sizing.** The component uses `resolutionScale` to decouple render resolution from CSS size. `canvas.width = parent.clientWidth * resolutionScale` while `canvas.style.width = parent.clientWidth + "px"`. Always set both — missing either one gives you a blurry or misaligned canvas.

4. **WebGL detection + fallback.** Wrap `getContext("webgl")` in try/catch and have a CSS gradient fallback for unsupported browsers. The provided asset does this.

5. **Cleanup on unmount.** Cancel the `requestAnimationFrame` and remove the resize listener. React strict mode will double-mount in dev; without cleanup you get two render loops fighting each other.

6. **Parent must be positioned.** The canvas is absolutely sized to its parent via `clientWidth`/`clientHeight`, so the parent must have explicit dimensions (not `height: auto`).

## Next.js specifics

If placing this in a Next.js App Router project:

```tsx
"use client";
// SpectraNoise.tsx must start with this directive — WebGL requires the browser
```

For server components that want to embed it, create a thin client wrapper:

```tsx
// components/SpectraNoiseWrapper.tsx
"use client";
import SpectraNoise from "./SpectraNoise";
export default SpectraNoise;
```

And consider dynamic import with `ssr: false` if the component is heavy and not above the fold:

```tsx
const SpectraNoise = dynamic(() => import("@/components/SpectraNoise"), { ssr: false });
```

## Theme colour reference

The themes are hardcoded in the fragment shader. If the user asks to add a new theme, edit the `applyTheme` function — add a new branch with `theme == N` and pick a `mix(baseColor, vec3(R,G,B), amount) * vec3(Rmul, Gmul, Bmul)` tint. Update the TypeScript union for the `theme` prop to match.

| Theme | Tint direction |
|---|---|
| default | no tint |
| cyberpunk | cyan shift, magenta-boosted |
| neon | magenta shift, bright |
| fire | orange-red shift, warm-boosted |
| ocean | blue shift, cool-boosted |
| forest | green shift |
| sunset | orange shift, warm |
| monochrome | desaturated to luminance |

## Custom colours mode

When `useCustomColors={true}`, the shader blends three user-provided RGB colours across the luminance range: primary for shadows, secondary for midtones, accent for highlights. `colorIntensity` (0–1) controls how much the custom palette overrides the base shader output.

```tsx
<SpectraNoise
  useCustomColors
  primaryColor={[0.1, 0.0, 0.3]}   // RGB 0-1, shadow colour
  secondaryColor={[0.5, 0.2, 0.8]}  // midtone
  accentColor={[1.0, 0.9, 0.3]}     // highlight
  colorIntensity={0.7}
/>
```

## Performance tuning

- If mobile frame-rate is poor, set `resolutionScale={0.5}` — the CPPN is the cost, not the canvas size.
- Drop `speed` and it uses less CPU (fewer animation updates, but the shader itself runs every frame regardless, so the gain is small).
- Set `warpAmount={0}` to skip the per-pixel UV warp (minor gain).
- For static hero backgrounds, consider rendering once and pausing: cancel the RAF loop after the first frame.

## Common requests and how to handle them

- **"Make it loop seamlessly"** — the CPPN uses `sin(uTime * ...)` internally with irrational frequencies, so it never perfectly repeats. If seamless loop is required, multiply `uTime` by `TAU / loopDuration` and round the input to integer cycles — but warn the user this changes the visual character.
- **"Add mouse interaction"** — add a `uMouse` uniform, pass `vec2(mouseX, mouseY)` from a mousemove listener, and use it as an extra input to the CPPN (e.g. `cppn_fn(uv, uMouse.x, uMouse.y, time*0.1)`). This makes the blobs follow the cursor.
- **"Export as image/video"** — WebGL canvas `.toDataURL()` works for stills. For video, use `canvas.captureStream(30)` + `MediaRecorder`.
- **"Make it faster on my laptop"** — reduce `resolutionScale`, reduce `speed`, and/or tell them the CPPN is intrinsically expensive; consider the simpler gradient-noise alternative (not covered by this skill).

## Attribution

The CPPN shader technique is a well-known generative-graphics pattern (trained neural networks generating patterns from UV coords + time). The specific weight matrices in this implementation come from the Framer Spectra_Noise module. Since this is for personal/experimental use, that's fine — don't ship it as your own original shader work in a commercial pitch without understanding the provenance.
