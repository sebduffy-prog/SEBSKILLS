---
name: motion-system
category: frontend-and-design
description: >-
  Define a reusable motion design system instead of hand-tuning every transition —
  a small named scale of duration, easing, spring and stagger tokens as CSS custom
  properties plus a Motion (motion.dev) JS map, with a first-class prefers-reduced-motion
  path. Reach for this when animations across a site feel inconsistent (random 300ms
  here, ease-in-out there), when you need one place to tune all timing, or when motion
  must be accessible. Grounded on motion.dev + the CSS spec.
when_to_use:
  - Animations across the app use scattered ad-hoc durations/easings and need one shared vocabulary
  - You want named motion tokens (--dur-fast, --ease-emphasized, spring presets) in CSS and JS
  - Building enter/exit + stagger patterns for lists, cards, modals that must feel like one system
  - You must respect prefers-reduced-motion without deleting every animation by hand
  - Choosing spring vs easing and want defensible physics presets rather than guesswork
when_not_to_use:
  - Implementing one specific complex effect (shatter, distortion, WebGL) — use that effect's skill
  - Pure scroll-reveal wrapper only — use scroll-reveal-section
  - Colour/gradient token work — use brand-color-token-system or perceptual-gradient-designer
  - Fluid type/space scales unrelated to timing — use fluid-responsive-system
keywords:
  - motion
  - animation
  - easing
  - duration
  - spring
  - stagger
  - transition
  - prefers-reduced-motion
  - design-tokens
  - cubic-bezier
  - motion.dev
  - css-custom-properties
  - choreography
  - accessibility
  - enter-exit
similar_to:
  - fluid-responsive-system
  - brand-color-token-system
  - scroll-reveal-section
  - frontend-design
inputs_needed: A target project (CSS + optionally the `motion` npm package), and a rough sense of brand personality (calm/snappy/playful) to pick spring bounce and easing character
produces: A drop-in motion-tokens.css file of named duration/easing/spring/stagger custom properties, a matching JS token map for Motion, reduced-motion overrides, and copy-paste enter/exit/stagger recipes
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Motion System

Consistent motion is a token problem, not a per-component problem. Pick a **small
named scale** once — a handful of durations, 3–4 easing curves, 2–3 spring presets,
one stagger step — then every animation references a token. Tuning the whole feel
becomes editing one file. This skill gives you that scale for both **CSS transitions**
and **Motion (motion.dev) JS**, with `prefers-reduced-motion` handled at the token
layer so you never sprinkle guards through components.

## When to use

Use it the moment a second animation appears in a codebase. Two hand-typed durations
is already drift. Also use it when an accessibility pass flags motion, or when a
designer says "make everything feel snappier" and you want a one-line answer.

## Prerequisites

- CSS custom properties support (every current browser). No build step required.
- For JS springs/stagger: `npm i motion` (motion.dev — the successor to Framer Motion's
  vanilla API). Import from `"motion"`.
- python3 3.9 only needed if you run the token-lint check at the end.

## The scale (design decisions first)

Keep it minimal — more tokens means more drift, not less.

- **Durations** — a geometric-ish ramp, not linear. `instant 80ms`, `fast 150ms`,
  `base 250ms`, `slow 400ms`, `slower 600ms`. Enter is usually one step slower than exit.
- **Easing** — four curves cover almost everything:
  - `standard` (in-out) for things moving within the viewport,
  - `decelerate` (ease-out) for elements **entering** (fast → settle),
  - `accelerate` (ease-in) for elements **leaving** (settle → fast off-screen),
  - `emphasized` — an expressive overshoot-ish curve for hero/brand moments.
- **Spring** — prefer springs for anything interactive or gesture-driven (they
  interrupt gracefully). Define presets by *feel* using Motion's `bounce`+`visualDuration`,
  not raw stiffness: `snappy` (no bounce), `gentle` (soft), `bouncy` (playful).
- **Stagger** — one base step (`0.05s`) scaled per context. Never larger than ~0.08s
  for lists over ~8 items or the tail feels laggy.

## Recipe 1 — motion-tokens.css (drop in globally)

```css
:root {
  /* durations */
  --dur-instant: 80ms;
  --dur-fast:    150ms;
  --dur-base:    250ms;
  --dur-slow:    400ms;
  --dur-slower:  600ms;

  /* easing curves (cubic-bezier control points) */
  --ease-standard:   cubic-bezier(0.2, 0, 0, 1);
  --ease-decelerate: cubic-bezier(0, 0, 0, 1);      /* enter */
  --ease-accelerate: cubic-bezier(0.3, 0, 1, 1);    /* exit  */
  --ease-emphasized: cubic-bezier(0.2, 0, 0, 1.2);  /* slight overshoot */

  /* composed shorthands — reference these in components */
  --motion-enter: var(--dur-base) var(--ease-decelerate);
  --motion-exit:  var(--dur-fast) var(--ease-accelerate);
  --motion-move:  var(--dur-base) var(--ease-standard);

  /* stagger step (consumed by JS; kept here as the single source of truth) */
  --stagger-step: 0.05s;
}

/* Reduced-motion: collapse timing at the TOKEN layer.
   Components keep referencing the same vars — nothing else changes. */
@media (prefers-reduced-motion: reduce) {
  :root {
    --dur-instant: 0.01ms;
    --dur-fast:    0.01ms;
    --dur-base:    0.01ms;
    --dur-slow:    0.01ms;
    --dur-slower:  0.01ms;
    --stagger-step: 0s;
  }
}
```

