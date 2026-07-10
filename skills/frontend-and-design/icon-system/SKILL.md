---
name: icon-system
category: frontend-and-design
description: >-
  Stand up ONE consistent icon system instead of pasting random SVGs from
  everywhere — pick a source (Lucide for a curated stroke set, Iconify for
  200k+ on-demand icons), optimise every SVG with SVGO (preserving viewBox and
  currentColor), and expose stroke-width + size tokens plus a sprite or
  component wrapper so icons scale, recolour and align as one family. Reach for
  this when icons look mismatched (different strokes, filled vs outline, hard-coded
  colours), when SVGs bloat the bundle, or when you need a single Icon primitive.
  Grounded on lucide.dev, svgo.dev and iconify.design.
when_to_use:
  - Icons in the UI are visually inconsistent (mixed stroke weights, filled + outline, off-grid sizes)
  - You are choosing an icon source and want Lucide vs Iconify vs hand-rolled sprite decided on real tradeoffs
  - Raw SVGs are bloating the bundle or carry hard-coded fills/width/height that block theming
  - You want a single <Icon> component or SVG sprite with size + stroke tokens instead of scattered inline SVG
  - You need icons to inherit text colour (currentColor) and respond to a theme or dark mode
when_not_to_use:
  - Designing/animating a bespoke illustration or logo — use svg-illustration-animation
  - Defining the colour palette itself — use brand-color-token-system or oklch-color-engine
  - Building the motion/timing vocabulary for icon transitions — use motion-system
  - A multi-colour app icon / favicon export pipeline only — that is asset generation, not an icon system
keywords:
  - icons
  - lucide
  - iconify
  - svgo
  - svg-sprite
  - icon-component
  - stroke-width
  - currentcolor
  - viewbox
  - design-tokens
  - svg-optimisation
  - symbol-use
  - icon-font
  - tree-shaking
similar_to:
  - brand-color-token-system
  - oklch-color-engine
  - motion-system
  - svg-illustration-animation
  - fluid-responsive-system
inputs_needed: >-
  A framework/target (React, Vue, vanilla, or plain HTML), a chosen or preferred
  icon source, and any existing SVGs or brand stroke/size preferences.
produces: >-
  An icon source decision, an SVGO config, size + stroke tokens, and either an
  <Icon> wrapper component or an optimised SVG sprite with usage snippets.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Icon System

Turn a pile of ad-hoc SVGs into one coherent, tokenised icon family. Decide the
source, optimise every asset the same way, and ship a single primitive.

## When to use

Use this when icons feel like they came from five different places, when SVGs
carry hard-coded `fill="#333"` / `width="18"` that fight your theme, or when you
want a defensible answer to "which icon library?" and a repeatable optimise step.

## Prerequisites

- Node 18+ and npm (for SVGO and any React/Vue package).
- `npx` available (all commands below use it, so nothing needs global install).
- Verify the toolchain before you commit to it:

```bash
npx --yes svgo --version        # SVGO CLI
node -v                         # 18+ expected
```

## Step 1 — Pick the source (decide once, write it down)

| Source | Best when | Install | Cost |
|--------|-----------|---------|------|
| **Lucide** | You want ONE curated, consistent 24×24 stroke set that tree-shakes | `lucide-react` / `lucide` | Bundled, ~each icon is a component |
| **Iconify** | You need breadth — 200k+ icons across 150+ sets, loaded on demand | `@iconify/react` (or `iconify-icon`) | Runtime API fetch (or bundle offline) |
| **Own sprite** | Fixed, small set of custom/brand glyphs; zero runtime deps | your SVGs + SVGO | You maintain the SVGs |

Rules of thumb: **one source per project** for visual consistency. Lucide when a
single house stroke matters; Iconify when you need many icons and can accept the
on-demand fetch (or self-host the API). Roll your own sprite only for a small,
stable, custom set.

## Step 2 — Optimise every SVG the same way (SVGO)

Never ship raw exported SVG. Standardise with one config. Create
`svgo.config.mjs` — the two things that break icon systems are stripping the
`viewBox` (kills scaling) and baking in colours (kills theming):

```js
// svgo.config.mjs
export default {
  multipass: true,
  plugins: [
    {
      name: 'preset-default',
      params: {
        overrides: {
          removeViewBox: false,   // KEEP viewBox — required for scaling
          cleanupIds: false,      // keep if you reference ids elsewhere
        },
      },
    },
    'removeDimensions',           // drop width/height so CSS/size prop controls size
    { name: 'convertColors', params: { currentColor: true } }, // fills follow text colour
    { name: 'removeAttrs', params: { attrs: '(stroke-width)' } }, // let a token set stroke
  ],
};
```

Run it over your icon folder (recursive `-rf`, output to a build dir):

```bash
npx svgo -rf ./icons -o ./icons-optimised   # folder mode, recursive
npx svgo one.svg -o one.min.svg             # single file
```

If icons must keep their designed stroke, drop the `removeAttrs` line. If they
are multi-colour brand marks, drop the `convertColors` line so real colours survive.

## Step 3 — Define size + stroke tokens

Give every icon the same knobs. As CSS custom properties:

