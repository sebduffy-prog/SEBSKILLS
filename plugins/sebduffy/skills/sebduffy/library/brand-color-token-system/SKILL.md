---
name: brand-color-token-system
category: frontend-and-design
description: >
  Turn ONE brand hex into a complete 50->950 tonal ramp with a semantic token layer and
  light/dark parity, exported as CSS custom properties, a Tailwind color object, or Style
  Dictionary tokens. Uses OKLab (hold hue, sweep lightness, gamut-clip chroma) so every stop
  is perceptually even — no muddy mid-tones, no washed-out extremes. Reach for this on
  "generate a color scale from my brand color", "make a 50-950 palette", "build design
  tokens", "Radix/Tailwind-style tonal system", or "light and dark mode from one accent".
when_to_use:
  - "You have one brand/accent hex and need a full 50->950 tonal ramp built from it"
  - "You need a semantic layer (bg, surface, border, text, primary...) that maps onto the ramp"
  - "You want light AND dark mode tokens generated together with correct step inversion"
  - "You need the same palette exported to CSS variables, Tailwind, and Style Dictionary at once"
  - "An existing ramp looks uneven/muddy and you want a perceptually-uniform OKLab rebuild"
when_not_to_use:
  - "You just need raw OKLCH<->hex conversion math or gamut mapping helpers -> oklch-color-engine"
  - "You need to verify WCAG contrast ratios of a chosen pair -> accessible-contrast-checker"
  - "You want a multi-hue harmony (complementary/triadic) from a seed -> color-harmony-generator"
  - "You need colorblind-safe categorical series for charts -> colorblind-safe-palettes"
  - "You want to apply a ready-made preset theme to an artifact -> theme-factory"
keywords: [tonal palette, color scale, 50-950, design tokens, semantic tokens, css custom properties, tailwind colors, style dictionary, oklab, oklch, radix colors, material hct, light dark mode, gamut clip, brand color, perceptually uniform]
similar_to: [oklch-color-engine, accessible-contrast-checker, color-harmony-generator, colorblind-safe-palettes, theme-factory]
inputs_needed:
  - "One brand/accent color as hex (#RGB or #RRGGBB)"
  - "A token namespace/name (default: brand)"
  - "Target export format: CSS vars, Tailwind object, or Style Dictionary JSON"
  - "Whether you need the semantic layer + dark mode (--semantic) or just the raw ramp"
produces: An 11-stop 50->950 tonal ramp (hex + oklch) plus a light/dark semantic token layer, exported as CSS custom properties, a Tailwind color object, or Style Dictionary tokens
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Brand Color Token System

One brand hex in, a full production token set out: an 11-stop tonal ramp
(`50 100 200 300 400 500 600 700 800 900 950`), a semantic layer mapped onto it,
and light/dark parity — in CSS, Tailwind, or Style Dictionary format.

## When to use

Use this the moment a project has a brand color but no *system*. A single hex can't
theme a UI — you need light backgrounds, hover states, borders, muted text, and a solid
accent, all derived so they belong to the same family. This skill generates that family
perceptually (in OKLab), so step 300 isn't randomly more saturated than step 700 and the
near-white/near-black ends don't turn grey or clip out of the sRGB gamut.

## How it works (grounded)

Three ideas, borrowed from the best existing systems:

- **Tailwind-style stops** — the `50->950` numeric ramp is the de-facto token contract
  (`brand-500` is your base). Predictable, tooling-friendly.
- **Radix-style semantic layer** — Radix's 12-step scale assigns each step a *job*
  (1-2 app/subtle bg, 3-5 component bg + hover/active, 6-8 borders, 9-10 solid, 11-12 text).
  We fold that intent into named semantic tokens (`bg`, `surface`, `border`, `text`,
  `primary`...) that point at ramp steps, so consuming code never hard-codes a step number.
- **Perceptual generation (OKLab / HCT spirit)** — like Material's HCT and Leonardo, we work
  in a perceptual space: hold **hue** constant, sweep **lightness** on an even staircase, and
  scale **chroma** down toward the extremes, then gamut-clip chroma by binary search so every
  stop is a real, in-gamut sRGB color. This is what stops the muddy mid-tones you get from
  naive HSL `lighten()/darken()`.

