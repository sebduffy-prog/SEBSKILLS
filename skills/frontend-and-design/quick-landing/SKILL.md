---
name: quick-landing
category: frontend-and-design
description: >-
  Ship one polished, single-file HTML + Tailwind (Play CDN) landing page in under 2 minutes,
  no build step — semantic hero, exactly 3 feature cards, one primary CTA, footer, tasteful
  light+dark theme, one accent, WCAG-AA contrast, focus-visible, keyboard nav. Use when asked
  for a landing page, marketing page, hero section, product splash, waitlist/coming-soon page,
  or a "quick single-page site". Ends on a design-approval gate — preview before done.
when_to_use:
  - You need a marketing / product landing page fast and a single self-contained .html file is acceptable
  - Someone asks for a hero + a few feature cards + a call-to-action, no framework or backend
  - A coming-soon, waitlist, or launch splash page that must look polished but ship in minutes
  - You want a Tailwind page with no npm / build step that opens straight in a browser
  - Prototyping a page's copy and layout before committing to a full Next/Vite project
when_not_to_use:
  - The page needs routing, auth, forms that POST, or shared state — graduate to frontend-design or web-artifacts-builder
  - It is an interactive dashboard with charts/tables — use quick-dashboard (and dataviz for the charts)
  - It is primarily a form to collect input — use quick-form
  - It is a multi-page marketing site — use quick-microsite
  - You need production-grade Tailwind (purged, versioned) rather than the dev-only Play CDN — set up a real Tailwind build via frontend-design
keywords:
  - landing page
  - hero section
  - tailwind
  - play cdn
  - single file html
  - cta
  - feature cards
  - coming soon
  - waitlist
  - marketing page
  - no build step
  - dark mode
  - responsive
  - focus-visible
similar_to:
  - quick-dashboard
  - quick-form
  - quick-tool
  - quick-microsite
  - frontend-design
inputs_needed: >-
  Product/brand name and one-line value proposition; ideally 3 feature titles+blurbs and one CTA
  label+target. Missing pieces get honest "awaiting data" placeholders — do not block on questions.
produces: >-
  One self-contained landing.html (Tailwind Play CDN, inline @theme accent, light+dark) — hero,
  3 feature cards, one primary CTA, footer — that opens directly in a browser.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Quick Landing

Author **one** polished landing page as a **single self-contained `landing.html`** — hero, exactly
three feature cards, one primary CTA, footer. Tailwind via the Play CDN means **no build step, no npm,
no framework**: it opens straight in a browser and ships in under two minutes.

## When to use

The moment someone says "landing page", "hero", "coming soon", "waitlist", or "quick splash page" and
a single HTML file is acceptable. Wanting a router, a submitting form, charts, or multiple pages? Stop
— see `when_not_to_use` for the right sibling.

## Prerequisites

Nothing to install — any modern browser opens the file. The Tailwind Play CDN needs network access at
load and is **dev-only** by Tailwind's own docs: fine for preview, but wire a real Tailwind build
(frontend-design) before calling it production.

## The non-negotiables (quality floor, even when fast)

Speed is no excuse to skip these:

1. **Semantic HTML** — `<header> <main> <section> <footer>`, one `<h1>`, real `<a>`/`<button>`.
2. **Keyboard + focus** — visible `focus-visible` ring on every interactive element; logical tab order.
3. **WCAG-AA contrast** — body text ≥ 4.5:1 in **both** themes (check with `accessible-contrast-checker`).
4. **Light + dark** — Tailwind v4's `dark:` variant follows `prefers-color-scheme`; no toggle needed here.
5. **Responsive** — one column on mobile, grid on ≥ `md`, no horizontal scroll at 360px.
6. **Awaiting-data placeholders** — unknown copy becomes an honest `[awaiting: …]` stub, never invented
   claims or fake logos. Never block the build on questions.
7. **At most ONE ui-effect** — the starter lifts cards on hover + fades up on load, gated behind
   `prefers-reduced-motion`. Do not stack more.

## Opinionated defaults (don't offer options — just do these)

