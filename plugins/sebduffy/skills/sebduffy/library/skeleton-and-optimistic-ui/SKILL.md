---
name: skeleton-and-optimistic-ui
category: ui-effects
description: >
  Build perceived-speed UI: shimmer/skeleton placeholders while data loads, React
  Suspense streaming with the use() hook, and instant optimistic updates that roll
  back automatically on error via useOptimistic. Reach for this whenever a list, feed,
  card grid, form, like/vote button, or dashboard "flashes empty then pops in", a
  spinner feels janky, or a mutation should feel instant before the server confirms.
  Covers CSS-only skeletons (no React), Next.js loading.tsx, and React 19 Actions.
when_to_use:
  - A page shows a blank area or spinner while fetching, and you want a content-shaped skeleton instead
  - You want a like/vote/rename/add-to-cart button to update instantly and undo itself if the request fails
  - Streaming server data with React Suspense boundaries + the use() hook or Next.js loading.tsx
  - Reducing perceived latency / cumulative layout shift on a feed, list, or dashboard
  - Wrapping a slow subtree so the rest of the page renders immediately
when_not_to_use:
  - Pure decorative motion (hover tilt, marquee, glow) — use framer-level-interactions or aurora-gradient instead
  - Animating a single number counting up on scroll — use animated-counter instead
  - Scroll-triggered entrance reveals of already-loaded content — use scroll-reveal-section instead
  - A plain determinate progress bar with a known percentage — a simple width transition, no skill needed
keywords:
  - skeleton
  - shimmer
  - loading state
  - optimistic ui
  - useoptimistic
  - suspense
  - streaming
  - use hook
  - placeholder
  - rollback
  - perceived performance
  - react 19
  - loading.tsx
  - spinner replacement
similar_to:
  - animated-counter
  - scroll-reveal-section
  - floating-label-input
  - framer-level-interactions
inputs_needed: The framework (plain HTML/CSS, React 18, React 19, or Next.js App Router); the layout shape to mirror as a skeleton; for optimistic updates, the async mutation function.
produces: Copy-paste CSS shimmer skeletons, a Suspense + use() streaming pattern, and a React 19 useOptimistic component with automatic error rollback.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Skeleton & Optimistic UI

Three tools for making an app *feel* fast: **skeletons** (show the shape before the
data), **Suspense streaming** (render the shell instantly, stream slow parts in), and
**optimistic updates** (apply the change locally before the server confirms, roll back
if it fails). Grounded against the React docs for `useOptimistic`, `Suspense`, and `use`.

## When to use

The moment a UI "flashes empty then pops in", a spinner feels janky, or a mutation (like,
rename, add-to-cart, reorder) should feel instant. Skip decorative motion — see `when_not_to_use`.

## Prerequisites

- **Skeletons (Recipe 1):** nothing. Pure CSS/HTML, works everywhere.
- **`useOptimistic` (Recipe 3):** **React 19** (stable). It only updates state *inside an
  Action* — a function passed to `startTransition`, or a `<form action={...}>` /
  `formAction`. Outside a transition the optimistic value never appears.
- **`use(promise)` (Recipe 2):** React 19 (or a late React 18 canary). The promise must be
  created by a Suspense-enabled framework or cached — do **not** create a `fetch()` promise
  fresh in render each pass (it re-fires forever). Cache it, or use a framework loader.
- **Next.js App Router:** `loading.tsx` and Server Components give you Recipes 1+2 with zero
  client JS. No extra install.

## Recipe 1 — CSS shimmer skeleton (framework-free)

The golden rule: **match the real content's box model** (width, height, margins, radius) so there
is no layout shift when data arrives. Animate a moving highlight, and respect reduced-motion.

```html
<div class="card-skel" aria-hidden="true">
  <div class="skel skel-avatar"></div>
  <div class="skel skel-line" style="width: 70%"></div>
  <div class="skel skel-line" style="width: 90%"></div>
  <div class="skel skel-line" style="width: 40%"></div>
</div>

<style>
  .card-skel { display: grid; gap: 10px; padding: 16px; max-width: 340px; }
  .skel {
    --base: #e5e7eb;         /* light theme */
    --hi:   #f3f4f6;
    border-radius: 8px;
    background:
      linear-gradient(90deg, var(--base) 0%, var(--hi) 50%, var(--base) 100%);
    background-size: 200% 100%;
    animation: shimmer 1.4s ease-in-out infinite;
  }
  .skel-avatar { width: 48px; height: 48px; border-radius: 50%; }
  .skel-line   { height: 12px; }

  @keyframes shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }
  @media (prefers-color-scheme: dark) {
    .skel { --base: #27272a; --hi: #3f3f46; }
  }
  @media (prefers-reduced-motion: reduce) {
    .skel { animation: none; opacity: 0.7; }  /* static grey, no motion */
  }
</style>
```

Accessibility: `aria-hidden="true"` the skeleton and announce status via a visually-hidden
`<div role="status" aria-live="polite">Loading…</div>` — one clear announcement, not a wall of boxes.

**Tailwind shortcut:** `animate-pulse` gives an opacity-fade skeleton for free — `<div class="h-3
w-40 rounded bg-zinc-200 dark:bg-zinc-800 animate-pulse" />`. Use the shimmer above for the sweep.

## Recipe 2 — Suspense streaming with `use()`

Render the page shell immediately; stream the slow part in when its promise resolves. The
skeleton from Recipe 1 becomes the Suspense `fallback`.

