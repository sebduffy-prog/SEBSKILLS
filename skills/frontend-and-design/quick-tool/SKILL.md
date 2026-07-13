---
name: quick-tool
category: frontend-and-design
description: >-
  Ship one single-purpose interactive tool — calculator, unit/currency converter, generator
  (password, slug, QR-input, color), picker, scorer/quiz, estimator — as ONE self-contained
  .html file with clean reactive state via Alpine.js (CDN, no build). Opinionated light+dark
  theme, WCAG-AA, focus-visible, keyboard nav, real empty/loading/error states. Use when asked
  for a "quick tool", "calculator", "converter", "generator", "picker", or a small interactive
  widget. Ends on a design-approval gate — preview before done.
when_to_use:
  - You need a small single-purpose interactive tool (calculator, converter, generator, picker, scorer) fast
  - The logic is client-side and a single self-contained .html file with reactive state is acceptable
  - Someone wants inputs → live computed output with no backend and no build step
  - You want reactive UI (bindings, computed values) without React/Vue/npm — Alpine.js from a CDN
  - Prototyping a tool's interaction and math before committing to a full app
when_not_to_use:
  - It is a form that POSTs/collects submissions rather than computing a live result — use quick-form
  - It shows charts/tables/metrics dashboards — use quick-dashboard (and dataviz for charts)
  - It is a marketing/landing page — use quick-landing
  - It needs routing, auth, a database, or shared server state — graduate to frontend-design or web-artifacts-builder
  - The heavy lifting is a data chart — use quick-chart
keywords:
  - quick tool
  - calculator
  - converter
  - generator
  - picker
  - scorer
  - alpine.js
  - htmx
  - reactive state
  - single file html
  - no build step
  - client-side
  - dark mode
  - focus-visible
  - widget
similar_to:
  - quick-form
  - quick-dashboard
  - quick-chart
  - quick-landing
  - quick-microsite
inputs_needed: >-
  What the tool does (inputs → output), the compute rule/formula, and any fixed options or
  ranges. Missing pieces get honest "awaiting formula" placeholders — do not block on questions.
produces: >-
  One self-contained tool.html (Alpine.js CDN, inline CSS tokens, light+dark) — labelled inputs,
  a live computed result, copy/reset affordances — that opens directly in a browser.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Quick Tool

Author **one** single-purpose interactive tool as **one self-contained `tool.html`** — labelled
inputs, a live computed result. Reactive state comes from **Alpine.js via CDN**, so there is **no
build step, no npm, no framework**. It opens straight in a browser.

## When to use

The job is a **small tool with one job**: inputs go in, a computed answer comes out live.
Calculators (tip, mortgage, BMI, ROI), converters (units, currency, timezone), generators
(password, slug, UUID, palette), pickers, scorers/quizzes, estimators. If it needs a backend,
routing, or persistent data, it is not a quick tool — see `when_not_to_use`.

## Core rules (opinionated on purpose)

1. **ONE self-contained file.** No build, no bundler, no framework. Alpine.js from a CDN is the only
   dependency. Add htmx (also CDN) *only if* the tool truly needs a server round-trip — most quick
   tools compute entirely client-side and never do.
2. **Alpine for state, not a spaghetti of `onclick`.** One `x-data` object holds all state; use
   `x-model` for inputs and `x-text` / getters for derived output. Compute as pure functions of
   state — never mutate inputs in place (return fresh values).
3. **Opinionated defaults, not options.** One light+dark theme, one spacing scale, one accent — no
   theme pickers or layout choices unless asked.
4. **Quality floor is non-negotiable, even when fast:** semantic HTML (`<label for>`, `<output>`,
   `<button>`), visible `:focus-visible` ring, full keyboard operation, WCAG-AA contrast, and real
   **empty / loading / error** states for the result — never a blank box.
5. **"Awaiting formula" over blocking.** If the math/rule is unknown, ship a working shell with a
   labelled placeholder computation and a `// TODO` — do not stall on questions.
6. **At most ONE ui-effect** — a single tasteful flourish (count-up or copy-flash), never a pile of
   animations. Respect `prefers-reduced-motion`.
