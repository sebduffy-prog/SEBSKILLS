---
name: quick-microsite
category: frontend-and-design
description: >-
  Ship a polished 2-4 "page" static microsite (event, product launch, personal profile,
  docs-lite) as ONE self-contained HTML file using anchor-nav sections with scroll-spy — no
  build step, no framework. Sticky nav, smooth in-page routing, tasteful light+dark theme, one
  accent, WCAG-AA contrast, focus-visible, keyboard nav. Graduate to a minimal Astro scaffold
  only when true separate URLs, per-page metadata, or a growing content set demand it. Use for
  "microsite", "small site", "event site", "launch page", "about/profile site", "few-page site".
  Ends on a design-approval gate — preview before done.
when_to_use:
  - You need a 2-4 section site (event, launch, profile, mini-docs) and one self-contained .html is acceptable
  - Someone wants a small multi-section site with a nav bar that jumps between sections, no backend
  - A one-off event / launch / "about me" site that must look polished but ship in minutes
  - You want smooth in-page navigation and scroll-spy without a router or npm install
  - Prototyping site structure and copy before deciding whether it warrants a real framework
when_not_to_use:
  - It is a single hero + CTA marketing page — use quick-landing (one screen, one section)
  - It is an interactive dashboard with charts/tables/filters — use quick-dashboard (and dataviz for charts)
  - It is primarily a form that collects input — use quick-form
  - It is an interactive utility/converter/calculator — use quick-tool
  - You truly need separate URLs, per-page SEO metadata, an MDX content collection, or 5+ pages — scaffold Astro (recipe below) or use frontend-design
keywords:
  - microsite
  - small site
  - event site
  - launch page
  - profile site
  - anchor navigation
  - scroll spy
  - single file html
  - smooth scroll
  - sticky nav
  - astro
  - no build step
  - dark mode
  - focus-visible
  - multi-section
similar_to:
  - quick-landing
  - quick-dashboard
  - quick-form
  - quick-tool
  - frontend-design
inputs_needed: >-
  Site name/title, the 2-4 sections to include (e.g. Home/About/Schedule/Contact) with a heading
  and a sentence each, and one accent colour or brand hint. Missing pieces get honest "awaiting
  data" placeholders — do not block on questions.
produces: >-
  One self-contained microsite.html — sticky anchor nav with scroll-spy, 2-4 semantic <section>
  landmarks, light+dark theme via one CSS custom-property block, one accent — that opens directly
  in a browser. Or, when it graduates, a minimal Astro scaffold command + page structure.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Quick Microsite

Author **one** polished microsite as a **single self-contained `microsite.html`** — a sticky top
nav whose links smooth-scroll between 2-4 semantic `<section>`s, with scroll-spy highlighting the
active section. No build step, no framework, no npm. It opens straight in a browser and ships in
minutes. Reach for Astro **only** when the content genuinely outgrows one file.

## When to use

The moment someone says "microsite", "small event/launch/profile site", or "a few pages with a nav
bar" and a single HTML file is acceptable. If it is really one hero → `quick-landing`. If it needs a
router, separate URLs, or per-page SEO → jump to the Astro recipe or `frontend-design`.

## Prerequisites

- Nothing to install for the single-file path. Any modern browser opens the file.
- No CDN required — the starter is fully self-contained (system fonts, hand-written CSS/JS), so it
  works offline and has no third-party runtime dependency.
- Astro path only: **Node.js v22.12.0+** (odd majors like v23 are unsupported). This Mac's `python3`
  is 3.9 and irrelevant here — a static site needs no Python.

## Design contract (opinionated — do not negotiate these away)

- **ONE file** until proven otherwise. Graduate to Astro only when `when_not_to_use` bites.
- **One tasteful theme, light + dark**, driven by CSS custom properties + `prefers-color-scheme`.
- **One accent colour.** One spacing scale (a `--space` rhythm). No second font unless asked.
- **Quality floor, always:** semantic `<header>/<nav>/<main>/<section>/<footer>`, one `<h1>` then
  ordered headings, visible `:focus-visible` rings, full keyboard nav, and WCAG-AA text contrast
  (≥ 4.5:1 body, ≥ 3:1 large). Verify with the sibling `accessible-contrast-checker`.
- **AT MOST ONE ui-effect** — the scroll-spy active-link highlight is it. Resist parallax, reveals,
  cursor tricks. `prefers-reduced-motion` disables smooth scroll.