```jsx
import { Suspense, use } from 'react';

// Create/cache the promise OUTSIDE render (module scope, a cache, or a framework loader).
// Never call fetch() inline in the child's render body — it would refetch every attempt.
const usersPromise = fetch('/api/users').then((r) => r.json());

function UserList() {
  const users = use(usersPromise);          // suspends until resolved
  return <ul>{users.map((u) => <li key={u.id}>{u.name}</li>)}</ul>;
}

export default function Page() {
  return (
    <main>
      <h1>Team</h1>
      <Suspense fallback={<CardSkeleton count={5} />}>
        <UserList />
      </Suspense>
    </main>
  );
}
```

**Next.js App Router equivalent** — a co-located `loading.tsx` becomes the Suspense fallback for
the whole route segment automatically; the Server Component can just `await` its data:

```tsx
// app/team/loading.tsx  — shown instantly while page.tsx streams
export default function Loading() { return <CardSkeleton count={5} />; }

// app/team/page.tsx  (Server Component)
export default async function Page() {
  const users = await getUsers();           // no use() needed; server awaits
  return <ul>{users.map((u) => <li key={u.id}>{u.name}</li>)}</ul>;
}
```

Wrap individual slow widgets in their own `<Suspense>` so a slow chart never blocks the dashboard.

## Recipe 3 — Optimistic update with automatic rollback (`useOptimistic`, React 19)

Signature (from the React docs):

```js
const [optimisticState, addOptimistic] = useOptimistic(state, updateFn);
// updateFn: (currentState, optimisticValue) => newState   (pure)
```

`optimisticState` equals `state` until you call `addOptimistic` *inside an Action*; then it shows
the optimistic value until the Action settles. **Rollback is automatic** — when the transition ends
React discards the optimistic layer and re-renders from the real `state`; if the mutation threw,
`state` never advanced, so the UI snaps back on its own. You write no undo code — just don't commit
the real state on failure.

```jsx
import { useOptimistic, useState, startTransition } from 'react';

function LikeButton({ postId, initialLikes }) {
  const [likes, setLikes] = useState(initialLikes);
  const [error, setError] = useState(null);

  // optimistic layer: bump the count by the pending delta
  const [optimisticLikes, addOptimisticLike] = useOptimistic(
    likes,
    (current, delta) => current + delta,
  );

  function handleLike() {
    setError(null);
    startTransition(async () => {
      addOptimisticLike(+1);              // UI updates instantly
      try {
        const confirmed = await likePost(postId);   // server call
        setLikes(confirmed.likes);        // commit real state → keeps the change
      } catch (e) {
        setError('Could not save — reverted.');
        // do nothing else: likes stays put, optimistic +1 is discarded → auto rollback
      }
    });
  }

  return (
    <>
      <button onClick={handleLike}>♥ {optimisticLikes}</button>
      {error && <p role="alert">{error}</p>}
    </>
  );
}
```

**Form / list-append variant** — same pattern with a `<form action>`; append a temp item,
then let the action reconcile. Render `sending: true` items dimmed so pending reads as pending:

```jsx
const [optimisticMsgs, addOptimisticMsg] = useOptimistic(
  messages,
  (state, text) => [...state, { text, sending: true }],
);
async function formAction(formData) {
  addOptimisticMsg(formData.get('text'));   // greyed "sending…" bubble
  await sendMessage(formData.get('text'));  // throw here → bubble disappears
}
// <form action={formAction}>…</form>
```

## Verify

1. **No layout shift:** load with network throttled (DevTools → Slow 3G). The skeleton must occupy
   the *same* box as the real content — content should not jump when it arrives. Watch the CLS
   number in the Performance panel.
2. **Streaming works:** the `<h1>`/shell paints before the Suspense child; the fallback shows, then
   swaps to data. In Next.js, view source — the shell HTML arrives first, data streams after.
3. **Optimistic + rollback:** click Like — count bumps immediately. Then force a failure (throw in
   `likePost`, or go offline) and click again — the count must **snap back** on its own and the
   error message appears. No manual revert.
4. **Reduced motion:** enable OS "Reduce motion" — the shimmer stops (static grey), no infinite
   sweep.
5. **React 19 check:** `npm ls react` must show 19.x — on React 18 `useOptimistic`/`use` are absent or canary-only and throw.

## Pitfalls

- **`useOptimistic` outside a transition does nothing.** The update *must* run inside
  `startTransition` or a form `action`/`formAction`. A plain `onClick` that calls `addOptimistic`
  synchronously won't show the optimistic value.
- **Committing state on failure defeats rollback.** Only call the real `setState` on the *success*
  path. If you set it in a `finally`, you overwrite with stale/failed data and lose the auto-revert.
- **Creating the promise in render (Recipe 2).** `use(fetch(...))` written inline refetches on every
  render attempt and can loop. Hoist to module scope, a cache, or a framework loader.
- **Spinner-shaped skeletons.** A centered spinner in a card-shaped hole still causes a jump. Mirror
  the real layout's dimensions, not a generic blob.
- **Over-skeletonizing.** If data returns in <300ms a skeleton flash looks worse than nothing —
  delay showing it ~200–300ms so fast loads never flash.
- **Missing `key` on optimistic list items.** Appended optimistic rows need stable keys (a client
  id, not the array index) or React mis-reconciles when the real item replaces the temp one.
- **Accessibility noise.** `aria-hidden` the skeleton and announce loading once via a `role="status"`
  live region, rather than letting dozens of empty nodes reach screen readers.
