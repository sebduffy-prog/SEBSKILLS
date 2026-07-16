---
name: accessible-contrast-checker
category: frontend-and-design
description: >-
  Check AND auto-fix colour contrast before you ship a palette. Computes WCAG 2.x
  ratios (4.5:1 / 3:1 / 7:1) plus modern APCA Lc, then nudges a failing colour to
  the nearest passing value along its lightness axis instead of guessing. Use when
  a design's text/background pair might be unreadable, when a brand colour fails
  AA, when a reviewer flags contrast, or when wiring CSS contrast-color() theming.
  Pure-stdlib Python — no npm, runs on macOS system python3. Verify every pair.
when_to_use:
  - A text/background or UI colour pair may fail WCAG AA/AAA and you need the exact ratio
  - A brand or accent colour fails contrast and you want the minimal nudge that passes
  - You want APCA Lc (the WCAG 3 direction) alongside the legacy 2.x ratio
  - Auditing a whole palette/token set for readable foreground-background combinations
  - Deciding auto foreground colour via CSS contrast-color() and validating the fallback
when_not_to_use:
  - Generating a fresh palette from scratch — use color-harmony-generator or oklch-color-engine
  - Simulating colour-blindness safety of a palette — use colorblind-safe-palettes
  - Managing design tokens across themes — use brand-color-token-system
  - Converting/interpolating in perceptual space — use oklch-color-engine
keywords:
  - contrast
  - wcag
  - apca
  - accessibility
  - a11y
  - color-contrast
  - contrast-ratio
  - contrast-color
  - readability
  - luminance
  - aa
  - aaa
  - lc
  - auto-fix
  - palette-audit
similar_to:
  - oklch-color-engine
  - brand-color-token-system
  - colorblind-safe-palettes
  - color-harmony-generator
  - perceptual-gradient-designer
inputs_needed: A foreground colour and a background colour (hex #rgb/#rrggbb), optionally target level (AA/AAA) and text size (normal/large).
produces: Pass/fail verdict with WCAG ratio and APCA Lc; for fixes, the nearest passing hex plus before/after ratios.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Accessible Contrast Checker

Two contrast models, one tool. **WCAG 2.x** gives the ratio auditors and legal
standards require (AA = 4.5:1 body / 3:1 large; AAA = 7:1 / 4.5:1). **APCA**
(Accessible Perceptual Contrast Algorithm, the WCAG 3 research direction) gives a
perceptually-tuned Lc score that models real readability far better for thin/light
type and dark mode. Report both; **auto-fix** turns a failing pair into a passing
one by moving the smallest amount along the lightness axis.

## When to use

Reach for this the moment a colour decision has a *reader* on the other end: body
text, buttons, badges, chart labels, disabled states, placeholder text. Do NOT
eyeball it — a `#777` on white looks fine and fails AA (4.48:1). Run the check.

## Prerequisites

- macOS system `python3` (3.9+) — the helper is pure stdlib, no pip, no npm.
- Colours as hex: `#rgb`, `#rrggbb`, or bare `rrggbb`.
- Know your target: body text → AA 4.5:1; large text (>=24px, or >=18.66px bold)
  → AA 3:1; strict → AAA. UI components/graphics have a separate 3:1 floor (WCAG
  1.4.11) — treat icons/borders as `--size large`.

## Recipes

### 1. Check one pair (WCAG + APCA)

```bash
S=skills/frontend-and-design/accessible-contrast-checker/scripts/contrast.py
python3 "$S" check "#1a1a2e" "#ffffff"            # body text, AA
python3 "$S" check "#767676" "#fff" --level AAA --size large
python3 "$S" apca  "#595959" "#ffffff"            # APCA Lc only
```

`check` exits non-zero on fail, so it drops straight into CI/pre-commit:

```bash
python3 "$S" check "$FG" "$BG" || { echo "contrast fail"; exit 1; }
```

### 2. Auto-fix a failing colour to the nearest pass

Nudges ONE colour (default the foreground) toward black or white — whichever
raises contrast with the *least* change — via binary search, then reports the
minimal passing hex. Hue/chroma are preserved as far as the lightness move allows.

```bash
python3 "$S" fix "#2277d3" "#ffffff" --level AA           # fix the text colour
python3 "$S" fix "#e8e8e8" "#ffffff" --fix bg --level AA  # fix the background instead
```

Output: `fg: #2277d3 -> #1e6abd   3.98:1 -> 4.51:1  (>= 4.5:1)`. If the pair
already passes it says so; if even pure black/white can't reach the target (rare,
only for near-mid backgrounds at AAA) it reports no change so you know to rethink
the pairing rather than trust a false pass.

