---
name: animated-counter
description: Number that counts up (or down) to a target value when it scrolls into view. Eased, locale-formatted, supports decimals, prefix ("$"), suffix ("%"/"+"). Use when the user asks for an "animated counter", "counting number", "stat number", "count-up", "metric card animation", "KPI ticker", "funded-amount style counter", or wants stats blocks that animate on scroll. Framer category — Data.
---

# Animated Counter

A `<span>` that starts at `from`, counts up to `to` with an easing curve over `duration` ms when the element enters the viewport. One IntersectionObserver + one `requestAnimationFrame` loop. No deps.

## When to use

- Stats sections ("10,000+ customers", "$2.3M funded", "99.9% uptime")
- KPI dashboards
- Anywhere you want numbers to feel earned, not printed

## What to produce

`assets/AnimatedCounter.tsx`.

```tsx
import AnimatedCounter from "@/components/AnimatedCounter";

<AnimatedCounter to={12500} suffix="+" />
<AnimatedCounter to={99.9} decimals={1} suffix="%" />
<AnimatedCounter to={2300000} prefix="$" locale="en-US" />
```

## Props

| Prop | Type | Default | Notes |
|---|---|---|---|
| `to` | number | — | Target value. |
| `from` | number | `0` | Starting value. |
| `duration` | number | `1800` | ms. |
| `decimals` | number | `0` | Fraction digits shown. |
| `prefix` / `suffix` | string | `""` | Text around the number. |
| `locale` | string | browser default | Passed to `Intl.NumberFormat`. |
| `easing` | `(t:number) => number` | ease-out-expo | Takes 0–1, returns 0–1. Swap for cubic/quart if you want. |
| `once` | boolean | `true` | Re-animates on re-entry if `false`. |

## Implementation notes

- **IntersectionObserver, threshold 0.3.** Counter starts when ~30% of it is in view. Feels natural — not right on enter, not so late it finishes off-screen.
- **`Intl.NumberFormat`** handles thousands separators and decimal digits in whatever locale the user prefers. Free i18n.
- **ease-out-expo** default — feels like a snappy decelerating slam. Matches the Framer marketplace vibe better than linear or quadratic.
- **Once only by default.** Set `once={false}` and animation replays every time the element re-enters the viewport.

## Common tweaks

- **Roman / currency formatting:** swap the `Intl.NumberFormat` options (`style: "currency", currency: "USD"`) and drop `prefix`.
- **Sync with enter motion:** pair with `scroll-reveal-section` — the whole card slides in, and the number counts up inside it.
- **Slower for dramatic KPIs:** bump `duration` to 3000–3500 for that "big important number" feel.

## Attribution

Common pattern across Framer marketplace "count up" / "stat counter" components. Implementation is idiomatic React + browser APIs.