- **Accent**: one color as `--color-accent` in an inline `@theme` — change that line to rebrand.
- **Type**: system UI stack (zero network fonts); one webfont only if asked. **Spacing**: Tailwind's
  default scale; section rhythm `py-20 sm:py-28`; container `max-w-6xl mx-auto px-6`.

## Recipe

Copy the starter below to `landing.html`. Replace four things — brand name, hero headline+subhead, the
3 feature cards, the CTA — using `[awaiting: …]` stubs for anything you don't have yet. Rebrand by
editing **one line** (`--color-accent`). Then run **Verify** and the **design-approval gate**.

```html
<!doctype html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Acme — [awaiting: tagline]</title>
  <meta name="description" content="[awaiting: 155-char meta description]" />
  <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
  <style type="text/tailwindcss">
    @theme {
      --color-accent: oklch(0.62 0.19 264);      /* the ONE line to rebrand */
      --color-accent-fg: oklch(0.99 0 0);        /* text ON the accent */
    }
    @media (prefers-reduced-motion: no-preference) {
      .reveal { opacity: 0; transform: translateY(12px); animation: rise .6s ease forwards; }
      .reveal:nth-child(2) { animation-delay: .08s; }
      .reveal:nth-child(3) { animation-delay: .16s; }
      @keyframes rise { to { opacity: 1; transform: none; } }
    }
  </style>
</head>
<body class="min-h-screen bg-white text-slate-800 dark:bg-slate-950 dark:text-slate-200
             antialiased selection:bg-accent/20">

  <header class="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
    <a href="#" class="font-semibold tracking-tight text-lg
                       rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-accent">
      Acme
    </a>
    <nav class="flex items-center gap-6 text-sm">
      <a href="#features" class="hover:text-accent focus:outline-none focus-visible:ring-2
                                 focus-visible:ring-accent rounded px-1">Features</a>
      <a href="#cta"
         class="inline-flex items-center rounded-lg bg-accent px-4 py-2 font-medium text-accent-fg
                shadow-sm transition hover:brightness-110
                focus:outline-none focus-visible:ring-2 focus-visible:ring-accent
                focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-950">
        Get started
      </a>
    </nav>
  </header>

  <main>
    <!-- HERO -->
    <section class="max-w-6xl mx-auto px-6 py-20 sm:py-28 text-center">
      <p class="reveal inline-block rounded-full border border-slate-200 dark:border-slate-800
                px-3 py-1 text-xs font-medium text-slate-500 dark:text-slate-400">
        [awaiting: eyebrow — e.g. "Now in beta"]
      </p>
      <h1 class="reveal mt-6 text-4xl sm:text-6xl font-bold tracking-tight text-balance">
        The fastest way to [awaiting: core promise]
      </h1>
      <p class="reveal mx-auto mt-6 max-w-2xl text-lg text-slate-600 dark:text-slate-400 text-pretty">
        [awaiting: one-sentence subhead that says who it's for and why it's better.]
      </p>
      <div class="reveal mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
        <a href="#cta"
           class="inline-flex items-center rounded-lg bg-accent px-6 py-3 font-medium text-accent-fg
                  shadow-sm transition hover:brightness-110
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-accent
                  focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-950">
          [awaiting: primary CTA]
        </a>
        <a href="#features"
           class="inline-flex items-center rounded-lg px-6 py-3 font-medium
                  text-slate-700 dark:text-slate-300 hover:text-accent
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-lg">
          See features →
        </a>
      </div>
    </section>

    <!-- FEATURES: exactly 3 -->
    <section id="features" class="max-w-6xl mx-auto px-6 py-20 sm:py-28">
      <h2 class="text-center text-3xl font-bold tracking-tight">Why teams choose us</h2>
      <div class="mt-14 grid gap-6 md:grid-cols-3">
        <article class="reveal group rounded-2xl border border-slate-200 dark:border-slate-800
                        bg-white dark:bg-slate-900 p-6 shadow-sm transition
                        hover:-translate-y-1 hover:shadow-md">
          <div class="grid h-11 w-11 place-items-center rounded-xl bg-accent/10 text-accent"
               aria-hidden="true">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"
                 stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round"
                 d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
          </div>
          <h3 class="mt-4 font-semibold">[awaiting: feature 1 title]</h3>
          <p class="mt-2 text-sm text-slate-600 dark:text-slate-400">
            [awaiting: one-line benefit, not a feature list.]
          </p>
        </article>
        <!-- Feature 2 and Feature 3: paste the <article> above twice more. Change only the
             <path d="…"> (pick another icon), the <h3> title, and the <p> benefit. Keep three. -->
      </div>
    </section>

    <!-- CTA -->
    <section id="cta" class="max-w-6xl mx-auto px-6 pb-20 sm:pb-28">
      <div class="rounded-3xl bg-accent px-8 py-16 text-center text-accent-fg">
        <h2 class="text-3xl sm:text-4xl font-bold tracking-tight text-balance">
          [awaiting: closing headline]
        </h2>
        <p class="mx-auto mt-4 max-w-xl opacity-90">[awaiting: reassuring one-liner.]</p>
        <a href="#"
           class="mt-8 inline-flex items-center rounded-lg bg-white px-6 py-3 font-medium text-slate-900
                  shadow-sm transition hover:bg-slate-100
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-white
                  focus-visible:ring-offset-2 focus-visible:ring-offset-accent">
          [awaiting: CTA label]
        </a>
      </div>
    </section>
  </main>

  <footer class="border-t border-slate-200 dark:border-slate-800">
    <div class="max-w-6xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between
                gap-4 text-sm text-slate-500">
      <p>© <span id="yr"></span> Acme. [awaiting: rights line]</p>
      <nav class="flex gap-6">
        <a href="#" class="hover:text-accent focus:outline-none focus-visible:ring-2
                           focus-visible:ring-accent rounded px-1">Privacy</a>
        <a href="#" class="hover:text-accent focus:outline-none focus-visible:ring-2
                           focus-visible:ring-accent rounded px-1">Contact</a>
      </nav>
    </div>
  </footer>

  <script>document.getElementById('yr').textContent = new Date().getFullYear();</script>
</body>
</html>
```

