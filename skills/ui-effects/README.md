# UI Effects

**Drop-in React / Next.js / WebGL components for showstopper interactive effects.**

Each skill produces a single `.tsx` file (plus minimal dependencies) you can copy into any React/Next.js project. These are re-implementations of premium Framer modules as standalone code — no Framer runtime required.

Most require `"use client"` for Next.js app router.

## Index

### Shader / WebGL effects (original set)

| Skill | Effect | Tech | Key props |
|---|---|---|---|
| [`image-shatter`](image-shatter) | Image shatters into a grid on hover, spring-animated tiles with cursor magnet | `framer-motion` | `tilesX`, `tilesY`, `maxOffset`, `magnetStrength` |
| [`interactive-distortion`](interactive-distortion) | WebGL2 pixel displacement that follows the mouse over an image or video | WebGL2 (raw) | `strength`, `falloff`, `resolution` |
| [`liquid-image`](liquid-image) | Water-ripple hover with grayscale→color reveal mask | WebGL | `rippleStrength`, `revealRadius` |
| [`liquid-glass-button`](liquid-glass-button) | Apple-style frosted glass button with shine/highlight | Pure CSS (no JS) | CSS variables |
| [`rubiks-image-cube`](rubiks-image-cube) | 3D rotatable cube displaying image segments or colour tiles | CSS 3D + `framer-motion` | `images`, `shuffleOnMount` |
| [`spectra-noise`](spectra-noise) | Animated shader background — hue shift, scanlines, warp, noise | WebGL shader | `speed`, `hueShift`, `warp` |

### Framer-marketplace-inspired components (one per category)

| Skill | Framer category | Effect | Tech |
|---|---|---|---|
| [`aurora-gradient`](aurora-gradient) | Backgrounds | Drifting blurred multi-color blobs behind any content | Pure CSS keyframes + blend modes |
| [`magnetic-button`](magnetic-button) | Buttons | Button attracts toward the cursor inside a radius, spring snap-back | rAF spring loop |
| [`infinite-marquee`](infinite-marquee) | Carousels | Seamless looping horizontal strip (logos/testimonials), pauses on hover | Duplicated-track CSS animation |
| [`animated-counter`](animated-counter) | Data | Number counts up on viewport entry, locale-formatted, easing-curved | IntersectionObserver + rAF |
| [`floating-label-input`](floating-label-input) | Forms | Material/Stripe-style input with floating label + focus ring + error state | Controlled/uncontrolled React |
| [`magnetic-cursor`](magnetic-cursor) | Interactions | Global custom cursor with spring lag, grows on interactive elements, blend-mode invert | rAF + mix-blend-mode |
| [`bento-grid`](bento-grid) | Layout | Variable-span bento card grid with 3D hover tilt + lift | CSS grid + transform |
| [`scroll-reveal-section`](scroll-reveal-section) | Sections | Staggered fade/slide-in for children as the section enters the viewport | IntersectionObserver + CSS transitions |
| [`text-scramble`](text-scramble) | Typography | Headline/label scrambles random glyphs then decrypts to final string | setTimeout loop |
| [`theme-toggle`](theme-toggle) | Utilities | Sun↔moon morphing dark-mode toggle, persists to localStorage | Pure SVG + CSS |

## When to use each

| Goal | Pick |
|---|---|
| Hero image needs "wow" on hover | `image-shatter` or `liquid-image` |
| Image should feel alive/melty under the cursor | `interactive-distortion` |
| A premium-feeling back/close button | `liquid-glass-button` |
| Playful portfolio/photo showcase | `rubiks-image-cube` |
| Full-screen animated background | `spectra-noise` or `aurora-gradient` |
| Hero CTA with physicality | `magnetic-button` (+ optional `magnetic-cursor`) |
| Logo / press strip | `infinite-marquee` |
| Stat section ("10,000+ users") | `animated-counter` inside `scroll-reveal-section` |
| Production form field | `floating-label-input` |
| Feature mosaic à la Apple.com | `bento-grid` |
| Any section needs to animate in on scroll | `scroll-reveal-section` |
| Dramatic headline reveal | `text-scramble` |
| Dark-mode switch in the nav | `theme-toggle` |

## Combining

- `spectra-noise` (bg) + `liquid-glass-button` (foreground CTAs) = Apple/vision-OS feel
- `aurora-gradient` (bg) + `magnetic-button` (CTA) + `magnetic-cursor` (global) = high-polish marketing landing
- `frontend-design` (layout) + `image-shatter` (hero) = portfolio site
- `scroll-reveal-section` wrapping `animated-counter`s = premium stats block
- `bento-grid` (feature showcase) + `text-scramble` (card titles) = Apple-style feature section
- `infinite-marquee` (press logos) below a hero = canonical SaaS landing
- `interactive-distortion` + `liquid-glass-button` + `theme-factory` + `theme-toggle` = premium product landing

## Performance notes

- Shader-based skills (`interactive-distortion`, `liquid-image`, `spectra-noise`) respect `prefers-reduced-motion`
- `image-shatter` caps at ~112 tiles (14×8) by default and downscales on mobile
- `rubiks-image-cube` is CSS-3D, not WebGL — cheap
- `liquid-glass-button` is pure CSS — cheapest

## Attribution

Re-implementations of Framer modules. Each `SKILL.md` credits the original Framer component and the technique (framer-motion patterns, WebGL2 displacement, CPPN noise, etc.).

The "Framer-marketplace-inspired" set (aurora-gradient, magnetic-button, infinite-marquee, animated-counter, floating-label-input, magnetic-cursor, bento-grid, scroll-reveal-section, text-scramble, theme-toggle) is one representative skill per free marketplace category. They are **not** 1:1 copies of any specific marketplace component — they're clean-room re-implementations of the category's prevailing pattern, built from standard web APIs (CSS transitions, IntersectionObserver, requestAnimationFrame, SVG). No Framer runtime or proprietary code is reused.