```css
:root {
  --icon-size-sm: 16px;
  --icon-size-md: 20px;
  --icon-size-lg: 24px;   /* Lucide's native grid — align to it */
  --icon-stroke: 2;       /* Lucide default is 2 */
}
.icon { width: var(--icon-size-md); height: var(--icon-size-md);
        stroke-width: var(--icon-stroke); color: inherit; }
```

Pick sizes on a small scale (16/20/24) and one default stroke. Consistency of
these two numbers is 90% of what makes a set "look like a system".

## Recipe A — Lucide (curated, tree-shaking)

```bash
npm install lucide-react
```

```jsx
import { Camera, ArrowRight } from 'lucide-react';

// Defaults: size=24, color="currentColor", strokeWidth=2
<Camera />
<ArrowRight size={20} strokeWidth={1.5} className="text-slate-600" />
```

Set project-wide defaults once so callers don't drift, via `LucideProvider` /
context, or a thin wrapper:

```jsx
// Icon.jsx — one place to enforce size + stroke tokens
import { icons } from 'lucide-react';
export function Icon({ name, size = 20, ...rest }) {
  const Cmp = icons[name];
  if (!Cmp) return null;                 // fail safe on unknown name
  return <Cmp size={size} strokeWidth={2} aria-hidden="true" {...rest} />;
}
```

`absoluteStrokeWidth` keeps the stroke a fixed px regardless of size (stops thin
strokes at small sizes / fat strokes at large sizes) — pass it when you scale a lot.
Vanilla HTML: `npm install lucide`, add `data-lucide="camera"` to an `<i>`, then
call `lucide.createIcons()`.

## Recipe B — Iconify (breadth, on-demand)

```bash
npm install @iconify/react
```

```jsx
import { Icon } from '@iconify/react';

// One syntax for 200k+ icons: "prefix:name". Height defaults to 1em.
<Icon icon="lucide:camera" width="20" height="20" />
<Icon icon="mdi:home" className="text-blue-600" />  // inherits currentColor
```

`icon` is `set:name` (e.g. `lucide:*`, `mdi:*`, `tabler:*`). Icons load on demand
from the Iconify API — for offline/no-network builds, self-host the API or import
icon objects directly. Framework-agnostic web component:
`npm install iconify-icon` then `<iconify-icon icon="mdi:home"></iconify-icon>`.

## Recipe C — Own SVG sprite (`<symbol>` + `<use>`)

Bundle a small custom set into one file, reference by id, style with CSS. Build
the sprite from the optimised folder with a tiny Node script:

```js
// build-sprite.mjs — concat optimised SVGs into one <symbol> sheet
import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
const dir = './icons-optimised';
const symbols = readdirSync(dir).filter(f => f.endsWith('.svg')).map(f => {
  const id = f.replace(/\.svg$/, '');
  const body = readFileSync(`${dir}/${f}`, 'utf8')
    .replace(/<svg[^>]*viewBox="([^"]*)"[^>]*>/, `<symbol id="i-${id}" viewBox="$1">`)
    .replace(/<\/svg>/, '</symbol>');
  return body;
});
writeFileSync('./sprite.svg',
  `<svg xmlns="http://www.w3.org/2000/svg" style="display:none">${symbols.join('')}</svg>`);
```

```bash
node build-sprite.mjs
```

Use it (inline the sprite once, then reference anywhere):

```html
<svg class="icon" aria-hidden="true"><use href="/sprite.svg#i-camera" /></svg>
```

`currentColor` in the source means each `<use>` picks up the surrounding text
colour — theming for free. (Or use `svg-sprite` / `svgstore-cli` if you prefer a
maintained CLI over the script.)

## Verify

- `npx svgo -rf ./icons -o ./out` runs clean and files shrink — spot-check one
  optimised file still contains `viewBox` and no hard-coded `width=`/`fill=`.
- Render an icon at 16/20/24 and confirm it stays crisp and centred (viewBox intact).
- Set a parent `color:` and confirm the icon recolours (currentColor working).
- Toggle dark mode / a text colour change — icons follow with no per-icon edits.
- One source only: grep the codebase for stray inline `<svg>` blocks that bypass
  the system (`grep -rn "<svg" src | grep -v Icon`).

## Pitfalls

- **Removing viewBox** — SVGO's `removeViewBox` defaults to ON inside
  `preset-default`; it silently breaks scaling. Always override it to `false`.
- **Baked-in colour** — icons with `fill="#000"` ignore your theme. Convert to
  `currentColor` (Step 2) unless the icon is genuinely multi-colour.
- **Mixing sources** — Lucide + Font Awesome + random Figma exports never align.
  Different grids, strokes and optical sizing read as "unpolished". Commit to one.
- **Icon fonts for new work** — ligature icon fonts (old Material) have a11y and
  rendering downsides; prefer SVG (sprite/component). Only keep a font if legacy-locked.
- **Iconify offline** — the default `@iconify/react` fetches from the API at
  runtime; in an air-gapped or SSR-critical build, bundle icon data or self-host.
- **Missing a11y** — decorative icons need `aria-hidden="true"`; icons that carry
  meaning (a lone icon button) need an accessible label (`aria-label`) on the control.
- **Per-caller drift** — if every call site sets its own size/stroke, the system
  erodes. Route everything through the `<Icon>` wrapper or shared tokens.