The math (sRGB->linear->OKLab->OKLCH and back, Björn Ottosson's matrices) lives in
`scripts/tonal.py` — pure stdlib, python3.9+, no pip installs.

## Recipes

### 1. Generate the ramp (inspect first)

```bash
python3 scripts/tonal.py "#2F6BFF" --name brand --semantic
```

```
brand-50   #f1f6ff  oklch(0.9720 0.0132 263.86)
brand-500  #4880ff  oklch(0.6300 0.1983 263.86)   <- base
brand-950  #010f4d  oklch(0.2160 0.1145 263.86)
...
semantic (light / dark):
  bg             #f1f6ff / #010f4d
  primary        #2861f1 / #4880ff
  text           #031d6e / #e0eaff
```

Sanity-check the ramp reads as one hue and steps feel even before wiring it in.

### 2. CSS custom properties + dark mode (the usual target)

```bash
python3 scripts/tonal.py "#2F6BFF" --name brand --css --semantic > tokens.css
```

Emits `:root { --brand-50 ... --brand-950; --brand-bg ... }` plus a
`@media (prefers-color-scheme: dark)` block that re-points **only the semantic tokens**
(the raw ramp stays fixed; dark mode flips which step each role uses). Consume semantics,
not raw steps:

```css
.card   { background: var(--brand-surface); border: 1px solid var(--brand-border);
          color: var(--brand-text); }
.button { background: var(--brand-primary); color: var(--brand-on-primary); }
.button:hover { background: var(--brand-primary-hover); }
```

For a manual class toggle instead of the OS query, duplicate the dark block under
`:root[data-theme="dark"] { ... }`.

### 3. Tailwind color object

```bash
python3 scripts/tonal.py "#2F6BFF" --name brand --tw
```

Paste under `theme.extend.colors` (v3) or map into `@theme` `--color-brand-500` (v4).
Then `bg-brand-500 text-brand-50 border-brand-200` just work.

### 4. Style Dictionary tokens (multi-platform)

```bash
python3 scripts/tonal.py "#2F6BFF" --name brand --sd --semantic > tokens.json
```

Produces `{ color: { brand: { "500": {value,type}, semantic: {…light/dark…} } } }` —
feed straight into a Style Dictionary build to fan out iOS/Android/web.

### 5. Multiple brand colors

Run once per hex with a distinct `--name` (e.g. `--name accent`, `--name success`,
`--name danger`) and concatenate the CSS. Each gets its own ramp + semantics under its
namespace. Neutral/grey ramp: feed a low-chroma hex like `#5B6470`.

## Semantic step map

| Token            | Light step | Dark step | Radix-ish job         |
|------------------|-----------|-----------|-----------------------|
| `bg`             | 50        | 950       | app background        |
| `surface`        | 100       | 900       | card / panel          |
| `surface-hover`  | 200       | 800       | hovered panel         |
| `border`         | 200       | 800       | subtle separator      |
| `border-strong`  | 300       | 700       | focus ring / emphasis |
| `text-muted`     | 600       | 400       | secondary text        |
| `text`           | 900       | 100       | primary text          |
| `primary`        | 600       | 500       | solid accent          |
| `primary-hover`  | 700       | 400       | hovered accent        |
| `on-primary`     | 50        | 950       | text on the accent    |

Edit the `SEMANTIC` dict in `scripts/tonal.py` to retune the mapping to your house style.

## Verify

- **In gamut:** every emitted hex is a real sRGB color — the generator binary-searches the
  max in-gamut chroma per stop, so `oklch()` values never clip. Spot-check by pasting a
  couple into a browser devtools color picker.
- **Even staircase:** the printed `oklch(...)` lightness values step down smoothly
  (`0.972 -> 0.216`); no two adjacent stops should collide.
- **Base fidelity:** `brand-500` should sit visually adjacent to your input; hue is held
  constant across the whole ramp (same third `oklch` number).
- **Contrast (do this before shipping):** the `text`/`bg` and `on-primary`/`primary` pairs
  must clear WCAG AA (4.5:1 for body). This skill does NOT check contrast — run the pair
  through **accessible-contrast-checker** and nudge the semantic step map if a pair is short.

## Pitfalls

- **Don't consume raw ramp steps in components.** Point at semantic tokens; that's what makes
  dark mode a one-line flip instead of a find-and-replace.
- **Very light or very dark brand inputs** (e.g. a pale pastel or near-black) still produce a
  full ramp because lightness is *targeted*, not offset — but `brand-500` may look different
  from your input if the input was itself very light/dark. That's correct: 500 is the mid of
  the *system*, not necessarily your literal brand swatch. Keep your exact brand hex as a
  separate `--brand-base` if legal/marketing requires the precise value.
- **Neutrals need low chroma, not zero.** A pure-grey ramp (`#808080`) works, but a hint of
  the brand hue (`#5B6470`) gives warmer/cooler UI greys that read as intentional.
- **OS dark-mode only, by default.** The `@media` block follows the OS. Add the
  `:root[data-theme="dark"]` duplicate if your app has a manual toggle (see theme-toggle).
- **Chroma taper is a taste knob.** If mid-tones feel too punchy or too flat, adjust
  `C_SCALE`/`L_TARGETS` at the top of `tonal.py` — they're deliberately exposed constants.