### 3. APCA reading (Lc thresholds)

APCA returns signed Lc; use `abs()`. Practical minimums from the APCA/Bronze docs:

| Use case                          | min \|Lc\| |
|-----------------------------------|-----------|
| Body text (fluent reading)        | 75        |
| Large / 24px+ or 16px+ bold       | 60        |
| Non-text UI, large headings       | 45        |
| Disabled / decorative only        | 30        |

`Lc 60` ~ roughly WCAG 4.5:1; the two disagree most on dark backgrounds, where
APCA is the more honest number.

### 4. CSS contrast-color() theming (Baseline 2026)

`contrast-color()` auto-picks black or white against a variable background — no
hand-maintained pairs:

```css
.btn {
  background: var(--btn);
  color: contrast-color(var(--btn));   /* white or black, best contrast */
}
```

It only ever returns black/white and only targets WCAG AA, so it FAILS on mid-tones
(royal blue `#2277d3` gets black text → unreadable). Rule: use it for clearly
light or clearly dark backgrounds, and validate the two outcomes here before trusting it:

```bash
python3 "$S" check "#ffffff" "$BTN"   # would white text pass?
python3 "$S" check "#000000" "$BTN"   # would black text pass?
```

Provide a fallback for pre-2026 engines:

```css
.btn { color: #fff; color: contrast-color(var(--btn)); }
@supports not (color: contrast-color(white)) { /* ship your validated pairs */ }
```

### 5. Audit a whole palette in JS (Color.js, the same math)

If you already load [Color.js](https://colorjs.io) in the browser/build, mirror
these calls — the algorithm names match this tool:

```js
import Color from "colorjs.io";
const bg = new Color("#ffffff"), text = new Color("#767676");
bg.contrast(text, "WCAG21");           // -> 4.54  (ratio)
bg.contrastAPCA(text);                 // -> Lc; call bg.contrast(text,...) as background.contrast(text)
```

Order matters for APCA: call it as **background**.contrastAPCA(**text**); swapping
gives a wrong sign/magnitude.

## Verify

```bash
S=skills/frontend-and-design/accessible-contrast-checker/scripts/contrast.py
python3 "$S" check 000000 ffffff   # -> 21.00:1 PASS,  APCA Lc +106.0
python3 "$S" apca  595959 ffffff   # -> Lc +84.3  (known-good anchor)
python3 "$S" check 777777 ffffff   # -> 4.48:1 FAIL (proves it catches the classic near-miss)
python3 "$S" fix   2277d3 ffffff   # -> darkens fg to a passing hex
```

The black/white pair must read 21.00:1 / Lc +106; that is the fixed calibration
point for both algorithms.

## Pitfalls

- **21:1 is the ceiling.** Any tool reporting >21 or <1 has a luminance bug.
- **Large-text discount is a trap.** 3:1 only applies at >=24px or >=18.66px bold.
  Don't apply it to 16px body just to pass.
- **APCA argument order.** It is polarity-aware: pass (text, background). The sign
  encodes light-on-dark vs dark-on-light; compare with `abs()`.
- **contrast-color() only meets AA and only outputs black/white** — never assume it
  makes a mid-tone readable; validate both outcomes (recipe 4).
- **Fixing the wrong colour.** On a fixed brand background, `--fix fg`; on fixed
  body text, `--fix bg`. Nudging the locked colour just produces an off-brand result.
- **Semi-transparent / gradient backgrounds.** These formulas assume opaque solids.
  Flatten `rgba()` over its actual backdrop first, and for text on a gradient/image
  test the *worst-case* spot (lightest patch under light text).
- **Anti-aliased thin fonts read lighter** than their hex implies — for hairline
  weights, prefer the APCA Lc 75 bar over a bare 4.5:1 pass.