- **"Awaiting data" over blocking.** Unknown copy becomes a visible `[awaiting: schedule]`
  placeholder; never invent facts, never stall on questions.
- **End on the design-approval gate** (see Verify). Preview + explicit approval before "done".

## Recipe A — single-file microsite (default)

1. Confirm the 2-4 sections and the site name. Anything unknown → placeholder, keep moving.
2. Copy the starter below to `microsite.html`. Rename sections, set `--accent`, fill copy.
3. Each nav link's `href="#id"` must match a `<section id="id">`. Keep IDs and labels in sync.
4. Open in a browser, click through the nav, tab through every link/button, toggle OS dark mode.
5. Run the Verify checklist, then the approval gate.

### Copy-paste starter

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Nova Summit 2026 — Microsite</title>
<style>
  :root{
    --accent:#4f46e5; --accent-ink:#ffffff;
    --bg:#ffffff; --surface:#f6f7f9; --text:#15181d; --muted:#5b6270; --border:#e3e6ea;
    --space:clamp(1rem,2.5vw,1.75rem); --maxw:60rem; --radius:14px;
    --ring:0 0 0 3px color-mix(in srgb, var(--accent) 45%, transparent);
  }
  @media (prefers-color-scheme:dark){
    :root{ --bg:#0e1014; --surface:#171a20; --text:#eef1f5; --muted:#a2abb8; --border:#272b33; }
  }
  *{box-sizing:border-box} html{scroll-behavior:smooth}
  @media (prefers-reduced-motion:reduce){ html{scroll-behavior:auto} }
  body{margin:0;font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
    background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased}
  a{color:var(--accent)} .wrap{max-width:var(--maxw);margin:0 auto;padding:0 var(--space)}
  /* sticky nav + scroll-spy */
  header{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--bg) 88%,transparent);
    backdrop-filter:blur(8px);border-bottom:1px solid var(--border)}
  nav{display:flex;gap:.25rem;align-items:center;flex-wrap:wrap;min-height:56px}
  nav .brand{font-weight:700;margin-right:auto}
  nav a{padding:.5rem .7rem;border-radius:8px;text-decoration:none;color:var(--muted);font-weight:600}
  nav a:hover{color:var(--text)}
  nav a[aria-current="true"]{color:var(--text);background:var(--surface)}
  :focus-visible{outline:none;box-shadow:var(--ring);border-radius:8px}
  /* skip link for keyboard users */
  .skip{position:absolute;left:-999px}.skip:focus{left:.5rem;top:.5rem;background:var(--accent);
    color:var(--accent-ink);padding:.5rem .8rem;border-radius:8px;z-index:20}
  section{scroll-margin-top:72px;padding:clamp(3rem,8vw,6rem) 0;border-bottom:1px solid var(--border)}
  h1{font-size:clamp(2rem,6vw,3.25rem);line-height:1.1;margin:.2em 0}
  h2{font-size:clamp(1.4rem,4vw,2rem);margin:0 0 .4em}
  .lead{font-size:1.15rem;color:var(--muted);max-width:42ch}
  .cta{display:inline-block;margin-top:1.5rem;background:var(--accent);color:var(--accent-ink);
    padding:.8rem 1.3rem;border-radius:var(--radius);text-decoration:none;font-weight:700}
  .grid{display:grid;gap:var(--space);grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));margin-top:1.5rem}
  .card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1.25rem}
  .todo{color:var(--muted);font-style:italic} /* awaiting-data placeholder */
  footer{padding:2.5rem 0;color:var(--muted)}
</style>
</head>
<body>
<a class="skip" href="#home">Skip to content</a>
<header>
  <nav class="wrap" aria-label="Primary">
    <a class="brand" href="#home">Nova Summit</a>
    <a href="#home">Home</a>
    <a href="#about">About</a>
    <a href="#schedule">Schedule</a>
    <a href="#contact">Contact</a>
  </nav>
</header>