7. **End on the design-approval gate.** Preview it and get explicit approval before calling it done.

## Steps

1. **Name the shape:** list the inputs, their types/ranges, and the single output; write the
   compute rule as one pure expression of the inputs.
2. **Copy the starter below**, rename the `x-data` fields, and replace the derived getters with
   your formula. Keep the structure (skip-link, `<label>`s, `<output>`, states).
3. **Validate at the boundary:** guard empty / NaN / out-of-range input and show the `error` state
   rather than computing garbage.
4. **Verify** (below), then run the **design-approval gate** — open it, screenshot, get sign-off.

## Copy-paste starter

CDN Alpine, single accent, light+dark via `prefers-color-scheme`, keyboard-first, real states.

```html
<!-- tool.html — self-contained. Open directly in a browser. -->
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Tip Calculator</title>
<!-- Alpine: pinned version (verified live). 'defer' is required. -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js"></script>
<style>
  :root {
    --bg: #f7f7f8; --card: #fff; --fg: #1c1c1f; --muted: #6b7280;
    --line: #e5e7eb; --accent: #4f46e5; --accent-fg: #fff; --danger: #b42318;
    --radius: 12px; --gap: 1rem;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0f1115; --card: #171a21; --fg: #f3f4f6; --muted: #9aa3b2;
      --line: #262b36; --accent: #818cf8; --accent-fg: #0f1115; --danger: #ff9b93;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--fg); padding: 1.5rem;
    font: 16px/1.5 system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    display: grid; place-items: center; min-height: 100vh; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
    padding: 1.5rem; width: min(34rem, 100%); display: grid; gap: 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,.06); }
  h1 { font-size: 1.25rem; margin: 0; }
  .field { display: grid; gap: .35rem; }
  label { font-weight: 600; font-size: .9rem; }
  input, select { font: inherit; padding: .55rem .7rem; border: 1px solid var(--line);
    border-radius: 8px; background: var(--bg); color: var(--fg); }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--gap); }
  .result { display: grid; gap: .25rem; padding: 1rem; border-radius: 8px;
    background: color-mix(in srgb, var(--accent) 10%, transparent);
    border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent); }
  .result output { font-size: 2rem; font-weight: 700; font-variant-numeric: tabular-nums; }
  .result.error { background: color-mix(in srgb, var(--danger) 12%, transparent);
    border-color: color-mix(in srgb, var(--danger) 40%, transparent); }
  .muted { color: var(--muted); font-size: .85rem; }
  .actions { display: flex; gap: .5rem; }
  button { font: inherit; font-weight: 600; cursor: pointer; padding: .55rem .9rem;
    border-radius: 8px; border: 1px solid var(--line); background: var(--card); color: var(--fg); }
  button.primary { background: var(--accent); color: var(--accent-fg); border-color: transparent; }
  :focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
  .skip { position: absolute; left: -999px; }
  .skip:focus { left: 1rem; top: 1rem; background: var(--card); padding: .5rem 1rem; border-radius: 8px; }
  @media (prefers-reduced-motion: no-preference) {
    .flash { transition: background .3s; }
    .flash.on { background: color-mix(in srgb, var(--accent) 35%, transparent); }
  }
</style>

<a href="#tool" class="skip">Skip to tool</a>

<main id="tool" class="card" x-data="tool()">
  <h1>Tip Calculator</h1>

  <div class="field">
    <label for="bill">Bill amount</label>
    <input id="bill" type="number" min="0" step="0.01" inputmode="decimal"
           x-model.number="bill" placeholder="0.00" />
  </div>

  <div class="row">
    <div class="field">
      <label for="pct">Tip %</label>
      <input id="pct" type="number" min="0" max="100" step="1" x-model.number="pct" />
    </div>
    <div class="field">
      <label for="split">Split between</label>
      <input id="split" type="number" min="1" step="1" x-model.number="split" />
    </div>
  </div>

  <!-- Result: shows empty / error / value states, never a blank box -->
  <div class="result" :class="{ error: hasError }" aria-live="polite">
    <span class="muted" x-text="hasError ? 'Check your input' : 'Each person pays'"></span>
    <output x-text="display"></output>
    <span class="muted" x-show="!hasError && bill" x-text="`Tip: ${money(tip)} on ${money(bill)}`"></span>
  </div>

  <div class="actions">
    <button type="button" class="primary flash" :class="{ on: flashed }" @click="copy()">
      <span x-text="flashed ? 'Copied!' : 'Copy result'"></span>
    </button>
    <button type="button" @click="reset()">Reset</button>
  </div>
</main>

<script>
  function tool() {
    return {
      bill: null, pct: 15, split: 1, flashed: false,
      // --- pure derived values (no mutation of inputs) ---
      get tip()   { return (Number(this.bill) || 0) * (Number(this.pct) || 0) / 100; },
      get total() { return (Number(this.bill) || 0) + this.tip; },
      get perHead() { return this.total / Math.max(1, Number(this.split) || 1); },
      get hasError() {
        return this.bill < 0 || this.pct < 0 || (this.split ?? 1) < 1;
      },
      get display() {
        if (this.hasError) return '—';
        if (!this.bill) return this.money(0); // empty state
        return this.money(this.perHead);
      },
      money(n) { return new Intl.NumberFormat(undefined,
        { style: 'currency', currency: 'USD' }).format(Number(n) || 0); },
      // --- one ui-effect: copy-flash ---
      async copy() {
        if (this.hasError) return;
        try { await navigator.clipboard.writeText(this.display); } catch {}
        this.flashed = true; setTimeout(() => this.flashed = false, 900);
      },
      reset() { this.bill = null; this.pct = 15; this.split = 1; },
    };
  }
</script>
```

