---
name: view-transitions-morphing
category: ui-effects
description: >
  Use the native View Transitions API to morph between UI states and pages with
  zero animation JS — crossfade the whole viewport, or FLIP-morph a shared element
  (thumbnail → hero, card → detail, list reorder) by tagging it with
  view-transition-name. Covers same-document (document.startViewTransition) SPA
  swaps AND cross-document (@view-transition) multi-page navigation with pageswap/
  pagereveal, honest browser-support gating, and reduced-motion. Trigger on "view
  transitions", "page morph", "shared element transition", "smooth page navigation",
  "MPA transitions", or "crossfade route change".
when_to_use:
  - Morphing a thumbnail into a full hero image (or card into a detail page) so one element appears to fly and grow across the swap
  - Adding a smooth crossfade between routes in a SPA without pulling in Framer Motion or GSAP
  - Giving a classic multi-page site (server-rendered, Astro, plain HTML) animated navigations with zero client JS
  - Animating list reordering, filtering, or add/remove where items should slide to new positions (FLIP for free)
  - Replacing hand-rolled FLIP or layout-animation code with the browser-native primitive
when_not_to_use:
  - Continuous gesture-driven or physics/spring motion (drag, momentum, cursor-follow) — reach for a spring lib or the magnetic-cursor / interactive-distortion skills
  - Scroll-triggered entrance reveals of many elements — use the scroll-reveal-section skill instead
  - A single decorative hover effect on one component — use image-shatter, liquid-image, or the relevant ui-effects skill
  - You must support browsers with no View Transition support AND a transition is mandatory (not enhancement) — use an animation library with its own FLIP engine
keywords: [view-transitions, startviewtransition, shared-element-transition, view-transition-name, cross-document, mpa, spa, page-morph, crossfade, flip, pageswap, pagereveal, reduced-motion, css-animation, baseline]
similar_to: [scroll-reveal-section, image-shatter, liquid-image, framer-level-interactions]
inputs_needed: The DOM/route change to animate, plus which element (if any) should morph across the change (its stable identity).
produces: Drop-in HTML/CSS/JS snippets — a startViewTransition wrapper, view-transition-name tagging, @view-transition cross-document setup, and custom keyframes for the ::view-transition pseudo-elements.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# View Transitions — Native Morphing Between States and Pages

The **View Transitions API** animates a change to the DOM by snapshotting the old and
new states and cross-fading (or morphing) between them, with the animation described
purely in CSS. You get FLIP-style shared-element morphs for free — no measuring, no
transform math, no animation library.

Two modes:

- **Same-document** (`document.startViewTransition`) — for SPA state/route swaps.
- **Cross-document** (`@view-transition { navigation: auto }`) — for classic MPA
  navigations (server-rendered, Astro, plain multi-page). **Zero JS** for the basic case.

## When to use

Reach for this when a change of state or page has a clear *before* and *after* and you
want the browser to tween between them: crossfades, a shared element that grows/flies,
or lists that reflow. It is an **enhancement** — if the API is missing, the DOM still
updates instantly.

## Prerequisites

- **No dependencies, no build step.** It is a browser platform feature.
- **Support (as of mid-2026):**
  - *Same-document* is Baseline "Newly available" — Chrome/Edge 111+, Safari 18+,
    Firefox 129+. Broadly usable today.
  - *Cross-document* (`@view-transition`) is newer and less universal — Chromium 126+,
    Safari 18.2+; Firefox trailing. **Always treat as progressive enhancement.**
- **Always feature-detect** for same-document JS: `if (!document.startViewTransition)`.
- **Always respect** `prefers-reduced-motion`.

## Recipes

### 1. Same-document crossfade (the one-liner)

Wrap the DOM mutation. That is the whole API for a basic crossfade.

```js
function swap(updateDom) {
  // Feature-detect: fall back to an instant update.
  if (!document.startViewTransition) { updateDom(); return; }
  document.startViewTransition(updateDom);
}

// e.g. swap route content
swap(() => { app.innerHTML = renderPage(nextRoute); });
```

`startViewTransition` returns a `ViewTransition` with promises you can await:

```js
const vt = document.startViewTransition(() => renderRoute(next));
await vt.ready;            // pseudo-elements built, animation about to run
await vt.updateCallbackDone; // your DOM callback finished
await vt.finished;        // animation fully done
// vt.skipTransition() jumps straight to the end
```

### 2. Shared-element morph (thumbnail → hero)

Give the *same* `view-transition-name` to the before and after element. The browser
matches them by name and morphs position, size, and content between them. **A name
must be unique per rendered state** — never tag two visible elements with the same name.

```css
/* Old page: the thumbnail. New page: the big hero. Same name → morph. */
.thumb.is-active,
.hero-image {
  view-transition-name: hero-media;
}
```

For a list where each row can morph to a detail view, assign names dynamically so only
the active one is tagged (avoid duplicate-name errors):

```js
// Before starting the transition, tag just the clicked item.
clickedCard.style.viewTransitionName = 'hero-media';
const vt = document.startViewTransition(() => navigateToDetail(id));
vt.finished.finally(() => { clickedCard.style.viewTransitionName = ''; });
```

