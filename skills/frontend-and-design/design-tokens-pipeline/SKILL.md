---
name: design-tokens-pipeline
category: frontend-and-design
description: >-
  Build a full W3C DTCG design-token pipeline with Style Dictionary v5 — spacing, radius,
  shadow, typography, motion/duration, and color — compiled to CSS variables, SCSS, JS/TS,
  iOS and Android from one source of truth. Reach for this the moment you need multi-brand /
  multi-theme tokens, DTCG ($value/$type) files, composite tokens expanded, outputReferences,
  or a `style-dictionary build` step wired into a design system. Not just colours.
when_to_use:
  - Standing up a design-token source of truth (spacing, radius, shadow, type, motion) as W3C DTCG JSON
  - Compiling one token set to many outputs (CSS vars, SCSS, JS/TS, iOS Swift, Android XML)
  - Supporting multiple brands or light/dark themes from a shared core token layer
  - Handling composite DTCG tokens (typography, shadow, border) via expand or custom formats
  - Preserving token references in output with outputReferences so var() aliases survive
  - Wiring `style-dictionary build` into a repo, CI, or a design-system package
when_not_to_use:
  - You only need a colour ramp or palette in OKLCH — use oklch-color-engine or perceptual-gradient-designer
  - You want brand colours mapped to semantic slots without a build tool — use brand-color-token-system
  - You need runtime CSS-variable theming in a live app only — use theme-factory
  - You are choosing type scales / pairings rather than emitting tokens — use typography-type-system
keywords:
  - design tokens
  - style dictionary
  - dtcg
  - w3c
  - token pipeline
  - multi-brand
  - css variables
  - scss
  - theming
  - spacing scale
  - typography tokens
  - motion tokens
  - outputReferences
  - transform group
  - composite tokens
similar_to:
  - brand-color-token-system
  - theme-factory
  - typography-type-system
  - oklch-color-engine
  - design-system
inputs_needed: Node.js 18+ and npm; a set of raw design decisions (spacing scale, radii, shadows, type ramp, durations, brand colours) to encode as DTCG tokens; the target platforms you must emit (web/iOS/Android).
produces: A `tokens/` tree of DTCG `.tokens.json` files, a Style Dictionary config, and generated platform outputs (CSS custom properties, SCSS, JS/TS, iOS Swift, Android XML) — optionally per brand/theme.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Design Tokens Pipeline (W3C DTCG + Style Dictionary)

Turn one tool-agnostic set of **W3C Design Tokens Community Group (DTCG)** files into CSS, SCSS,
JS/TS, iOS and Android outputs with **Style Dictionary v5** — the full surface (spacing, radius,
shadow, typography, motion), not just colour, and scaling to multiple brands and light/dark themes.

## When to use

Use this when you need a real build step (`style-dictionary build`) that fans one source of
truth out to many platforms, or when tokens must be DTCG-compliant (`$value` / `$type`) so they
round-trip with Figma Variables, Tokens Studio, and other tools. If you only need a palette or
runtime theming, use the alternatives listed in the frontmatter.

## Prerequisites

- **Node.js 18+** and npm (Style Dictionary v5 is ESM-only; v4 also supports DTCG if you are pinned).
- Install locally so the build is reproducible:
  ```bash
  npm install -D style-dictionary   # adds "style-dictionary" to devDependencies
  npx style-dictionary --version    # confirm the CLI resolves (expect 5.x or 4.x)
  ```
- No API keys. Everything runs offline once installed.
- macOS note: this machine has no node/npm; author the files here, run the build where Node lives (CI or a dev box).

## DTCG in one screen

A DTCG token uses `$value` and `$type`; groups nest freely and set a group-level `$type`. Style
Dictionary auto-detects DTCG when files end in `.tokens.json`/`.tokens`; `usesDtcg: true` makes it explicit.

```jsonc
// tokens/core/spacing.tokens.json
{ "space": { "$type": "dimension",
    "1": { "$value": "4px" }, "2": { "$value": "8px" },
    "4": { "$value": "16px" }, "6": { "$value": "24px" }, "8": { "$value": "32px" } } }
```

Common `$type` values: `color`, `dimension`, `fontFamily`, `fontWeight`, `number`, `duration`,
`cubicBezier`, `shadow`, `typography`, `border`, `transition`. References use curly-brace paths:
`{space.4}`, `{color.brand.500}`.

## Recipe 1 — Minimal single-brand build

1. Lay out tokens as DTCG files:

   ```
   tokens/
     core/
       color.tokens.json     # color.brand.500 = "#6C2BD9", etc.
       spacing.tokens.json
       radius.tokens.json
       shadow.tokens.json    # $type: shadow (composite)
       typography.tokens.json# $type: typography (composite)
       motion.tokens.json    # duration + cubicBezier
   ```

2. Add `config.json` at the repo root:

   ```jsonc
   {
     "log": { "verbosity": "verbose" },
     "usesDtcg": true,
     "source": ["tokens/**/*.tokens.json"],
     "expand": { "typesMap": true },
     "platforms": {
       "css": {
         "transformGroup": "css",
         "buildPath": "build/css/",
         "files": [{
           "destination": "tokens.css",
           "format": "css/variables",
           "options": { "outputReferences": true }
         }]
       },
       "scss": {
         "transformGroup": "scss",
         "buildPath": "build/scss/",
         "files": [{ "destination": "_tokens.scss", "format": "scss/variables" }]
       },
       "js": {
         "transformGroup": "js",
         "buildPath": "build/js/",
         "files": [
           { "destination": "tokens.js", "format": "javascript/es6" },
           { "destination": "tokens.d.ts", "format": "typescript/es6-declarations" }
         ]
       }
     }
   }
   ```

