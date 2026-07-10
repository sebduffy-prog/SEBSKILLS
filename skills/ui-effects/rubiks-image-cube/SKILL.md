---
name: rubiks-image-cube
category: ui-effects
description: >
  Build an interactive 3D Rubik's cube component in React/Next.js using CSS 3D
  transforms and framer-motion. Each face can display either colour tiles or a
  3x3 grid of image segments. Use this skill whenever the user asks for a
  "Rubik's cube", "3D image cube", "rotating image cube", "interactive cube",
  "draggable 3D cube", or wants to display images on the faces of a 3D cube.
  Also use when the user references the Framer Rubix Image Cube component, or
  describes wanting to show photos / images / a portfolio on a rotatable 3D
  cube with shuffle and reset controls. Trigger this even if the user just
  describes wanting a playful 3D photo display or a cube hero element.
when_to_use:
  - User wants a 3D cube with images on each face
  - User references "Rubik's cube", "rubix cube", "3D photo cube", or "image cube"
  - User is building a portfolio, gallery, or interactive hero and wants a draggable 3D element
  - User describes showing 6 images (or 54 images) on a rotatable cube with shuffle/reset controls
  - User references the Framer Rubix Image Cube component
  - User just describes a playful 3D photo display or cube hero element
when_not_to_use:
  - User needs a true Rubik's solver or real face-turn mechanics — the shuffle here is cosmetic; point at cubejs/cube-solver
  - Scenes needing real lighting/shadows or WebGL — this is pure CSS 3D, use Three.js instead
  - A single image with a dramatic hover break-apart effect — use sibling skill image-shatter
  - Flat image distortion/hover effects rather than a 3D object — see interactive-distortion or liquid-image
keywords:
  - rubiks cube
  - rubix cube
  - 3d cube
  - image cube
  - photo cube
  - rotating cube
  - draggable cube
  - interactive cube
  - css 3d transforms
  - framer-motion
  - react
  - nextjs
  - portfolio
  - gallery
  - hero element
  - shuffle
  - image slicing
  - preserve-3d
similar_to:
  - image-shatter
  - interactive-distortion
  - liquid-image
inputs_needed:
  - Colour tiles or image faces (useImages) — and if images, one image sliced 3x3 per face or 9 distinct images per face (paths for up to 6 faces)
  - Cube sizing (cubeSize, gap) and behaviour (autoRotate, rotationSpeed, showControls)
  - Whether it is a Next.js project (needs "use client" and /public image paths)
produces: A single RubiksCube.tsx React component (framer-motion as the only extra dependency) rendering a drag-rotatable 3D cube with shuffle/reset controls.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Rubik's Image Cube Component

