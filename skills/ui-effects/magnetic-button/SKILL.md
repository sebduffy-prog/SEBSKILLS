---
name: magnetic-button
description: React button that attracts toward the cursor when it's within a radius, with spring-damped follow and elastic snap-back on exit. Use when the user asks for a "magnetic button", "sticky button", "cursor-follow button", "button that pulls toward cursor", "Awwwards-style button", references Framer magnetic CTAs, or wants hero/CTA buttons with tactile physicality. Framer category — Buttons.
---

# Magnetic Button

A button that subtly chases the mouse cursor when the cursor enters an invisible radius around it, then springs back to its resting position on exit. Physics runs on a single `requestAnimationFrame` loop using stiffness + damping — no external motion library.

## When to use

- Hero CTAs on high-polish marketing sites
- Primary "Book a call", "Get started" actions
- Any place you want a playful but not distracting interaction

## What to produce

`assets/MagneticButton.tsx` — single file, React only.

```tsx
import MagneticButton from "@/components/MagneticButton";

<MagneticButton onClick={() => alert("hi")}>
  Get started →
</MagneticButton>

// Customise pull strength + range
<MagneticButton strength={0.6} radius={160} stiffness={0.15} damping={0.75}>
  Book a call
</MagneticButton>
```

## Props

| Prop | Type | Default | Notes |
|---|---|---|---|
| `strength` | number | `0.4` | 0–1. Fraction of cursor offset applied as translation. |
| `radius` | number | `120` | px. Cursor must be within this radius to pull the button. |
| `stiffness` | number | `0.12` | Spring stiffness (per-frame). Higher = snappier. |
| `damping` | number | `0.7` | Velocity damping (0–1). Lower = bouncier. |
| `as` | string | `"button"` | Render as any HTML tag (`a`, `div`, etc.). |

## Implementation notes

- Uses a global `mousemove` listener so the button can "feel" the cursor before it enters the element itself.
- Spring is integrated as `v += (target - cur) * stiffness; v *= damping; cur += v` — this is the standard "toxi / pop-motion" spring model. Cheap and stable.
- Content is wrapped in a `<span>` with `pointerEvents: none` so hover on the label doesn't fire extra `mouseleave` on the button itself.
- `will-change: transform` and `translate3d` force GPU compositing; no layout thrash.

## Common tweaks

- **Stronger pull:** raise `strength` to 0.7, drop `damping` to 0.6.
- **Label trails button:** wrap the inner `<span>` in another MagneticButton with lower strength — nested magnetism.
- **Accessibility:** prefers-reduced-motion — wrap the effect in `if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;` inside the effect. Left out by default to keep the file tiny.

## Attribution

Inspired by the standard Framer marketplace magnetic-button pattern. Physics loop is generic spring integration, reimplemented from scratch.
