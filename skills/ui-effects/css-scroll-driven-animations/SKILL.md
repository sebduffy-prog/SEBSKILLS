---
name: css-scroll-driven-animations
category: ui-effects
description: >
  Build scroll-linked and view-triggered animations with native CSS — zero JavaScript, zero
  IntersectionObserver — using animation-timeline: scroll() / view(), named scroll-timeline /
  view-timeline, animation-range with entry/exit/cover/contain, timeline-scope, plus @starting-style
  for first-render entry animations. Use when the user asks for a "scroll progress bar", "scroll
  reveal in pure CSS", "parallax on scroll", "image reveal as it enters", "scroll-linked animation",
  "animation-timeline", "scroll() view() CSS", or wants to drop the JS scroll listeners. Compositor-driven, GSAP-free.
when_to_use:
  - A reading-progress or section-progress bar that fills as the page scrolls
  - Elements that fade / slide / scale in as they enter the viewport, driven purely by CSS
  - Parallax, horizontal-scroll galleries, or cover-flow effects tied to scroll position
  - Replacing an IntersectionObserver or GSAP ScrollTrigger setup with native, compositor-driven CSS
  - Animating an element in on first render or from display:none with @starting-style
  - You want jank-free scroll animation that runs off the main thread
when_not_to_use:
  - You need a JS-observer reveal with per-child stagger callbacks and legacy-browser reach — use scroll-reveal-section instead
  - Morphing one element into another across a route/state change — use view-transitions-morphing instead
  - A continuously looping logo strip unrelated to scroll position — use infinite-marquee instead
  - Counting a number up when it scrolls into view — use animated-counter instead
keywords:
  - scroll-driven-animations
  - animation-timeline
  - scroll-timeline
  - view-timeline
  - animation-range
  - timeline-scope
  - starting-style
  - scroll-progress
  - parallax
  - view
  - scroll-reveal
  - css-only
  - compositor
  - prefers-reduced-motion
similar_to:
  - scroll-reveal-section
  - view-transitions-morphing
  - infinite-marquee
inputs_needed: Target element(s) and the trigger — page/container scroll progress (scroll()) or element-enters-viewport (view()); the CSS property to animate.
produces: A self-contained CSS block (plus minimal HTML) wiring animation-timeline + @keyframes, with a reduced-motion fallback.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# CSS Scroll-Driven Animations

Drive `@keyframes` from **scroll position** instead of time. The browser advances the animation
as the user scrolls, on the compositor thread, so it stays smooth with no `scroll` listener and no
`IntersectionObserver`. Two timeline sources:

- **`scroll()`** — progress of a **scroll container** (0% at top, 100% at bottom). Use for progress bars, page-wide parallax.
- **`view()`** — progress of the **subject element's own pass through the scrollport**. Use for reveal-on-enter effects.

## When to use

Reach for this over the JS `scroll-reveal-section` skill when you want native, main-thread-free
animation and can accept a progressive-enhancement fallback for Firefox stable. If you need
guaranteed reach on every browser today with stagger callbacks, use `scroll-reveal-section`.

## Prerequisites

- **No dependencies.** Pure CSS. Works in any bundler or a plain `.html` file.
- **Browser support (verify at caniuse.com/mdn-css_properties_animation-timeline_scroll):**
  - Chrome / Edge **115+** (July 2023, unflagged).
  - Safari **26+** (Sept 2025).
  - Firefox: **behind `layout.css.scroll-driven-animations.enabled`** in stable as of 152 (default-on in Nightly; an Interop 2026 priority). Treat Firefox stable as the fallback case.
- **Optional polyfill** for older engines: `flackr/scroll-timeline` (npm `scroll-timeline-polyfill`). It reimplements the JS `ScrollTimeline`/`ViewTimeline` objects; the CSS `animation-timeline` support in it is partial, so prefer native + graceful fallback for most work.
- Because it degrades to "no animation" (element just shows in its final state), **always author the un-animated end state as the default** and let the animation only add motion.

## Recipes

### 1. Reading / scroll progress bar (`scroll()`)

```css
@keyframes grow-progress { from { transform: scaleX(0); } to { transform: scaleX(1); } }

.progress-bar {
  position: fixed; inset: 0 0 auto 0; height: 4px;
  transform-origin: 0 50%; background: hotpink;

  animation: grow-progress auto linear;   /* name + duration (auto ok in Chrome) */
  animation-timeline: scroll(root block); /* whole-page vertical scroll */
}
```

`scroll(<axis> <scroller>)` — axis `block` (default) | `inline` | `x` | `y`; scroller `nearest`
(default) | `root` (the document viewport) | `self`.

### 2. Reveal an element as it enters the viewport (`view()`)

```css
@keyframes reveal {
  from { opacity: 0; transform: translateY(40px); }
  to   { opacity: 1; transform: translateY(0); }
}

.card {
  animation: reveal linear both;
  animation-timeline: view();       /* the card's own trip through the scrollport */
  animation-range: entry 0% entry 100%;  /* play only while entering */
}
```

`view(<axis> <inset>)` — inset shrinks the "active" scrollport (e.g. `view(block 20%)` starts the
timeline 20% in from each edge). `both` keeps the from-state before entry and the to-state after.

### 3. `animation-range` — the timeline windows for `view()`

Named ranges describe where the subject sits relative to the scrollport:

- `cover` — from the moment any part enters to the moment the last part leaves (full pass).
- `contain` — the span where the element is fully inside the scrollport.
- `entry` / `exit` — the entering / leaving phases specifically.
- `entry-crossing` / `exit-crossing` — while the element crosses the far edge.

```css
animation-range: cover 0% cover 100%;   /* animate across the entire pass */
animation-range: entry 25% cover 50%;   /* start 25% into entry, end at 50% cover */
```

### 4. Named timeline — one scroller drives a distant element

Anonymous `scroll()`/`view()` only reach an ancestor scroller. To link a **sibling/cousin**, name
the timeline and hoist it with `timeline-scope`:

```css
.gallery {                       /* the scroll container */
  overflow-x: auto;
  scroll-timeline: --gallery x;  /* name + axis */
}
.wrapper { timeline-scope: --gallery; } /* common ancestor of scroller + target */
.indicator {
  animation: grow-progress auto linear;
  animation-timeline: --gallery; /* references the named timeline */
}
```

Use `view-timeline: --name block` the same way to expose a subject's view progress by name.
Timeline names are `<dashed-ident>` — they must start with `--`.

### 5. `@starting-style` — animate in on first render / from `display:none`

Not scroll-driven, but the companion primitive for entry animations. It supplies the *pre-render*
values a transition starts from, so newly-inserted or `display:none → block` elements animate in:

```css
.toast {
  opacity: 1; transform: translateY(0);
  transition: opacity .3s, transform .3s, display .3s allow-discrete;
}
@starting-style {
  .toast { opacity: 0; transform: translateY(-12px); }
}
```

Pair `transition-behavior: allow-discrete` (or the `allow-discrete` keyword above) with `display`
so the element stays visible through its exit transition.

## Critical: the `animation` shorthand resets the timeline

Setting the `animation` shorthand **after** `animation-timeline` silently resets the timeline to
`auto` (time-based), and it also resets `animation-range`. Order matters:

```css
/* WRONG — shorthand wipes the timeline set above it */
.x { animation-timeline: view(); animation: reveal linear both; }

/* RIGHT — longhands, or timeline/range declared AFTER the shorthand */
.x { animation: reveal linear both; animation-timeline: view(); animation-range: entry; }
```

## Reduced-motion fallback

Scroll-driven motion can trigger vestibular discomfort. Gate it and keep the end state readable:

```css
.card { opacity: 1; }                 /* visible by default = the fallback */
@media (prefers-reduced-motion: no-preference) {
  @supports (animation-timeline: view()) {
    .card {
      animation: reveal linear both;
      animation-timeline: view();
      animation-range: entry;
    }
  }
}
```

`@supports (animation-timeline: view())` also cleanly excludes Firefox stable (flag off), so those
users see the finished layout with no missing content.

## Verify

Paste into a `.html` file and open in Chrome 115+ or Safari 26+; scroll and watch the top bar fill
and cards fade up. Confirm the page still reads correctly with reduced-motion on (macOS: System
Settings → Accessibility → Display → Reduce motion).

```html
<!doctype html><meta charset="utf-8">
<style>
  body { margin: 0; font: 16px/1.5 system-ui; }
  .bar { position: fixed; inset: 0 0 auto 0; height: 5px; background: hotpink;
         transform-origin: 0 50%;
         animation: grow auto linear; animation-timeline: scroll(root); }
  section { min-height: 90vh; display: grid; place-items: center; }
  .card { padding: 2rem 3rem; border-radius: 12px; background: #eee; opacity: 1; }
  @keyframes grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
  @keyframes up   { from { opacity: 0; transform: translateY(50px); } to { opacity: 1; transform: none; } }
  @media (prefers-reduced-motion: no-preference) {
    @supports (animation-timeline: view()) {
      .card { animation: up linear both; animation-timeline: view(); animation-range: entry 0% cover 45%; }
    }
  }
</style>
<div class="bar"></div>
<section><div class="card">Scroll down ↓</div></section>
<section><div class="card">I fade up on entry</div></section>
<section><div class="card">So do I</div></section>
```

Quick DOM check that the property parses in the current browser (DevTools console):

```js
CSS.supports('animation-timeline', 'view()')  // true on supported engines
```

## Pitfalls

- **Timeline not applying?** The element needs a **named animation** and a **duration** (`animation: name auto ...` or an explicit `1ms` — Firefox historically required a non-zero duration). `animation-timeline` alone does nothing.
- **`scroll()` finds no scroller.** `scroll()` walks up for the nearest *scrollable* ancestor; if none scrolls, nothing moves. Ensure an ancestor has `overflow: scroll/auto` and a constrained size, or use `scroll(root)`.
- **Anonymous timelines can't reach siblings.** A subject can only read an *ancestor's* `scroll()`/`view()`. For sibling/cousin links use a **named** `scroll-timeline`/`view-timeline` + `timeline-scope` on a common ancestor.
- **Shorthand reset** (see the section above) — the single most common "why is it broken" cause.
- **`view-timeline` on a scrollable subject:** an element that is itself a scroll container can't also be a good `view()` subject; wrap it.
- **Don't animate layout properties** (`width`, `top`, `margin`) — animate `transform`/`opacity` to keep it on the compositor; layout props force reflow every frame and defeat the point.
- **Firefox stable** ships it off-by-default (as of mid-2026). The `@supports` + visible-by-default pattern above is not optional there.