Generates a React component rendering an interactive 3D cube with six 3×3 faces. Each face can show either solid colours (classic Rubik's) or image segments (a single image sliced 3×3, or nine separate images). The cube is drag-rotatable, can auto-rotate, and has shuffle/reset controls.

Built with pure CSS 3D transforms plus `framer-motion` for the rotation animation — no WebGL required. Works anywhere React works.

## When to use

- User wants a 3D cube with images on each face
- User references "Rubik's cube", "rubix cube", "3D photo cube", "image cube"
- User is building a portfolio, gallery, or interactive hero and wants a draggable 3D element
- User describes wanting to "show 6 images / 54 images on a rotatable cube"

## What to produce

A **single `.tsx` file** (or `.jsx`) called `RubiksCube.tsx`. One dependency beyond React: `framer-motion`.

### Install dependency

```bash
npm install framer-motion
```

### Usage — classic colour cube

```tsx
import RubiksCube from "@/components/RubiksCube";

<RubiksCube
  cubeSize={60}
  gap={2}
  rotationSpeed={0.5}
  autoRotate
  showControls
/>
```

### Usage — one image per face, sliced 3×3

```tsx
<RubiksCube
  useImages
  cubeSize={80}
  frontImages={[{ src: "/front.jpg" }]}    // single image gets sliced into 9 tiles
  backImages={[{ src: "/back.jpg" }]}
  topImages={[{ src: "/top.jpg" }]}
  bottomImages={[{ src: "/bottom.jpg" }]}
  leftImages={[{ src: "/left.jpg" }]}
  rightImages={[{ src: "/right.jpg" }]}
/>
```

### Usage — 9 distinct images per face (54 total, one per tile)

```tsx
<RubiksCube
  useImages
  frontImages={Array.from({ length: 9 }, (_, i) => ({ src: `/front-${i}.jpg` }))}
  // ... same for other five faces
/>
```

## Implementation notes

1. **Pure CSS 3D, not WebGL.** The cube is six `<div>` faces positioned via `translateZ(cubeSize * 1.5)` and rotated into place. This is cheap and accessible. Don't replace with Three.js unless you need real lighting / shadows.

2. **`perspective` on the parent.** The outer container must have `perspective: 1000px` (the asset does this). Without it, the cube renders flat.

3. **`transform-style: preserve-3d`.** The rotating inner container must have this, otherwise faces will composite in 2D and disappear.

4. **Image slicing via `backgroundPosition`.** For the "one image per face" case, each of the 9 tiles uses `backgroundImage: url(face.jpg)` with `backgroundSize: ${cubeSize*3}px ${cubeSize*3}px` and `backgroundPosition: -{col*size}px -{row*size}px`. This slices without needing separate image files.

5. **Rotation state is `{x, y, z}` in degrees.** Drag updates `rotation.y += deltaX * speed`, `rotation.x += deltaY * speed`. Framer-motion animates the `rotateX/Y/Z` smoothly.

6. **Global mouse handlers while dragging.** The drag listener is attached to `document` (not the cube container) once dragging starts, so the user can drag off-element. The asset handles this with an effect.

7. **The shuffle animation is cosmetic.** `rotateFace()` only properly rotates the front face + its adjacent edges. Other faces rotate their own 3×3 but don't propagate to neighbours. This matches the Framer module's behaviour. If the user wants a true Rubik's solver, that's a much bigger project — flag it.

## Next.js specifics

Include `"use client"` at the top of `RubiksCube.tsx` — framer-motion + drag handlers require the browser.

Place images in `/public` and pass the paths as `src` strings. Don't pass `next/image` StaticImageData objects (the asset uses the raw `src` string in `backgroundImage: url(...)`).

## Props reference

| Prop | Type | Default | Description |
|---|---|---|---|
| `cubeSize` | number | 60 | Side length of one 3×3 tile, in px |
| `gap` | number | 2 | Gap between tiles, in px |
| `rotationSpeed` | number | 0.5 | Drag-to-rotation multiplier |
| `shuffleSpeed` | number | 500 | Total shuffle animation duration, ms |
| `autoRotate` | boolean | false | Spin the cube when idle |
| `showControls` | boolean | true | Display Shuffle/Reset buttons |
| `useImages` | boolean | false | Switch from colour tiles to image tiles |
| `frontImages` etc. | `{src: string}[]` | `[]` | Images for each face (see usage) |
| `backgroundColor` | string | "#000000" | Gap / behind-tile colour |
| `borderRadius` | number | 4 | Tile corner radius, px |

## Common requests

- **"Don't show the controls, I'll make my own"** — set `showControls={false}`. Lift the shuffle/reset functions up via a ref with `useImperativeHandle`, or pass them down as callbacks (needs small modification to the asset).
- **"Clicking the cube should do something custom"** — the asset currently does a quick shuffle on click-without-drag. Edit the `onClick` handler in the cube container div.
- **"I want each tile to be clickable individually"** — add `onClick` to each tile in `renderSegment`. The callback can receive `(face, index)` to identify which tile was clicked.
- **"Make it responsive"** — the cube uses fixed `cubeSize` in px. For responsive, compute `cubeSize` from `useWindowSize` or a container ref.
- **"Add a proper Rubik's solver"** — outside scope. Point the user at libraries like `cubejs` or `cube-solver`.

## Attribution

Original component from the Framer "Rubix Image Cube" module. This skill is for personal/experimental use. The technique (CSS 3D transforms + framer-motion) is standard web tech and re-implementing from scratch is straightforward if you need to ship commercially.
