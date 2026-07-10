---
name: svg-illustration-animation
category: frontend-and-design
description: >-
  Animate SVG illustrations with GSAP's now-free (since 2025) plugins — DrawSVGPlugin
  for self-drawing line art, MorphSVGPlugin for shape-to-shape morphs, and MotionPathPlugin
  for moving/orienting elements along a path. Reach for this to build a hand-drawn signature
  reveal, a logo that morphs between icons, a plane that flies a curved route, an animated
  hero illustration, a loading/checkmark stroke, or an SVG data-viz that draws in. Covers
  correct plugin registration, the exact drawSVG / morphSVG / motionPath syntax, CDN + npm
  setup, ScrollTrigger scrubbing, and prefers-reduced-motion. Grounded on gsap.com 3.13.
when_to_use:
  - You have inline SVG line art and want it to "draw itself" (stroke reveal / signature / checkmark)
  - You need to morph one SVG shape into another (icon toggle, logo blend, liquid shape change)
  - An element must travel along a curved SVG path and rotate to face its direction of travel
  - Building an animated hero, explainer, or infographic where SVG strokes/shapes reveal on scroll
  - You want production-correct GSAP plugin registration + CDN/npm setup that actually runs
when_not_to_use:
  - Pure CSS enter/exit token system with no SVG geometry — use motion-system
  - A named icon set / sprite pipeline without bespoke animation — use icon-system
  - WebGL / 3D scene work — use webgl-3d-scene
  - One-off Framer-style DOM effect (marquee, magnetic, scramble) — use that effect's own skill
  - Building the SVG chart data model itself, not animating it — use dataviz
keywords:
  - svg
  - gsap
  - drawsvg
  - morphsvg
  - motionpath
  - animation
  - stroke-dashoffset
  - path-morph
  - line-draw
  - scrolltrigger
  - illustration
  - vector-animation
  - registerplugin
  - self-drawing
  - checkmark
similar_to:
  - motion-system
  - icon-system
  - webgl-3d-scene
inputs_needed: >-
  Inline SVG markup (paths must be real <path>/<line>/<polyline>, or primitives you convert);
  a target look (draw / morph / path-motion); whether it triggers on load, scroll, or interaction.
produces: >-
  A working HTML/JS snippet wiring GSAP 3.13 + the relevant plugin(s) to your SVG, with correct
  registration, timing, ScrollTrigger scrubbing where asked, and a reduced-motion fallback.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# SVG Illustration Animation (GSAP DrawSVG · MorphSVG · MotionPath)

Animate real SVG geometry with GSAP's three SVG plugins. As of the Webflow-backed
release in **2025, every GSAP plugin — including the former Club-only DrawSVGPlugin,
MorphSVGPlugin and MotionPathPlugin — is 100% free for commercial use** and published
to public npm/CDN. Use **GSAP 3.13 or later**; older versions still gate these behind a
private registry.

## When to use

Pick the plugin by intent:

| Want | Plugin | Core property |
|------|--------|---------------|
| Line art that draws itself | `DrawSVGPlugin` | `drawSVG` |
| One shape becomes another | `MorphSVGPlugin` | `morphSVG` |
| Element flies along a path | `MotionPathPlugin` | `motionPath` |

All three animate **inline** `<svg>` — not `<img src="x.svg">` or CSS `background`.
The SVG must be in the DOM so GSAP can reach its geometry.

## Prerequisites

- GSAP 3.13+ core plus the plugin(s) you need.
- Inline SVG. `drawSVG` needs a **visible stroke** (`stroke` + `stroke-width`, `fill:none`
  for open paths). `morphSVG` needs `<path>` elements — convert primitives first (below).
- **Register every plugin once** before tweening, or tweens silently no-op.

### CDN setup (grounded — GSAP 3.13.0 on cdnjs)

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.13.0/gsap.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.13.0/DrawSVGPlugin.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.13.0/MorphSVGPlugin.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.13.0/MotionPathPlugin.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.13.0/ScrollTrigger.min.js"></script>
<script>
  gsap.registerPlugin(DrawSVGPlugin, MorphSVGPlugin, MotionPathPlugin, ScrollTrigger);
</script>
```

npm (bundler): `npm i gsap@^3.13` then
`import { gsap } from "gsap"; import { DrawSVGPlugin } from "gsap/DrawSVGPlugin";` etc.,
and the same `gsap.registerPlugin(...)`. Load only the plugins you actually use.

## Recipes

### 1 — Self-drawing line art (DrawSVG)

`drawSVG` describes the visible portion of the stroke as `"start end"` (percent or px).
`"0%"`/`0` = nothing; `"100%"` or `"0% 100%"` = whole stroke; `"20% 80%"` = middle band.
Animate **from** an empty stroke to reveal it:

```html
<svg viewBox="0 0 200 100" width="200">
  <path class="sig" d="M10,80 C40,10 90,10 110,60 S170,90 190,40"
        fill="none" stroke="#111" stroke-width="3" stroke-linecap="round"/>
</svg>
<script>
  gsap.from(".sig", { duration: 1.4, drawSVG: 0, ease: "power1.inOut" });