3. Build:

   ```bash
   npx style-dictionary build --config config.json
   ```

   `outputReferences: true` keeps aliases as `var(--space-4)` instead of flattening to `16px`.
   `expand` splits composite `typography`/`shadow`/`border` tokens into constituent tokens so
   flat targets (CSS/SCSS) can emit them.

## Recipe 2 — Composite tokens (shadow, typography, motion)

```jsonc
// tokens/core/shadow.tokens.json
{
  "shadow": {
    "$type": "shadow",
    "card": {
      "$value": {
        "color": "#00000026", "offsetX": "0px", "offsetY": "2px",
        "blur": "8px", "spread": "0px"
      }
    }
  }
}
```

```jsonc
// tokens/core/typography.tokens.json — composite typography + a motion set
{
  "text": {
    "$type": "typography",
    "body": { "$value": {
      "fontFamily": "{font.family.sans}", "fontSize": "16px",
      "fontWeight": 400, "lineHeight": "1.5"
    }}
  },
  "duration": { "$type": "duration", "base": { "$value": "250ms" } },
  "easing": { "$type": "cubicBezier", "standard": { "$value": [0.2, 0, 0, 1] } }
}
```

With `expand` on, `text.body` becomes `--text-body-font-size`, `--text-body-line-height`, etc.
For a single CSS `font:` or `box-shadow` shorthand instead, register a custom format
(see Recipe 4) rather than expanding.

## Recipe 3 — Multi-brand / multi-theme

Keep a shared **core** layer and thin **brand/theme** overrides, then build each brand into its
own output folder with a small JS runner. Use `scripts/build-tokens.mjs` (bundled):

```
tokens/
  core/                        # brand-agnostic scales (spacing, radius, motion, type ramp)
  brands/acme/color.tokens.json    # color.brand.500 = "#6C2BD9"
  brands/umbra/color.tokens.json   # color.brand.500 = "#0F62FE"
  themes/acme.light.tokens.json    # semantic: color.bg = "{color.neutral.50}"
  themes/acme.dark.tokens.json     # semantic: color.bg = "{color.neutral.900}"
```

```bash
node scripts/build-tokens.mjs acme umbra   # builds build/<brand>/tokens.css each
```

The runner loops brands, constructs `new StyleDictionary(...)` per brand with `source` =
core + that brand's files, and awaits `buildAllPlatforms()`. Because Style Dictionary v5's
API is fully async, each brand is an isolated instance — no leaking state between builds.

## Recipe 4 — Custom transform / format (when built-ins fall short)

Register hooks on the class before you build (v5 signatures). DTCG tokens expose `$value`/`$type`
on the token object (not `value`/`type`):

```js
import StyleDictionary from 'style-dictionary';

StyleDictionary.registerTransform({
  name: 'size/px-to-rem',
  type: 'value',
  transitive: true, // run after references resolve
  filter: (token) => token.$type === 'dimension' && String(token.$value).endsWith('px'),
  transform: (token) => `${parseFloat(token.$value) / 16}rem`,
});
```

Then reference `"size/px-to-rem"` in a platform's `transforms` array. Custom `registerFormat`
hooks (signature `format: async ({ dictionary }) => string`) let you emit a `box-shadow` or
`font` shorthand from composite tokens instead of expanding them.

## Verify

```bash
# 1. Config + tokens parse and a build runs clean
npx style-dictionary build --config config.json

# 2. Outputs exist and contain expected vars
grep -- '--space-4' build/css/tokens.css        # dimension token emitted
grep -- 'var(--space-4)' build/css/tokens.css   # outputReferences preserved an alias

# 3. Multi-brand runner produced per-brand files, references all resolved
node scripts/build-tokens.mjs acme umbra
ls build/acme/tokens.css build/umbra/tokens.css
! grep -RE '\{[a-z0-9.]+\}' build/ || echo "UNRESOLVED REFERENCE — check token paths"
```

A green build prints each platform and file written. Style Dictionary errors loudly on broken
references and unknown token types, so a clean run is a strong signal.

## Pitfalls

- **`value` vs `$value`.** In DTCG mode everything is `$`-prefixed. Mixing legacy `value` tokens
  with `usesDtcg: true` silently drops them. Convert legacy files first (SD ships a converter; it
  does not remap old `$type` names like `size` → `dimension`, so fix those by hand).
- **Composite tokens don't emit to flat targets by themselves.** Turn on `expand`, or write a
  custom format (Recipe 4). Without either, `typography`/`shadow` tokens vanish from CSS output.
- **outputReferences needs the referenced token in the same build.** If a brand build excludes the
  core file a token points at, the reference flattens to a literal or errors. Include core sources.
- **ESM only.** v5 config `.js` files use `export default`; a `.cjs` `module.exports` config fails.
  Use `config.json` or an `.mjs` runner. `buildPath` must end in `/` or files land in the parent dir.
- **Transitive references + custom transforms.** Set `transitive: true` on a value transform or it
  runs before references resolve and mangles alias values.
- **Don't hand-edit generated files.** `build/` is output; regenerate from `tokens/` and gitignore it
  unless a consuming package needs the compiled artefacts committed.