## Verify

Confirm every box before claiming done:

- [ ] Opens as a standalone file — `open landing.html` (macOS) renders styled, no console errors.
- [ ] Exactly one `<h1>`; `<header>/<main>/<section>/<footer>` shell; `Tab` cycles every link/button
      in order with a **visible** accent ring.
- [ ] Toggle OS dark mode → colors flip, text stays AA-readable; narrow to 360px → single column, no h-scroll.
- [ ] "Reduce motion" → no fade/lift; content still fully visible. No invented claims/logos/lorem.

Shareable localhost preview: `python3 -m http.server 8000` → `http://localhost:8000/landing.html`.

## Design-approval gate (do this before saying "done")

This skill **ends on approval, not on file-write**. Produce a real preview (screenshot in light **and**
dark, or a published URL via the `design-approval-gate` skill / an Artifact), then ask plainly: *"Here's
the page in light and dark — approve as-is, or change the accent / headline / features?"* Only an
explicit yes completes the task. On changes, edit the single file (usually just `--color-accent` and the
copy blocks) and re-preview.

## Pitfalls

- **Play CDN is dev-only + needs network.** It fetches Tailwind at runtime and doesn't purge; the page
  is blank-styled offline. Shipping to real traffic → compiled Tailwind build (frontend-design).
- **CSP-strict hosts (claude.ai Artifacts) block external CDNs.** There, don't use the Play CDN — use
  the Artifact tool's own pipeline (inlined styles) instead.
- **Don't grow the feature grid or the palette.** Three cards, one accent, one effect is the design.
  More sections → `quick-microsite`; a second brand color or stacked animations just reads as noise.
- **Keep contrast on the accent block.** A pale accent can push `--color-accent-fg` and CTA-on-accent
  text below AA — recheck both themes after changing `--color-accent`.
```