</script>
```

- **Multiple lines with stagger**: `gsap.from(".stroke", { drawSVG: 0, duration: 1, stagger: 0.15 })`.
- **Draw from the centre out**: `gsap.from(el, { drawSVG: "50% 50%", duration: 1 })`.
- **Responsive**: append `live` so lengths recompute on resize — `drawSVG: "20% 70% live"`.
- **Checkmark**: one `<path>` for the tick, `gsap.from(tick, { drawSVG: 0, duration: 0.5, ease: "power2.out" })`.

### 2 — Shape morph (MorphSVG)

Simplest form is a selector — GSAP interpolates the current path's `d` toward the target's:

```html
<svg viewBox="0 0 100 100" width="120">
  <path id="start" d="M20,20 H80 V80 H20 Z" fill="#e11"/>
  <path id="end"   d="M50,10 L90,90 L10,90 Z" fill="#11e" style="display:none"/>
</svg>
<script>
  gsap.to("#start", { duration: 1, morphSVG: "#end", ease: "power2.inOut", repeat: -1, yoyo: true });
</script>
```

Fine-tune with the object form when a morph twists or collapses awkwardly:

```js
gsap.to("#start", {
  duration: 1,
  morphSVG: {
    shape: "#end",
    type: "rotational",      // "linear" (default) vs "rotational" — rotational usually looks cleaner
    shapeIndex: 3,           // rotate which start point maps to the target's first point (try values)
    map: "complexity",       // point-matching: "size" | "position" (default) | "complexity"
    origin: "50% 50%"
  }
});
```

**Primitives must be paths.** `morphSVG` only tweens `<path>`. Convert first:

```js
MorphSVGPlugin.convertToPath("circle, rect, ellipse, line, polygon, polyline");
```

Morph to raw data (no target element needed): `morphSVG: "M10,10 L90,90 ..."`.

### 3 — Move along a path (MotionPath)

Send an element down an SVG path and orient it to the tangent with `autoRotate`:

```html
<svg viewBox="0 0 400 200" width="400">
  <path id="route" d="M20,180 Q200,-40 380,180" fill="none" stroke="#ccc"/>
  <path id="plane" d="M0,-6 L14,0 L0,6 L4,0 Z" fill="#111"/>
</svg>
<script>
  gsap.to("#plane", {
    duration: 3, repeat: -1, ease: "none",
    motionPath: {
      path: "#route",
      align: "#route",        // put the element into the path's coordinate space
      alignOrigin: [0.5, 0.5],// anchor its centre on the path
      autoRotate: true,        // rotate to face travel direction (or a number for a fixed offset)
      start: 0, end: 1         // scrub a sub-range, e.g. 0.25→0.75
    }
  });
</script>
```

`path` also accepts an array of points — `path: [{x:0,y:0},{x:100,y:50},{x:200,y:0}]` —
which GSAP smooths into a curve, no SVG path element required.

### 4 — Scrub any of the above on scroll (ScrollTrigger)

Tie progress to scroll instead of time — great for hero illustrations and infographics:

```js
gsap.from(".sig", {
  drawSVG: 0,
  ease: "none",
  scrollTrigger: { trigger: ".hero", start: "top 80%", end: "bottom 40%", scrub: true }
});
```

Same pattern works with `morphSVG` and `motionPath` — put the tween vars alongside a
`scrollTrigger` block. Use a GSAP **timeline** to choreograph draw → morph → move in sequence.

### 5 — Respect reduced motion

Wrap decorative motion so it snaps to the end state for users who opt out:

```js
const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
if (reduce) {
  gsap.set(".sig", { drawSVG: "100%" });   // final, static state
} else {
  gsap.from(".sig", { drawSVG: 0, duration: 1.4 });
}
```

## Verify

- Open the page; the animation runs with **no console errors**. A silent no-op almost always
  means the plugin was not registered — confirm `gsap.registerPlugin(...)` ran before the tween.
- DrawSVG: the stroke actually grows. If nothing shows, the path has no visible `stroke`/`stroke-width`,
  or `fill` is hiding an open path (set `fill:none`).
- MorphSVG: shapes interpolate smoothly. Kinks/flips → adjust `shapeIndex` or switch `type:"rotational"`.
- MotionPath: element tracks the curve and (with `autoRotate`) noses into the direction of travel.
- Quick registration check in console: `typeof DrawSVGPlugin !== "undefined"` → `true`.

## Pitfalls

- **Not registered** — the #1 issue. Every plugin needs `gsap.registerPlugin()` once, up front.
- **Version too old** — these plugins are only public/free on **GSAP 3.13+**. Earlier versions
  404 the CDN files or require the old Club registry. Pin `3.13.0` (or later) in CDN URLs and npm.
- **`<img>` / CSS background SVG** — GSAP can't reach the geometry. The SVG must be **inline** in the DOM.
- **Morphing non-paths** — `<circle>`/`<rect>` etc. must be run through `MorphSVGPlugin.convertToPath()` first.
- **DrawSVG needs a stroke** — a fill-only shape has nothing to draw; give it `stroke` + `stroke-width`.
- **MotionPath without `align`** — the element jumps to the path's raw coordinates. Set `align` to the
  same path and `alignOrigin:[0.5,0.5]` to anchor it correctly.
- **Claude Artifacts / strict CSP** — external CDN scripts are blocked, so GSAP won't load there. Ship
  these on a normal web page (or bundle GSAP via npm and inline it) rather than inside a sandboxed Artifact.
- **React double-run** — create tweens inside `useEffect`/`useGSAP` and return a cleanup that
  `.kill()`s them, or StrictMode's double-mount stacks duplicate animations.