## Recipe: when the tool needs a server (htmx)

Most quick tools stay client-side. If yours must call an API (live FX rate, server-side generate),
add htmx alongside Alpine to swap a fragment — no fetch boilerplate, loading/error states built in:

```html
<script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.10/dist/htmx.min.js"
        integrity="sha384-H5SrcfygHmAuTDZphMHqBJLc3FhssKjG7w/CeCpFReSfwBWDTKpkzPP8c+cLsK+V"
        crossorigin="anonymous"></script>
<button hx-get="/rate?from=USD&to=EUR" hx-target="#out" hx-indicator="#spin"
        hx-on::response-error="this.nextElementSibling.hidden = false">Get rate</button>
<span id="spin" class="htmx-indicator">Loading…</span>
<output id="out"></output>
```

`hx-indicator` gives the loading state for free; `htmx:responseError` covers the error state. No
backend to talk to? Do **not** add htmx — Alpine + `fetch` (or pure compute) is simpler.

## Verify

- **Opens standalone:** `open tool.html` works with no server; every input updates the result live,
  no console errors.
- **States exist:** empty input shows a zero/placeholder; bad input flips to `error`; a loading state exists if it fetches. Never a blank box.
- **Keyboard:** Tab reaches skip-link → inputs → both buttons in order; `:focus-visible` ring is
  visible; buttons fire on Enter/Space.
- **Contrast:** accent-on-card and muted text pass WCAG-AA in light and dark (via `accessible-contrast-checker`).
- **Immutability:** compute reads inputs via getters/pure functions; the flash respects `prefers-reduced-motion`.

## Pitfalls

- **Missing `defer` on the Alpine tag** → Alpine runs before the DOM and nothing binds. Mandatory.
- **`x-model` without `.number`** on numeric inputs → you concatenate strings (`"10"+"5"="105"`).
  Use `x-model.number` and coerce with `Number()` in getters.
- **Computing on invalid input** → guard with `hasError`; show the error state instead of `NaN`.
- **Mutating an input to store a result** breaks immutability and reactivity — keep outputs as
  derived getters, never write back into `bill`/`pct`.
- **Wildcard CDN in production** (`@3.x.x`) can drift — pin the exact version once it works.
- **Reaching for a framework** because "it might grow." YAGNI — one file until routing or shared
  state genuinely forces it, then hand off to `frontend-design`.
- **Skipping the gate.** Not done until previewed and approved — invoke `design-approval-gate`.