Then components never hardcode timing:

```css
.card        { transition: transform var(--motion-move), box-shadow var(--motion-move); }
.card:hover  { transform: translateY(-4px); }
.toast       { animation: slide-in var(--motion-enter) both; }
```

Because reduced-motion rewrites the tokens (not each rule), transitions still *fire*
— they just complete in ~0ms, so state changes stay instant and correct rather than
jumping in a way that breaks `transitionend` listeners.

## Recipe 2 — JS token map for Motion (motion.dev)

Mirror the CSS so JS and CSS animations share one vocabulary.

```js
// motion-tokens.js
export const dur = { instant: 0.08, fast: 0.15, base: 0.25, slow: 0.4, slower: 0.6 };

export const ease = {
  standard:   [0.2, 0, 0, 1],
  decelerate: [0, 0, 0, 1],
  accelerate: [0.3, 0, 1, 1],
  emphasized: [0.2, 0, 0, 1.2],
};

// Springs defined by feel. bounce 0 = no overshoot, ~0.3 = playful.
// visualDuration = how long it *looks* like it takes to reach target.
export const spring = {
  snappy: { type: "spring", visualDuration: 0.25, bounce: 0 },
  gentle: { type: "spring", visualDuration: 0.5,  bounce: 0.15 },
  bouncy: { type: "spring", visualDuration: 0.5,  bounce: 0.35 },
};

export const staggerStep = 0.05;

// Single accessibility gate for JS animations.
export const reduced =
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;
```

## Recipe 3 — enter / exit with tokens

```js
import { animate } from "motion";
import { dur, ease, reduced } from "./motion-tokens.js";

// Enter: fade + rise, decelerate easing (fast in, soft settle)
animate(el,
  { opacity: [0, 1], y: [12, 0] },
  { duration: reduced ? 0 : dur.base, ease: ease.decelerate }
);

// Exit: quicker, accelerate easing (settle → whip off)
animate(el,
  { opacity: 0, y: -8 },
  { duration: reduced ? 0 : dur.fast, ease: ease.accelerate }
);
```

## Recipe 4 — staggered list reveal

`stagger()` returns a function Motion calls per element to compute its delay.

```js
import { animate, stagger } from "motion";
import { dur, ease, staggerStep, reduced } from "./motion-tokens.js";

animate(
  "li.item",
  { opacity: [0, 1], y: [16, 0] },
  {
    duration: reduced ? 0 : dur.base,
    ease: ease.decelerate,
    delay: stagger(reduced ? 0 : staggerStep, { from: "first", ease: "easeOut" }),
  }
);
```

`from` accepts `"first" | "center" | "last" | <index>` — `"center"` ripples outward,
great for grids. Use `startDelay` in the options to offset the whole group after a
parent has landed.

## Recipe 5 — interactive spring (prefer over duration for gestures)

```js
import { animate } from "motion";
import { spring, reduced } from "./motion-tokens.js";

button.addEventListener("pointerdown", () =>
  animate(button, { scale: 0.94 }, reduced ? { duration: 0 } : spring.snappy)
);
button.addEventListener("pointerup", () =>
  animate(button, { scale: 1 }, reduced ? { duration: 0 } : spring.bouncy)
);
```

Springs interrupt cleanly: a second `animate()` mid-flight retargets from current
velocity, so mashing the button never snaps or stutters — the reason to prefer them
for anything the user can re-trigger.

## Verify

- **Token indirection:** grep the codebase for literal timing — there should be
  (almost) none outside the token files:
  `grep -rnE '[0-9]+ms|[0-9.]+s\b' src --include=*.css | grep -v motion-tokens.css`
- **Reduced motion:** in devtools → Rendering → "Emulate prefers-reduced-motion:
  reduce", confirm animations resolve instantly and no layout jumps or stuck states appear.
- **Spring interrupt:** rapidly re-trigger a spring; motion should retarget smoothly,
  never restart from zero.
- **Stagger tail:** with N items, last delay ≈ `(N-1) * step`. If the tail feels
  slow, lower the step or switch `from: "center"`.

## Pitfalls

- **Duplicating the scale in JS and CSS out of sync.** Treat CSS as source of truth;
  update both files in the same commit (a tiny build step can generate the JS map).
- **`transition: all`.** It animates properties you didn't mean to (including layout),
  costs performance, and ignores your easing intent per-property. Name the properties.
- **Animating `width`/`height`/`top`/`left`.** These trigger layout on every frame.
  Animate `transform` and `opacity`; use `translate`/`scale` for position and size.
- **Deleting animations for reduced-motion.** Users who set it still need *feedback*
  and correct end-states — collapse duration to ~0, don't remove the rule, or you'll
  break `transitionend`/`animationend` handlers and leave elements mid-state.
- **Bouncy springs on utilitarian UI.** Reserve `bounce > 0.2` for brand/hero moments;
  toasts, menus and form controls read as "broken" when they wobble.
- **Long durations on frequent interactions.** Hover/press should feel instant
  (`fast` or `snappy`). Save `slow`/`slower` for large entrances and page-level transitions.
- **Stagger step too large.** Above ~0.08s per item the list looks like it's loading,
  not animating. Scale the step down as item count grows.
