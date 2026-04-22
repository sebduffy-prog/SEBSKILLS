---
name: scroll-reveal-section
description: React wrapper that fades and slides its children into view with stagger as the section enters the viewport. IntersectionObserver + CSS transitions, respects prefers-reduced-motion. Use when the user asks for a "scroll reveal", "fade in on scroll", "slide in on scroll", "scroll animation", "stagger reveal", "AOS-style animation", "sections that animate on scroll", or wants each section to appear as the user scrolls down. Framer category — Sections.
---

# Scroll Reveal Section

Wrap any group of children with `<ScrollReveal>`. When the wrapper enters the viewport (≥ `threshold` visible), each child transitions from a hidden state (translated + transparent) to its resting state, staggered by index.

## When to use

- Landing-page sections that should feel alive as you scroll
- Stat blocks, feature rows, testimonial columns
- Anywhere you'd reach for AOS / ScrollTrigger but want a 1-file dependency-free solution

## What to produce

`assets/ScrollReveal.tsx`.

```tsx
import ScrollReveal from "@/components/ScrollReveal";

<ScrollReveal direction="up" stagger={120}>
  <h2>How it works</h2>
  <p>Step one…</p>
  <p>Step two…</p>
  <p>Step three…</p>
</ScrollReveal>

// Section header + three cards with heavier stagger:
<ScrollReveal direction="up" distance={48} stagger={150}>
  <h2>Features</h2>
  <div className="grid-3">...</div>
</ScrollReveal>
```

## Props

| Prop | Type | Default | Notes |
|---|---|---|---|
| `direction` | `"up" \| "down" \| "left" \| "right" \| "none"` | `"up"` | Direction children translate from. |
| `distance` | number | `32` | px of translation at rest. |
| `duration` | number | `700` | ms. |
| `delay` | number | `0` | ms added to every child. |
| `stagger` | number | `80` | ms between successive children. |
| `threshold` | number | `0.2` | IntersectionObserver threshold (0–1). |
| `once` | boolean | `true` | If `false`, children re-hide when scrolled out. |

## Implementation notes

- **Single IntersectionObserver on the wrapper** — not one per child. We just drive a shared `visible` state; each child reads it and picks its own transition delay based on index.
- **Cubic-bezier(0.2, 0.8, 0.2, 1)** — snappy ease-out. Matches the Framer marketplace "reveal" feel better than `ease-out`.
- **`prefers-reduced-motion`.** If the user has that set, children skip animation and render visible immediately. Non-negotiable accessibility.
- **Staggered delays are computed as `delay + i * stagger`** — use this pattern if you want to add a leading delay (e.g. after the section header).
- **Children are wrapped in per-child `<div>`s** — these exist only to host the transform. If you can't afford the extra wrapper (e.g., inside tables or flex-critical layouts), fall back to a per-child approach.

## Caveats

- The child wrapper `<div>`s are `display: block` by default. If your original children were inline (spans, links), you'll see layout shifts. Add `style={{ display: "inline-block" }}` to the wrapper children, or inline-refactor the component.
- `once: false` re-animates on every re-entry — great for demos, distracting in production. Default is `true`.

## Attribution

Uses public browser APIs (IntersectionObserver, CSS transitions) in the standard scroll-reveal pattern. No Framer code reused.
