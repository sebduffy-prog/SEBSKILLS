---
name: image-shatter
description: Build a React/Next.js component that shatters an image into a grid of tiles on hover, with each tile flying outward/rotating with spring physics and a magnetic cursor attraction. Use this skill whenever the user asks for an "image shatter", "shatter effect", "broken glass image", "tiled image hover", "image explosion", or "tiles that fly apart on hover". Also use when the user references the Framer Image Shatter component, or describes the effect as "image breaks into pieces when you hover", "photo splits into a grid that scatters", "puzzle pieces that fall apart with the cursor". Trigger even without exact naming — e.g. "I want the hero image to explode on hover", "photo that feels like it's breaking when you touch it".
---

# Image Shatter Component

Generates a React component that displays an image as a grid of tiles (typically 14×8 = 112 tiles). On hover, each tile flies outward in a random direction with a random rotation, governed by spring physics via framer-motion. Optionally, tiles also respond to cursor proximity with a magnetic effect (pulled toward the cursor, falloff by distance). On mouseleave they spring back into place.

The tiles use `background-image` with precisely calculated `backgroundPosition` so the grid forms a perfectly seamless image at rest, then flies apart coherently.

## What the effect looks like

A photo that, when you hover, appears to shatter like a glass mosaic — each tile taking a random trajectory with a springy bounce. Leave the element and tiles reassemble smoothly. If magnet strength is non-zero, nearby tiles drift toward the cursor before flying out.

## When to use

- User wants a dramatic hover effect on a hero image or portfolio piece
- User references "shatter", "explode", "break apart", "mosaic hover"
- User is building a site where the image is a focal point and needs "wow"
- User mentions Framer Image Shatter, or describes the effect

## What to produce

A single `.tsx` file called `ImageShatter.tsx`. **One dependency:** `framer-motion` (for spring physics and motion values).

### Install

```bash
npm install framer-motion
```

### Usage

```tsx
import ImageShatter from "@/components/ImageShatter";

<div style={{ width: 800, height: 500 }}>
  <ImageShatter
    image={{ src: "/hero.jpg", alt: "Hero" }}
    tilesX={14}              // tiles per row
    tilesY={8}               // tiles per column
    maxOffset={120}          // max px each tile flies outward
    maxRotate={18}           // max deg rotation per tile
    seed={42}                // random seed — same seed = same pattern
    springStiffness={220}
    springDamping={22}
    magnetStrength={0}       // 0 = no magnet; 30-60 = noticeable pull
    magnetRadius={200}       // px
    reassembleDelay={0}      // ms delay before tiles fly back
    imageFit="cover"         // cover | contain | fill | none | scale-down
  />
</div>
```

## Implementation notes

1. **Tile edges must snap to the device-pixel grid.** Without this, you'll see 1-pixel seams between tiles when the image is at rest. The asset rounds `colEdges[i] = Math.floor(i * Nw / tx) / dpr` — don't simplify.

2. **BLEED = 1px.** Each tile is rendered 1px larger on each side than its grid cell, to overlap neighbours and hide any sub-pixel seams. Don't remove this.

3. **`background-image` + computed `backgroundPosition`.** Each tile has the full image as its background, but offset so only its portion shows. The formula is `backgroundPosition: (imgLeft - (tileLeft - bleed))px ...`. This is what makes the grid form a coherent image.

4. **object-fit in JavaScript, not CSS.** The `computeObjectFit` helper replicates CSS's `object-fit: cover/contain/fill/none/scale-down` in JS, because the tiles need to know the image's actual pixel extents and position within the container. Keep this logic.

5. **Spring-per-tile, not animated per frame.** Each tile gets its own `useSpring` chain: `target → raw (+ magnet) → spring`. Framer-motion handles the RAF loop internally. Don't try to compute positions in a single `useEffect` — 100+ tiles * 60fps is not the way.

6. **Magnet effect uses cursor motion values.** `cursorX` / `cursorY` are `useMotionValue`s, updated via rAF-throttled mousemove. Each tile's `magX` / `magY` `useTransform` depends on `[hoverMV, cursorX, cursorY]` — only recomputes when those change.

7. **Prefers-reduced-motion respected.** If the user has `prefers-reduced-motion: reduce`, all tile offsets/rotations are zeroed. The asset checks `useReducedMotion()` from framer-motion.

8. **DPR cap.** Default 1.5 — on a 3× retina display, internal rendering stays at 1.5× to avoid memory blow-up on large tile counts.

9. **Responsive tile downscale.** If `responsiveTiles={true}` (default) and viewport < 640px wide, tile count drops to 70% of the specified values. 14×8 on mobile becomes 10×6.

## Next.js specifics

Needs `"use client"`.

Pass `image.src` as a path string. If using Next.js responsive images, pre-generate the URL you want and pass it directly — the component uses `new Image()` internally, not `next/image`.

## Props reference

| Prop | Type | Default | Description |
|---|---|---|---|
| `image` | `{ src: string; alt?: string; srcSet?: string; positionX?: string; positionY?: string; fit?: string }` | demo | Image to shatter |
| `imageFit` | `"cover" \| "contain" \| "fill" \| "none" \| "scale-down"` | `"cover"` | Object-fit behaviour |
| `tilesX` | number | 14 | Columns (min 2, max 40) |
| `tilesY` | number | 8 | Rows (min 2, max 40) |
| `maxOffset` | number | 120 | px — max distance a tile can fly |
| `maxRotate` | number | 18 | deg — max rotation per tile |
| `seed` | number | 42 | RNG seed for tile targets |
| `springStiffness` | number | 220 | 50-600 |
| `springDamping` | number | 22 | 5-60 |
| `magnetStrength` | number | 0 | 0-120 px — cursor attraction |
| `magnetRadius` | number | 200 | px — cursor attraction radius |
| `reassembleDelay` | number | 0 | ms — delay before tiles fly back on mouseleave |
| `dprCap` | number | 1.5 | Max device pixel ratio to render at |
| `responsiveTiles` | boolean | true | Drop tile count 30% on mobile |

## Common requests

- **"Make the shatter more violent"** — bump `maxOffset` to 250, `maxRotate` to 40, `springStiffness` to 400, `springDamping` to 15 (underdamped = more bounce).
- **"More subtle, more like a ripple"** — `maxOffset` 30, `maxRotate` 3, fewer tiles (8×5).
- **"Only shatter on click, not hover"** — replace `onMouseEnter/Leave` with `onClick` toggle and a `useState` for the on/off state.
- **"Tiles should fall downward (gravity)"** — override the random `target.y` generation to always positive values, scaled by distance from top. Small modification to `targets = useMemo(...)`.
- **"Reassemble in order (top-left first, bottom-right last)"** — add per-tile `transition.delay` based on `row * tx + col`.
- **"Use on video instead of image"** — more complex. The `background-image` approach doesn't work with video. Would need to render each tile as a `<canvas>` drawing a region of a `<video>` element every frame. Beyond this skill's scope.

## Attribution

Original from the Framer "Image_Shatter" module. The technique (tiled background + spring physics + cursor magnet) is a composition of standard framer-motion patterns. For personal/experimental use this adaptation is clean; the shatter grid math is the only non-trivial part and is fully reproduced here with credit to Framer.
