---
name: liquid-glass-button
description: Build an Apple-style liquid glass back button (or generic glass button) in React/Next.js using pure CSS — no WebGL, no canvas. Use this skill whenever the user asks for a "glass button", "liquid glass button", "Apple-style button", "frosted glass button", "back button", "glassmorphism button", "iOS 18 glass button", or describes wanting a blurred semi-transparent button with shine/highlight effects. Also use when the user references the Framer GlassBackButton component, or says things like "button that looks like it's made of glass", "translucent button with a glow", "button with backdrop blur and light reflection". Trigger even if the user just wants "a nice button for my hero" and the project aesthetic suggests Apple / premium / glassy.
---

# Liquid Glass Back Button

Generates a single-file React component rendering an Apple-inspired liquid glass button. The effect uses **pure CSS** — `backdrop-filter: blur()`, stacked linear gradients for directional light, layered box-shadows for inner/outer shadow, and a `::before`-equivalent overlay div for the gradient border. No WebGL, no canvas, no animation library.

## What the effect looks like

A translucent rounded-pill button with a realistic glass surface: blurred content visible behind it, a directional highlight (simulating light hitting the top-left), a subtle inner shadow for depth, and a soft outer drop shadow. On hover it lifts 2px, brightens, and the blur intensifies. On press it scales down to 0.96. Directionally lit — you control the light angle (0-360°) and it adjusts gradients + shadows accordingly.

The original is specifically a "back" button (chevron-left icon + "Back" label) but the skill produces a **reusable glass button** that can show any icon, any label, or be icon-only.

## When to use

- User wants a premium Apple-style button (hero CTA, navigation, toolbar)
- User references "glassmorphism", "liquid glass", "iOS 18", "frosted glass"
- User is building an app, dashboard, or site with a dark/photo background where a glass button would shine
- User specifically asks for a back button

## What to produce

A single `.tsx` (or `.jsx`) file called `LiquidGlassButton.tsx`. Zero dependencies beyond React. Use the code from `assets/LiquidGlassButton.tsx`.

### Usage

```tsx
import LiquidGlassButton from "@/components/LiquidGlassButton";

// Back button (default)
<LiquidGlassButton onClick={() => history.back()} />

// Custom label + icon
<LiquidGlassButton label="Continue" icon="chevron-right" onClick={handleNext} />

// Icon only
<LiquidGlassButton label="Close" showText={false} icon="x" />

// Custom tuning
<LiquidGlassButton
  label="Back"
  lightDirection={225}       // 0-360° — direction of virtual light source
  blurAmount={10}
  glassOpacity={0.25}
  highlightIntensity={0.15}
  borderRadius={21}
  paddingTop={14}
  paddingRight={21}
  paddingBottom={14}
  paddingLeft={21}
/>
```

Renders **best against a busy/colourful/photo background** — the blur has to have something to blur. On a flat grey wall it will look like a faint bubble.

## Implementation notes

1. **`backdrop-filter: blur()` support.** Works in all modern browsers (Safari 15+, Chrome 76+, Firefox 103+). Include `-webkit-backdrop-filter` for older iOS. The asset has both.

2. **Stacked linear gradients, not radial.** The Framer original deliberately avoids radial gradients because they don't respect non-circular shapes well. Four layered linear gradients at different angles create the directional highlight. Keep this pattern — don't simplify to one gradient.

3. **Gradient border via overlay div.** Since pure CSS can't combine `background` (for the glass fill) with a gradient border, the asset uses a positioned `<div>` with `mask-composite: exclude` (xor) to paint only the border ring. This is the cleanest pure-CSS way to do gradient borders.

4. **Colour string manipulation.** The Framer source uses `.replace(/[\d\.]+\)$/g, ...)` to swap alpha channels in `rgba()` strings at runtime. The asset preserves this because it's how `highlightIntensity`, `glassOpacity`, etc. work dynamically. If the user passes a hex colour, it won't work — the asset normalises hex → rgba up front.

5. **Transform composition.** `scale()` + `translateY()` + `translateZ(0)` — the `translateZ(0)` forces GPU compositing so the hover lift is smooth. Don't remove it.