<main>
  <section id="home" class="wrap" aria-labelledby="home-h">
    <h1 id="home-h">Nova Summit 2026</h1>
    <p class="lead">A one-day gathering for builders. <span class="todo">[awaiting: tagline]</span></p>
    <a class="cta" href="#schedule">See the schedule</a>
  </section>

  <section id="about" class="wrap" aria-labelledby="about-h">
    <h2 id="about-h">About</h2>
    <p class="lead">What the event is and who it's for.</p>
    <div class="grid">
      <div class="card"><h3>Talks</h3><p class="todo">[awaiting: track detail]</p></div>
      <div class="card"><h3>Workshops</h3><p class="todo">[awaiting: workshop list]</p></div>
      <div class="card"><h3>Venue</h3><p class="todo">[awaiting: location]</p></div>
    </div>
  </section>

  <section id="schedule" class="wrap" aria-labelledby="sched-h">
    <h2 id="sched-h">Schedule</h2>
    <p class="lead">Session times and speakers.</p>
    <p class="todo">[awaiting: schedule data — replace with a real agenda list]</p>
  </section>

  <section id="contact" class="wrap" aria-labelledby="contact-h">
    <h2 id="contact-h">Contact</h2>
    <p class="lead">Questions? <a href="mailto:hello@example.com">hello@example.com</a></p>
  </section>
</main>

<footer class="wrap">© 2026 Nova Summit. Built as a single file.</footer>

<script>
  // Scroll-spy: mark the nav link for the section in view (the one allowed ui-effect).
  const links = [...document.querySelectorAll('nav a[href^="#"]')];
  const byId = Object.fromEntries(links.map(a => [a.getAttribute('href').slice(1), a]));
  const spy = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      links.forEach(a => a.removeAttribute('aria-current'));
      byId[e.target.id]?.setAttribute('aria-current', 'true');
    }
  }, { rootMargin: '-45% 0px -50% 0px', threshold: 0 });
  document.querySelectorAll('main section[id]').forEach(s => spy.observe(s));
</script>
</body>
</html>
```

## Recipe B — graduate to Astro (only when it outgrows one file)

Trigger when you need real separate URLs, per-page `<title>`/meta, an MDX/Markdown content set, or
roughly 5+ pages. Astro ships **zero JS by default** and outputs plain static HTML — the same fast,
dependency-light result, with real routing.

```bash
# Node v22.12.0+ required. Scaffold a minimal, empty project non-interactively:
npm create astro@latest my-microsite -- --template minimal --yes
cd my-microsite
npm run dev        # live preview at http://localhost:4321
npm run build      # static output → ./dist  (deploy that folder anywhere)
```

Then one file per page under `src/pages/` — `index.astro`, `about.astro`, `schedule.astro` map to
`/`, `/about`, `/schedule`. Lift the CSS custom-property block and the design contract above into a
shared `src/layouts/Base.astro`; keep the same accent, spacing scale, and light+dark theme. Add
integrations only if truly needed: `npm create astro@latest -- --add sitemap`.

## Verify

- [ ] Exactly one `<h1>`; every `<section>` has an `id`, an `aria-labelledby`, and a matching nav link.
- [ ] Every nav `href="#id"` resolves to a real section (no dead anchors); clicking scrolls to it.
- [ ] Tab order reaches skip-link → brand → each nav link → each CTA; `:focus-visible` ring is visible.
- [ ] Scroll-spy sets `aria-current="true"` on exactly one link as you scroll through sections.
- [ ] Toggle OS dark mode — text stays AA-legible in both (check with `accessible-contrast-checker`).
- [ ] `prefers-reduced-motion` disables smooth scroll (test in devtools rendering panel).
- [ ] No fabricated content — unknowns remain visible `[awaiting: …]` placeholders.
- [ ] **Design-approval gate:** show the rendered page (screenshot or opened file) and get explicit
      approval via the `design-approval-gate` skill before calling it done.

## Pitfalls

- **Nav labels drift from IDs.** Renaming a section but not its `href` yields a dead anchor. Keep the
  `id`, the `aria-labelledby` target, and the nav `href` in lockstep.
- **Sticky nav hides section tops.** Fixed by `scroll-margin-top` on `section` — keep it ≥ nav height.
- **Scroll-spy flicker.** The `-45% 0px -50% 0px` rootMargin picks one section near viewport centre;
  widen the top/bottom margins if a very tall section never activates.
- **Reaching for a router too early.** In-page anchors ARE the routing for 2-4 sections. Don't add a
  framework for smooth scroll — the browser does it natively.
- **Second ui-effect creep.** Scroll-spy is the one effect. Adding reveal-on-scroll or parallax
  breaks the contract and the calm; say no.
- **Astro Node version.** `npm create astro` fails on Node < 22.12 or on odd-numbered majors (v23).
  Check `node -v` first if the scaffold errors.
- **Play CDN / external fonts.** The starter deliberately avoids them so it works offline; if you add
  a web font later, self-host or accept the network dependency and its FOUT.
