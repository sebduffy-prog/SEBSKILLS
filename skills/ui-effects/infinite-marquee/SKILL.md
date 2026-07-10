---
name: infinite-marquee
category: ui-effects
description: >
  Seamless infinite horizontal marquee / logo ticker in React using pure CSS
  animation — duplicates children, scrolls forever, pauses on hover, supports
  gradient edge fade. Use when the user asks for a "logo strip", "infinite
  marquee", "logo ticker", "marquee", "brand strip", "endless carousel",
  "scrolling logos", "ticker tape", or wants to loop press/partner logos
  across a hero. Framer category — Carousels.
when_to_use:
  - '"As seen in" / press-logo strips'
  - Partner / customer logo walls
  - Testimonial auto-scroll strips
  - Looping press/partner logos across a hero section
  - Anywhere ambient horizontal motion is wanted (ticker tape, brand strip)
when_not_to_use:
  - Vertical or scroll-position-driven reveals — use scroll-reveal-section
  - Children without intrinsic width (flex: 1 items) break the width: max-content layout
  - Interactive/swipeable carousels where users control position — this is ambient, non-interactive motion
  - Fewer than ~4 items — the loop feels stepped; provide 4-6+ children
keywords:
  - marquee
  - infinite marquee
  - logo ticker
  - logo strip
  - brand strip
  - ticker tape
  - scrolling logos
  - endless carousel
  - press logos
  - partner logos
  - logo wall
  - pause on hover
  - gradient edge fade
  - pure css animation
  - react
  - carousels
similar_to:
  - scroll-reveal-section
  - animated-counter
inputs_needed:
  - Children to loop (logos/images/testimonials) — at least 4-6 items with intrinsic width
  - Page background colour for fadeColor (invisible edge fade)
  - Speed (seconds per loop), direction (left/right), gap, pauseOnHover preference
  - Whether prefers-reduced-motion support is in scope (not wired by default)
produces: assets/InfiniteMarquee.tsx — single-file React component with pure CSS infinite-loop animation
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Infinite Marquee

Horizontal strip that scrolls its children leftwards (or right) forever. Duplicates the child list once so the seam is invisible — when the first copy reaches -50%, the second copy has taken its exact position.

## When to use

- "As seen in" / press-logo strips
- Partner / customer logo walls
- Testimonial auto-scroll
- Anywhere you want ambient horizontal motion

## What to produce

`assets/InfiniteMarquee.tsx` — single file, React only, pure CSS animation.

```tsx
import InfiniteMarquee from "@/components/InfiniteMarquee";

<InfiniteMarquee speed={40} fadeColor="#0b0b0b">
  {logos.map((src) => <img key={src} src={src} alt="" height={40} />)}
</InfiniteMarquee>

// Faster, no hover pause, right-to-left:
<InfiniteMarquee speed={20} direction="right" pauseOnHover={false}>
  ...
</InfiniteMarquee>
```

## Props

| Prop | Type | Default | Notes |
|---|---|---|---|
| `speed` | number | `40` | Seconds per full loop. Lower = faster. |
| `direction` | `"left" \| "right"` | `"left"` | Scroll direction. |
| `pauseOnHover` | boolean | `true` | Hover freezes the animation. |
| `gap` | number | `32` | px between children. |
| `fade` | boolean | `true` | Left/right gradient edge fade. |
| `fadeColor` | string | `"white"` | Should match your page background for invisible fade. |

## Implementation notes

- **Duplicated children.** To make the seam invisible, we render `[...items, ...items]` and animate the track from `0%` → `-50%`. At `-50%` the layout is identical to `0%`, so the loop restarts imperceptibly.
- **Pure CSS animation.** No `requestAnimationFrame`, no IntersectionObserver. Browser-optimised, runs even off-thread when possible.
- **Edge fades.** Two absolute-positioned gradient overlays left and right. Set `fadeColor` to the containing page background.
- **Hover pause.** Implemented via a scoped class name so multiple marquees on one page don't collide.

## Caveats

- Children must have intrinsic width (images with explicit height, fixed-width divs). Flex items with `flex: 1` will break the layout because we use `width: max-content`.
- If you provide 1 child only, doubling still works but the loop feels stepped. Provide at least 4–6 items for smooth motion.
- `prefers-reduced-motion`: not wired in by default. Add `@media (prefers-reduced-motion: reduce) { animation: none; }` to the track if accessibility is in-scope.

## Attribution

Standard Framer-marketplace marquee pattern. Pure-CSS approach is idiomatic web tech — no Framer code reused.