6. **Minimum hit target.** Fixed at `44×44px` to meet Apple HIG / WCAG touch target guidelines. Don't let the padding/content make it smaller.

7. **`onClick` handling.** The original Framer component hardcodes `window.history.back()`. The asset makes `onClick` a prop with that as the default, so it works as both a drop-in back button and a generic CTA.

## Next.js specifics

Add `"use client"` at the top — the button uses `useState` for hover/press and needs client-side hydration.

If you're using Tailwind, the component sets inline styles (not utility classes) because the effect requires precise gradient math. Don't try to refactor into Tailwind classes — you'll lose the dynamic highlight-intensity/light-direction behaviour.

## Props reference

| Prop | Type | Default | Description |
|---|---|---|---|
| `label` | string | `"Back"` | Button text |
| `showText` | boolean | `true` | If false, icon-only (44×44 min) |
| `icon` | `"chevron-left" \| "chevron-right" \| "x" \| "check" \| null` | `"chevron-left"` | Built-in icons |
| `onClick` | `() => void` | `window.history.back()` | Click handler |
| `iconSize` | number | 28 | px |
| `iconWeight` | number | 2 | Stroke width of the SVG icon |
| `textSize` | number | 28 | px |
| `textWeight` | number | 500 | Font weight (100-900) |
| `textColor` | string | `"rgba(255, 255, 255, 0.85)"` | rgba string |
| `glassBackground` | string | `"rgba(199, 199, 199, 0.45)"` | rgba |
| `glassBorderColor` | string | `"rgba(255, 255, 255, 0.3)"` | rgba |
| `highlightColor` | string | `"rgba(163, 163, 163, 0.6)"` | rgba |
| `outerShadowColor` | string | `"rgba(41, 41, 41, 0.1)"` | rgba |
| `innerShadowColor` | string | `"rgba(255, 255, 255, 0.05)"` | rgba |
| `hoverTint` | string | `"rgba(209, 209, 209, 0.15)"` | rgba |
| `padding*` | number | 14/21/14/21 | px |
| `gap` | number | 2 | Icon-text gap, px |
| `borderRadius` | number | 21 | px |
| `blurAmount` | number | 10 | Backdrop blur, px |
| `glassOpacity` | number | 0.25 | 0.1-0.9 |
| `glassTransparency` | number | 0.5 | 0.3-1.5 (multiplier on opacity) |
| `highlightIntensity` | number | 0.15 | 0-1 |
| `lightDirection` | number | 225 | degrees, 0-360 |
| `outerShadowIntensity` | number | 0.2 | 0-0.5 |
| `outerShadowBlur` | number | 5 | px |
| `outerShadowSpread` | number | -2 | px |
| `innerShadowIntensity` | number | 0.14 | 0-0.2 |
| `innerShadowBlur` | number | 3 | px |
| `innerShadowSpread` | number | -1 | px |
| `noiseOpacity` | number | 0.06 | 0-0.1 |

**All colour props must be `rgba()` strings** — the runtime alpha-channel swapping uses regex and needs the string form. Passing hex (`#fff`) will break the gradients.

## Common requests

- **"Make it look more like iOS 18"** — bump `blurAmount` to 20, `glassOpacity` to 0.35, `highlightIntensity` to 0.25, and use `rgba(255,255,255,0.15)` for `glassBackground`. iOS 18's "liquid glass" is more transparent + bluer than the Apple WWDC default.
- **"Add a subtle gradient border that animates on hover"** — modify the `borderOverlayStyle` gradient to include a hue-rotating animation via CSS `@keyframes`.
- **"Dark variant"** — set `textColor` to `rgba(0,0,0,0.8)`, swap highlight/innerShadow to darker values, and the glass becomes a light-on-dark pill suitable for light backgrounds.
- **"Use Lucide icons instead of the built-ins"** — pass a React node via a `children` or `customIcon` prop. Small asset modification.

## Attribution

Original from the Framer "GlassBackButton" module. The CSS technique (backdrop-filter + stacked gradients + mask-composite border) is standard web tech and fully re-implementable from scratch. This skill is for personal/experimental use; the re-implemented version is clean of any Framer-specific code.
