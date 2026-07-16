---
name: webgl-3d-scene
category: frontend-and-design
description: >
  Build a production-grade 3D scene on the web with React Three Fiber (Three.js) — a Canvas with proper camera and
  lighting rigs, GLTF model loading, drei helpers (OrbitControls, Environment, Bounds), performance budgets
  (on-demand frameloop, instancing, capped DPR), and graceful mobile / reduced-motion / no-WebGL fallbacks. Use
  this whenever someone says "add a 3D model to the site", "react three fiber", "three.js scene", "spinning
  product in 3D", "interactive 3D hero", "load a GLB/GLTF", or wants real 3D on a page that stays fast and doesn't
  jank on mobile. Reach for it even if they just say "make the hero 3D".
when_to_use:
  - Embedding an interactive 3D model / product viewer / hero in a React or Next.js site
  - Loading and displaying a GLTF/GLB asset with lighting and controls
  - You need a 3D scene that stays performant on mobile and respects reduced-motion
  - Building instanced/particle 3D visuals with React Three Fiber
when_not_to_use:
  - A full-screen animated shader background, no geometry → use spectra-noise
  - A 2D hover/distortion image effect → use interactive-distortion or liquid-image
  - Generating the 3D asset itself from an image → use photo-to-3d-asset / blender-mcp
  - A simple CSS 3D transform (card flip, cube) → use CSS transforms / rubiks-image-cube
keywords: [react three fiber, r3f, three.js, threejs, webgl, 3d, gltf, glb, drei, orbitcontrols, environment, instancing, product viewer, 3d hero, useGLTF, canvas, reduced motion]
similar_to: [spectra-noise, interactive-distortion, rubiks-image-cube, photo-to-3d-asset, frontend-design]
inputs_needed:
  - The GLTF/GLB model path (or the primitive/geometry to render)
  - Where it lives (hero, product viewer, background) and interaction wanted (orbit, autorotate, scroll)
  - Target — Next.js (needs dynamic import, ssr:false) or plain React/Vite
  - Brand lighting/environment mood
produces: A self-contained React Three Fiber scene component, performance-budgeted with mobile + fallback handling
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# WebGL 3D scene (React Three Fiber)

Real 3D on the web that stays fast: a declarative Three.js scene via `@react-three/fiber`, with `@react-three/drei`
helpers, sensible lighting, GLTF loading, and performance + fallback discipline so it doesn't melt phones.

## When to use

For actual geometry/models on a page. For a shader-only backdrop use `spectra-noise`; for 2D image effects use
`interactive-distortion`.

## Prerequisites

```bash
npm i three @react-three/fiber @react-three/drei
```
- **Next.js:** the Canvas is client-only — load it with `dynamic(() => import('./Scene'), { ssr: false })`.
- Put `.glb` files in `public/`. Compress with `npx gltfjsx model.glb --transform` (draco/meshopt) — often 5-10× smaller.

## The scene

```jsx
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Environment, Bounds, useGLTF, AdaptiveDpr, Html } from '@react-three/drei'
import { Suspense } from 'react'

function Model({ url }) {
  const { scene } = useGLTF(url)
  return <primitive object={scene} />
}
useGLTF.preload('/model.glb')

export default function Scene() {
  const reduced = typeof window !== 'undefined'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  return (
    <Canvas
      camera={{ position: [0, 0.5, 4], fov: 45 }}
      dpr={[1, 2]}                     // cap devicePixelRatio — never render at 3x on retina
      frameloop="demand"              // only re-render on change/interaction, not every frame
      gl={{ antialias: true, powerPreference: 'high-performance' }}
    >
      <ambientLight intensity={0.4} />
      <directionalLight position={[5, 5, 5]} intensity={1.2} castShadow />
      <Suspense fallback={<Html center>Loading…</Html>}>
        <Bounds fit clip observe margin={1.1}>   {/* auto-frame the model */}
          <Model url="/model.glb" />
        </Bounds>
        <Environment preset="city" />            {/* image-based lighting = instant realism */}
      </Suspense>
      <OrbitControls enablePan={false} autoRotate={!reduced} autoRotateSpeed={0.6}
                     minPolarAngle={Math.PI / 3} maxPolarAngle={Math.PI / 2} />
      <AdaptiveDpr pixelated />                   {/* drop resolution under load, restore when idle */}
    </Canvas>
  )
}
```

## Performance budget (non-negotiable for shipping)

- **`dpr={[1, 2]}`** — cap pixel ratio; 3× retina quadruples fragment cost for no visible gain.
- **`frameloop="demand"`** for static/orbit scenes — huge battery/CPU win vs the default always-on loop.
- **Instancing** (`<Instances>`/`InstancedMesh`) for repeated geometry — 1 draw call for thousands of copies.
- **Compress models** with draco/meshopt via gltfjsx `--transform`; lazy-load below the fold.
- Prefer `Environment` IBL over many real lights; bake shadows where you can.

## Mobile & fallback

- Detect WebGL support; if absent, render a static poster image instead of a broken canvas.
- Respect `prefers-reduced-motion` — disable `autoRotate` and scroll-driven camera moves (shown above).
- On small screens, reduce `dpr` ceiling and drop post-processing.

## Verify

- Scene renders the model framed and lit; orbit works; no console WebGL warnings.
- On a throttled mobile profile it holds ~30fps+ and `frameloop="demand"` keeps it idle when still.
- reduced-motion on → no autorotate; WebGL off → poster fallback shows.

## Pitfalls

- **SSR crash in Next** — always `ssr:false` dynamic import; Three.js touches `window`.
- **Giant GLBs** — an uncompressed 40MB model tanks load; always `--transform`.
- **Lighting flatness** — one ambient light looks dead; use an `Environment` preset for free realism.
- **Memory leaks** — dispose/`useGLTF.clear()` on unmount for route changes with many models.