### 3. Cross-document (MPA) — zero JS

Put this on **both** the source and destination pages (same origin). Same-origin
navigations then animate automatically.

```css
@view-transition { navigation: auto; }   /* or: none, to opt out */

/* Persist a shared header/logo across the whole site so it doesn't crossfade */
.site-logo { view-transition-name: site-logo; }

/* Give the main content its own name so it can be styled independently */
main { view-transition-name: page-main; }
```

To coordinate *which* element morphs across two different pages (list → detail), set a
matching name on both pages just before navigation using the `pageswap` event (old page)
and `pagereveal` event (new page):

```js
// On the LIST page — tag the clicked card on the way out.
window.addEventListener('pageswap', (e) => {
  if (!e.viewTransition) return;                 // navigation not transitioning
  const id = sessionStorage.getItem('activeId');
  document.querySelector(`#card-${id}`)?.style.setProperty('view-transition-name', 'hero-media');
});

// On the DETAIL page — tag the hero on the way in.
window.addEventListener('pagereveal', (e) => {
  if (!e.viewTransition) return;
  document.querySelector('.hero-image')?.style.setProperty('view-transition-name', 'hero-media');
});
```

### 4. Customise the animation (CSS keyframes on the pseudo-elements)

During a transition the browser builds a tree of pseudo-elements on the root:

```
::view-transition                       (overlay covering the viewport)
└─ ::view-transition-group(name)        (animates size + position — the morph)
   └─ ::view-transition-image-pair(name)
      ├─ ::view-transition-old(name)    (snapshot of the old view — fades out)
      └─ ::view-transition-new(name)    (live new view — fades in)
```

`name` is `root` for the default whole-page transition, or your `view-transition-name`.

```css
/* Slower crossfade for everything */
::view-transition-old(root),
::view-transition-new(root) { animation-duration: 0.4s; }

/* Slide the main content in from the right instead of crossfading */
@keyframes slide-from-right { from { transform: translateX(30px); opacity: 0; } }
@keyframes slide-to-left    { to   { transform: translateX(-30px); opacity: 0; } }
::view-transition-old(page-main) { animation: 0.3s ease both slide-to-left; }
::view-transition-new(page-main) { animation: 0.3s ease both slide-from-right; }
```

Group many named elements with one style hook via `view-transition-class`:

```css
.card { view-transition-class: card-morph; }
::view-transition-group(.card-morph) { animation-duration: 0.5s; }
```

### 5. Transition *types* (directional / conditional animations)

Pass `types` to drive different CSS per transition kind (e.g. forward vs back):

```js
document.startViewTransition({
  update: () => renderRoute(next),
  types: [next.index > current.index ? 'forward' : 'back'],
});
```

```css
:active-view-transition-type(back) ::view-transition-old(page-main) {
  animation: 0.3s ease both slide-from-right;   /* reverse the direction */
}
```

### 6. Respect reduced motion (do this every time)

```css
@media (prefers-reduced-motion: reduce) {
  ::view-transition-group(*),
  ::view-transition-old(*),
  ::view-transition-new(*) { animation: none !important; }
}
```

## Verify

1. **DevTools → Animations panel** (Chrome): trigger the change, hit the pause button;
   you can scrub the `::view-transition-*` timeline and confirm named groups exist.
2. **Force-slow it** to eyeball the morph: `::view-transition-group(*){animation-duration:3s!important;}`.
3. **Shared-element sanity:** if the element jump-cuts instead of morphing, the two
   `view-transition-name`s don't match, or one wasn't rendered when the snapshot was taken.
4. **Duplicate-name check:** the console throws and skips the transition if two visible
   elements share a name in the same state.
5. **Fallback path:** in a non-supporting browser (or DevTools with the feature off) the
   DOM must still update instantly with no error.
6. **Reduced motion:** toggle OS "reduce motion" (or DevTools rendering emulation) and
   confirm the swap is instant.

## Pitfalls

- **Snapshots are static images.** The `::view-transition-old` is a bitmap of the old
  state; mid-transition JS/video won't update it. Keep transitions short (< 500ms).
- **`position` and layout on named elements:** an element with `view-transition-name`
  is lifted into the overlay during the transition. Large/`position:fixed` elements can
  behave oddly — name the smallest stable box you need to morph.
- **Duplicate names crash the transition** — tag dynamically and clean up in `.finished`.
- **Cross-document requires same origin** and the rule on *both* pages; it silently
  won't animate otherwise. It's the least-supported piece — never make UX depend on it.
- **`await vt.ready` can reject** if the transition is skipped (e.g. duplicate name);
  wrap awaits or use `.finally`, don't let a rejection break your navigation.
- **Don't animate huge trees** — naming the whole page plus dozens of children multiplies
  snapshot cost and can jank. Name only what should visibly move.
- **It's an enhancement, not a polyfill.** There is no official polyfill that reproduces
  the morph; if a browser lacks support, users get an instant swap — design for that.
- **Not for gestures.** This API animates discrete state *changes*, not continuous
  interaction. For drag/spring, use a motion library.
