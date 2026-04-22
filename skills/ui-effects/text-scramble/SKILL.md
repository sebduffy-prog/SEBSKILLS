---
name: text-scramble
description: Text that scrambles random glyphs and then "decrypts" into its final string when triggered (viewport/hover/mount). Use when the user asks for a "text scramble", "glitch text", "decrypt text", "matrix text reveal", "scramble animation", "hacker text effect", "encoded text reveal", or wants headlines/numbers/labels that animate in with a glitch-to-readable flourish. Framer category — Typography.
---

# Text Scramble

A `<TextScramble>` span (or any tag via `as`) that reveals its text via a scramble. Each character has a random start frame and a random end frame; while active, it cycles through random glyphs from `chars`; when done, it locks to the target character.

## When to use

- Hero headlines on tech/agency sites
- Stat numbers for emphasis ("reveal on scroll")
- Hover "decrypt" interactions on links
- Section titles that need more punch than fade-in

## What to produce

`assets/TextScramble.tsx`.

```tsx
import TextScramble from "@/components/TextScramble";

// Animates in on scroll:
<TextScramble text="Ship faster." as="h1" />

// Decrypts on hover:
<a href="/work">
  <TextScramble text="View work" trigger="hover" />
</a>

// Fires immediately on mount, slower:
<TextScramble text="LOADING" trigger="mount" speed={50} revealDelay={60} />
```

## Props

| Prop | Type | Default | Notes |
|---|---|---|---|
| `text` | string | — | The target string. |
| `chars` | string | symbols + digits-ish | Pool of random glyphs. Customise for vibe (e.g., Katakana for Matrix). |
| `speed` | number | `30` | ms per frame. Lower = faster scramble cycling. |
| `revealDelay` | number | `35` | Per-character duration of the scramble before lock. |
| `trigger` | `"viewport" \| "hover" \| "mount"` | `"viewport"` | What starts the animation. |
| `threshold` | number | `0.4` | IntersectionObserver threshold when `trigger="viewport"`. |
| `once` | boolean | `true` | Viewport trigger replays if `false`. |
| `as` | tag | `"span"` | Render as `h1`, `p`, `a`, etc. |

## Implementation notes

- **Queue-of-characters model.** Each character gets `start`/`end` frame offsets computed once. In the main loop we check each char against the current frame and decide: still-hidden, scrambling (roll a new glyph ~28% of frames so it flickers but isn't unreadable chaos), or locked.
- **`setTimeout(tick, speed)`** — intentionally not `requestAnimationFrame` because we want a consistent visible flicker cadence, not frame-rate-coupled.
- **Completion guard.** `runningRef` prevents double-start if the observer fires rapidly during fast scrolling.
- **Hover mode has no IntersectionObserver** — trigger is attached via `onMouseEnter`.

## Common tweaks

- **Matrix look:** `chars="ｱｲｳｴｵｶｷｸｹｺ01"` (half-width katakana).
- **Terminal feel:** `chars="01"`, `speed={20}`.
- **Long copy:** increase `revealDelay` to 60–80, else long strings decrypt too uniformly.
- **Spoiler-safe text (SEO/a11y):** the initial render IS the final `text`, then state replaces it. Screen readers read the final string; crawlers see it. Good.

## Caveats

- Layout width jumps if your font isn't monospaced — the random glyphs' widths differ from the final text. For headlines, either use a monospaced display face (JetBrains Mono, Berkeley Mono), or apply `font-variant-numeric: tabular-nums; font-feature-settings: "tnum"` and keep scramble chars to same-width glyphs.

## Attribution

Scramble reveal is a canonical web-motion pattern (often credited to Justin Windle's original). Implementation is from-scratch, no Framer code reused.
