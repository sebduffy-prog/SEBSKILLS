---
name: magnetic-cursor
description: Custom cursor dot that follows the mouse with spring lag, scales up over interactive elements, shrinks on mousedown, and uses mix-blend-mode:difference so it inverts against any background. Use when the user asks for a "custom cursor", "cursor follower", "blend mode cursor", "Awwwards cursor", "cursor dot", "interactive cursor", "cursor that grows on links", or wants to replace the native cursor sitewide. Framer category — Interactions.
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
