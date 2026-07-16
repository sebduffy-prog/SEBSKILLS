---
name: magnetic-cursor
category: ui-effects
description: >
  Custom cursor dot that follows the mouse with spring lag, scales up over
  interactive elements, shrinks on mousedown, and uses
  mix-blend-mode:difference so it inverts against any background. Use when the
  user asks for a "custom cursor", "cursor follower", "blend mode cursor",
  "Awwwards cursor", "cursor dot", "interactive cursor", "cursor that grows on
  links", or wants to replace the native cursor sitewide. Framer category —
  Interactions.
when_to_use:
  - User asks for a "custom cursor", "cursor follower", "cursor dot", or "Awwwards cursor"
  - User wants to replace the native cursor sitewide with a soft dot
  - Portfolio, agency, or editorial sites where premium mouse feel matters
  - Hero sections where the normal cursor feels cheap
  - Cursor should grow over links/buttons and shrink on mousedown
  - A blend-mode cursor that auto-inverts against dark and light sections
when_not_to_use:
  - Touch-first or mobile-only experiences — the component bails out on coarse pointers
  - Form-heavy pages where the native text cursor over inputs matters
  - Magnetic pull on a specific element rather than a global cursor — use magnetic-button
  - Cursor-driven image distortion or shatter — use interactive-distortion or image-shatter
keywords:
  - custom cursor
  - cursor follower
  - cursor dot
  - magnetic cursor
  - blend mode
  - mix-blend-mode difference
  - awwwards
  - spring lag
  - hover scale
  - interactive cursor
  - cursor grows on links
  - pointer
  - lerp
  - react
  - framer interactions
  - cursor none
similar_to:
  - magnetic-button
  - liquid-glass-button
  - interactive-distortion
inputs_needed:
  - Where to mount it (root layout, e.g. app/layout.tsx)
  - Desired size, color, and blend mode (difference vs normal)
  - Hover selector and hoverScale (which elements grow the dot; add data-cursor targets)
  - Whether to hide the native cursor sitewide (hideNativeCursor)
  - Spring feel (stiffness/damping) and z-index if modals sit above 9999
produces: assets/MagneticCursor.tsx — a globally-mounted React custom-cursor component
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Magnetic Cursor

A globally-mounted `<MagneticCursor />` that replaces the native cursor with a soft dot. The dot lerps toward the real cursor (giving it weight), scales up on any `a`, `button`, or `[data-cursor]` element, and shrinks briefly on mousedown. Uses `mix-blend-mode: difference` by default so it reads against both dark and light sections.

## When to use

- Portfolio / agency / editorial sites where premium mouse feel matters
- Hero sections where normal cursors feel cheap
- Pair with magnetic-button for compounding polish

## What to produce

`assets/MagneticCursor.tsx` — mount it once at the root (e.g., in `app/layout.tsx`):

```tsx
// app/layout.tsx
import MagneticCursor from "@/components/MagneticCursor";

export default function Layout({ children }) {
  return (
    <html>
      <body>
        <MagneticCursor />
        {children}
      </body>
    </html>
  );
}
```

Add `data-cursor` to anything else you want to grow the dot (draggables, cards, etc.):
```tsx
<div data-cursor className="hover-tile">...</div>
```

## Props

| Prop | Type | Default | Notes |
|---|---|---|---|
| `size` | number | `20` | px. Diameter at rest. |
| `color` | string | `"white"` | Any CSS color. With `difference`, white is usually right. |
| `blendMode` | CSS blend | `"difference"` | Try `"normal"` for a solid-colored cursor. |
| `hoverScale` | number | `2.8` | Multiplier when over interactive elements. |
| `hoverSelector` | string | `"a, button, [data-cursor]"` | Any valid CSS selector. |
| `hideNativeCursor` | boolean | `true` | Sets `cursor: none` on `<html>`. |
| `stiffness` / `damping` | number | `0.18` / `0.75` | Spring follow behavior. |

## Implementation notes

- **Touch devices bail out.** `matchMedia('(pointer: coarse)')` returns true on touch; the component does nothing.
- **Global listeners.** `mouseover`/`mouseout` on `document` (not the dot) — we use `.closest(selector)` so nested interactive elements still trigger scale.
- **Two springs.** One for position (lag behind cursor), one for scale (smooth resize). Both use the standard spring integration.
- **mix-blend-mode: difference.** Inverts the color of everything underneath, so a white dot auto-reads as black on white sections, white on dark sections. No theme switching required.
- **`pointer-events: none`.** Critical — without it, the dot blocks clicks.
- **`z-index: 9999`.** Above modals, below system chrome. Raise if your modals are 10k+.

## Caveats

- Blocks native text cursor over inputs. Add `textarea, input` to your `hoverSelector` if you want a different hover state there, or conditionally disable the component on form-heavy pages.
- Some users dislike custom cursors. Respect `prefers-reduced-motion` and `(pointer: coarse)` — the latter is handled; the former is left to you.
- With `mix-blend-mode: difference`, images render correctly but some WebGL canvases can flicker. Test on your heaviest backgrounds.

## Attribution

Standard Awwwards/Framer pattern. Implementation is vanilla DOM + React, no proprietary code.
