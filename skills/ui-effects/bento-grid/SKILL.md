---
name: bento-grid
description: Responsive bento-box grid layout for React — variable column/row spans per card, with 3D hover tilt + lift that tracks the cursor. Use when the user asks for a "bento grid", "bento box layout", "Apple-style feature grid", "dashboard card grid", "variable-span grid", "product features grid", or wants the Apple.com / Vercel-style mosaic of differently-sized tiles. Framer category — Layout.
---

# Bento Grid

CSS-grid-based bento layout. Exports two components:

- `<BentoGrid>` — the grid container (fixed number of equal-width columns, auto rows).
- `<BentoCard>` — a card that takes `colSpan` (1-4) and `rowSpan` (1-3) to create the bento irregularity. On hover the card tilts 3D toward the cursor and lifts.

## When to use

- Feature showcases ("what's in the box")
- Dashboards with mixed widget sizes
- Portfolio work-grids
- Apple/Vercel/Linear-style landing-page feature mosaics

## What to produce

`assets/BentoGrid.tsx`.

```tsx
import BentoGrid, { BentoCard } from "@/components/BentoGrid";

<BentoGrid columns={4} rowHeight={200}>
  <BentoCard colSpan={2} rowSpan={2}>
    <h3>Big feature</h3>
  </BentoCard>
  <BentoCard><p>Small</p></BentoCard>
  <BentoCard><p>Small</p></BentoCard>
  <BentoCard colSpan={2}><p>Wide</p></BentoCard>
  <BentoCard rowSpan={2}><p>Tall</p></BentoCard>
  <BentoCard><p>Small</p></BentoCard>
  <BentoCard><p>Small</p></BentoCard>
</BentoGrid>
```

## Props

### `<BentoGrid>`
| Prop | Type | Default | Notes |
|---|---|---|---|
| `columns` | number | `4` | Equal fractional columns. |
| `gap` | number | `16` | px between cards. |
| `rowHeight` | number \| string | `180` | px (number) or any CSS (`"minmax(180px, auto)"`). |

### `<BentoCard>`
| Prop | Type | Default | Notes |
|---|---|---|---|
| `colSpan` | 1-4 | `1` | How many columns this card spans. |
| `rowSpan` | 1-3 | `1` | How many rows this card spans. |
| `tilt` | number | `6` | Max tilt angle in deg. `0` disables. |
| `lift` | number | `6` | px lifted on hover. |

## Implementation notes

- **`gridAutoRows`** — fixed row height by default. If you set `rowHeight="minmax(180px, auto)"` you get content-fit rows, but `rowSpan` stops visually spanning (both rows must exist first).
- **3D tilt.** Compute cursor position relative to card, normalize to `-0.5..0.5`, multiply by `tilt` for rotation. Negate Y because rotating +X tilts the top away.
- **`transformStyle: preserve-3d` + `perspective()` on the same element.** Perspective on the element (not the parent) keeps tilts independent per card — each card has its own vanishing point, which looks punchier than a single shared perspective.
- **`translateY(-lift)`** composed into the same transform so spring back on leave is a single transition.
- **Glass vibe by default.** `rgba(255,255,255,0.04)` + 1px soft border + `backdrop-filter: blur(12px)`. Override via `style` or `className`.

## Responsive

The grid as given does NOT collapse on mobile — four columns will overflow. Wrap with media queries in your app:

```css
@media (max-width: 900px) { .bento { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .bento { grid-template-columns: 1fr; } }
```

Or use `clamp`-based column counts if you want automatic reflow.

## Attribution

Bento layouts are industry-standard (Apple since iPadOS 17 Home Screen). Tilt effect is the standard "vanilla-tilt" math pattern. No Framer code reused.
